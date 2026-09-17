"""Server-side HTTP tools.

AssemblyAI invokes these endpoints from its own servers when the voice agent
decides to call a tool. Each tool:

  * reads the pinned `business_id` query param (added to the tool URL at
    agent-registration time),
  * reads the model's arguments from the JSON body,
  * performs the action in the local store,
  * logs a live event onto the currently active call so the owner dashboard
    animates in real time,
  * returns a short JSON body that the agent reads back to the caller.

A `call_id` is resolved through `active_call_for(business_id)` because the
tool URLs are fixed per business while call ids are per-session. This keeps
the demo deterministic without leaking session state into tool URLs.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.config import settings
from app.store import store

router = APIRouter(prefix="/tools", tags=["tools"])

BUSINESS_HOURS = {
    "status": "open",
    "hours": "Monday to Friday, 8:00 AM to 5:00 PM",
}


def _ctx(request: Request) -> tuple[dict | None, dict | None]:
    """Return (business, active_call) resolved from request context."""
    business_id = request.query_params.get("business_id")
    business = store.get_business(business_id) if business_id else None
    call = store.active_call_for(business_id) if business_id else None
    return business, call


def _log(call: dict | None, type_: str, title: str, detail: str = "") -> None:
    if call:
        store.add_call_event(call["id"], type_, title, detail)


async def _body(request: Request) -> dict:
    try:
        raw = await request.body()
        if not raw:
            return {}
        import json as _json

        return _json.loads(raw)
    except Exception:
        return {}


def _record(call: dict | None, name: str, args: dict, result: dict) -> None:
    if call:
        store.add_tool_call(call["id"], name, args, result)


# --------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------
@router.post("/get_business_info")
async def get_business_info(request: Request):
    business, call = _ctx(request)
    args = await _body(request)
    if not business:
        return {"success": False, "message": "Business not found.", "business": None}
    info = {
        "name": business.get("name"),
        "tagline": business.get("tagline"),
        "address": business.get("address"),
        "hours": business.get("hours"),
        "services": business.get("services", []),
        "service_prices": business.get("service_prices", {}),
        "note": business.get("service_note", ""),
    }
    result = {"success": True, "business": info}
    _record(call, "get_business_info", args, result)
    _log(call, "context", f"{business.get('name')}: business profile loaded")
    return result


@router.post("/check_availability")
async def check_availability(request: Request):
    business, call = _ctx(request)
    args = await _body(request)
    if not business:
        return {"success": False, "message": "Business not found.", "slots": []}
    slots = [
        {"date": "today", "time": "10:30 AM"},
        {"date": "today", "time": "1:15 PM"},
        {"date": "today", "time": "3:45 PM"},
        {"date": "tomorrow", "time": "9:00 AM"},
        {"date": "tomorrow", "time": "11:30 AM"},
    ]
    result = {"success": True, "slots": slots}
    _record(call, "check_availability", args, result)
    _log(call, "tool", "Availability checked", "Returned 5 open slots")
    return result


@router.post("/book_appointment")
async def book_appointment(request: Request):
    business, call = _ctx(request)
    args = await _body(request)
    name = args.get("name") or args.get("customer_name") or "Customer"
    service = args.get("service") or args.get("service_type") or "General appointment"
    date = args.get("date") or "as-requested"
    time = args.get("time") or "TBD"

    if business:
        services = business.get("services", [])
        if services and service.lower() not in {s.lower() for s in services} and "appointment" not in service.lower():
            result = {
                "success": False,
                "message": f"Sorry, {service} is not offered. Available services: {', '.join(services[:5])}. Offer those instead.",
            }
        else:
            booking = store.create_booking(
                call or {"id": "unknown", "business_id": (business or {}).get("id")},
                customer_name=name,
                service=service,
                date=date,
                time=time,
                channel="voice",
            )
            result = {
                "success": True,
                "booking_id": booking["id"],
                "message": f"Booked {service} for {name} on {date} at {time}. Confirmation id {booking['id']}.",
            }
            _log(call, "booking", f"Appointment booked — {service}", f"{name} · {date} {time} · {booking['id'].upper()}")
    else:
        result = {"success": False, "message": "Business not found."}
    _record(call, "book_appointment", args, result)
    if call:
        store.update_call(call["id"], last_tool="book_appointment")
    return result


@router.post("/create_quote")
async def create_quote(request: Request):
    business, call = _ctx(request)
    args = await _body(request)
    name = args.get("name") or args.get("customer_name") or "Customer"
    description = args.get("description") or args.get("details") or "General request"
    contact = args.get("phone") or args.get("contact") or "on file"

    quote = store.create_quote(
        call or {"id": "unknown", "business_id": (business or {}).get("id")},
        customer_name=name,
        description=description[:280],
        contact=contact,
    )
    result = {
        "success": True,
        "quote_id": quote["id"],
        "message": f"Quote request {quote['id'].upper()} created for {name}. A detailed estimate will be sent within 4 business hours.",
    }
    _record(call, "create_quote", args, result)
    _log(call, "quote", "Quote requested", f"{name} · {description[:80]} · {quote['id'].upper()}")
    return result


@router.post("/check_order")
async def check_order(request: Request):
    business, call = _ctx(request)
    args = await _body(request)
    order_id = str(args.get("order_id") or "TB-2045").upper()
    known = {
        "TB-2045": {"status": "out for delivery", "eta": "today between 4 and 6 PM", "items": "Large catering order, 12 boxed lunches"},
        "TB-1988": {"status": "ready for pickup", "eta": "pick up any time today", "items": "Birthday cake, 2 dozen cookies"},
        "TB-2107": {"status": "being prepared", "eta": "ready in about 45 minutes", "items": "Coffee + breakfast sandwiches for 6"},
    }
    info = known.get(order_id)
    if not info:
        result = {"success": False, "message": f"Order {order_id} not found. Ask the caller to double-check the number."}
    else:
        result = {"success": True, "order_id": order_id, **info}
    _record(call, "check_order", args, result)
    _log(call, "order", f"Order {order_id} looked up", info.get("status", ""))
    return result


@router.post("/cancel_appointment")
async def cancel_appointment(request: Request):
    business, call = _ctx(request)
    args = await _body(request)
    name = args.get("name") or "the customer"
    date = args.get("date") or "their upcoming"
    result = {
        "success": True,
        "message": f"Understood. The appointment for {name} on {date} has been cancelled. No penalty. We hope to serve them again soon.",
    }
    _record(call, "cancel_appointment", args, result)
    _log(call, "note", "Appointment cancelled", f"{name} · {date}")
    return result


@router.post("/escalate_to_human")
async def escalate_to_human(request: Request):
    business, call = _ctx(request)
    args = await _body(request)
    reason = args.get("reason") or args.get("summary") or args.get("issue") or "Customer requested a human"
    urgency = args.get("urgency") or "high"

    task = store.create_task(
        call or {"id": "unknown", "business_id": (business or {}).get("id")},
        reason=reason[:280],
        urgency=urgency,
        source="voice",
    )
    if call:
        store.update_call(call["id"], needs_human=True)
    result = {
        "success": True,
        "task_id": task["id"],
        "message": "Confirmed. A human will call back within 15 minutes. The reason has been logged and flagged as urgent.",
    }
    _record(call, "escalate_to_human", args, result)
    _log(call, "escalation", "Escalated — human callback queued", f"{reason[:80]} · {task['id'].upper()}")
    return result


@router.post("/notify_owner")
async def notify_owner(request: Request):
    business, call = _ctx(request)
    args = await _body(request)
    message = args.get("message") or "A customer called with an urgent request."
    result = {"success": True, "message": "Owner has been notified via SMS. Summary will follow after the call."}
    _record(call, "notify_owner", args, result)
    _log(call, "note", "Owner notified via SMS", message[:120])
    return result