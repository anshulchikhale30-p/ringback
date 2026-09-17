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

# Demo order book: recognizable order ids the owner might be asked about.
ORDER_BOOK = {
    "GR-2045": {"status": "confirmed, loading tonight", "window": "deliver tomorrow 5-7 AM", "items": "50 lb romaine · 3 cases avocados · 6 flats strawberries"},
    "GR-1988": {"status": "out for delivery", "window": "ETA 6:15 AM", "items": "2 cases cucumbers · 1 tote mixed greens"},
    "HL-2107": {"status": "confirmed", "window": "deliver tomorrow 6-8 AM", "items": "Organic order · 8 cases kale · 6 totes baby spinach"},
    "CF-1988": {"status": "out for delivery", "window": "ETA 6:05 AM", "items": "Café drop · green beans, oranges, bell peppers"},
    "CF-2107": {"status": "loading tonight", "window": "deliver tomorrow 5:30-7 AM", "items": "Deli drop · lemons, bananas, dill"},
}

# Simplified same-day stock picture. Keys match demo business catalog items
# (plus the bare-word names callers naturally use).
STOCK_PICTURE = {
    "romaine": {"stock": "enough for 'til close of order desk", "market_price": "$34/case (24 heads)"},
    "heirloom tomatoes": {"stock": "in stock", "market_price": "$28/box (25 lb)"},
    "avocados": {"stock": "limited — 9 cases left", "market_price": "$42/case (48 count)"},
    "hass avocados": {"stock": "limited — 9 cases left", "market_price": "$42/case (48 count)"},
    "strawberries": {"stock": "in stock", "market_price": "$16/flat (12 pints)"},
    "mixed greens": {"stock": "in stock", "market_price": "$26/tote (10 lb)"},
    "cucumbers": {"stock": "in stock", "market_price": "$24/case (20 lb)"},
    "kale": {"stock": "in stock", "market_price": "$22/case (12 bunches)"},
    "organic kale": {"stock": "in stock", "market_price": "$22/case (12 bunches)"},
    "baby spinach": {"stock": "in stock", "market_price": "$28/tote (10 lb)"},
    "spinach": {"stock": "in stock", "market_price": "$28/tote (10 lb)"},
    "blueberries": {"stock": "in stock", "market_price": "$38/case (8 pints)"},
    "green beans": {"stock": "enough for today's orders", "market_price": "$38/case (20 lb)"},
    "bell peppers": {"stock": "in stock", "market_price": "$29/case (25 lb)"},
    "navel oranges": {"stock": "in stock", "market_price": "$30/box (48 count)"},
    "oranges": {"stock": "in stock", "market_price": "$30/box (48 count)"},
    "lemons": {"stock": "in stock", "market_price": "$33/box (48 count)"},
}


def _catalog_hit(services: list[str], item: str) -> bool:
    """Fuzzy catalog match: 'avocados' hits 'hass avocados'."""
    if item in STOCK_PICTURE:
        return True
    words = {w.strip().lower() for w in item.replace(",", " ").split() if len(w) > 2}
    for svc in services:
        if svc.lower() == item:
            return True
        svc_words = {w.strip().lower() for w in svc.split()}
        if words & svc_words:
            return True
    return False


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
        "catalog": business.get("services", []),
        "prices": business.get("service_prices", {}),
        "note": business.get("service_note", ""),
    }
    result = {"success": True, "business": info}
    _record(call, "get_business_info", args, result)
    _log(call, "context", f"{business.get('name')}: order desk profile loaded")
    return result


@router.post("/check_stock")
async def check_stock(request: Request):
    business, call = _ctx(request)
    args = await _body(request)
    item = (args.get("item") or "the item").lower()
    info = STOCK_PICTURE.get(item)
    if business and business.get("services") and not _catalog_hit(business["services"], item):
        result = {
            "success": False,
            "message": f"{item} isn't on our current sheet. Catalog: {', '.join(business['services'][:6])}. Offer those instead. Never guess availability beyond this.",
            "stock": None,
        }
    elif not info:
        result = {"success": False, "message": f"No stock data for {item}. Say availability is on the sheet and suggest a catalog item."}
    else:
        result = {"success": True, "item": item, **info}
    _record(call, "check_stock", args, result)
    if result["success"]:
        _log(call, "tool", f"Stock checked — {item}", info["stock"] + " · " + info["market_price"])
    return result


@router.post("/place_order")
async def place_order(request: Request):
    business, call = _ctx(request)
    args = await _body(request)
    name = args.get("name") or args.get("customer_name") or "the customer"
    items = args.get("items") or args.get("order_details") or "the items discussed"
    delivery = args.get("delivery_time") or args.get("delivery_date") or "next delivery window"

    if business:
        services = business.get("services", [])
        if services:
            unknown = [
                w.strip() for w in items.lower().replace(",", " ").replace("and", " ").split()
                if not {s.lower().split(" ")[0] for s in services}.intersection(
                    {w.strip() if w.strip() else ""}
                ) and w.strip() not in {"lb", "lbs", "case", "cases", "flat", "flats", "of", "plus", "and", "some", "the", "a", "kg"}
            ]
            # Only reject when most words clearly aren't in the catalog.
            if unknown and sum(len(w) > 2 for w in unknown) >= 2:
                result = {
                    "success": False,
                    "message": f"I'm not finding those exact items on today's sheet. Confirm against the catalog: {', '.join(services[:6])}. Ask the caller to re-check.",
                }
                return result

        order = store.create_order(
            call or {"id": "unknown", "business_id": (business or {}).get("id")},
            customer_name=name,
            items=items[:280],
            delivery_time=delivery,
            channel="voice",
        )
        result = {
            "success": True,
            "order_id": order["id"],
            "message": f"Order confirmed for {name}: {items}, delivery {delivery}. Confirmation id {order['id']}.",
        }
        _log(call, "order", f"Wholesale order placed — {name}", f"{items} · {delivery} · {order['id'].upper()}")
    else:
        result = {"success": False, "message": "Business not found."}
    _record(call, "place_order", args, result)
    if call:
        store.update_call(call["id"], last_tool="place_order")
    return result


@router.post("/get_pricing_quote")
async def get_pricing_quote(request: Request):
    business, call = _ctx(request)
    args = await _body(request)
    name = args.get("name") or args.get("customer_name") or "the customer"
    items = args.get("items") or args.get("description") or "a wholesale order"
    volume = args.get("volume") or args.get("account_size") or "weekly volume"
    contact = args.get("phone") or args.get("contact") or "on file"

    quote = store.create_price_quote(
        call or {"id": "unknown", "business_id": (business or {}).get("id")},
        customer_name=name,
        items=items[:280],
        volume=volume[:80],
        contact=contact,
    )
    result = {
        "success": True,
        "quote_id": quote["id"],
        "message": f"Wholesale quote request {quote['id'].upper()} created for {name}: {items}, {volume}. Pricing will be sent before the next stop.",
    }
    _record(call, "get_pricing_quote", args, result)
    _log(call, "quote", "Bulk pricing quote requested", f"{name} · {items} · {volume} · {quote['id'].upper()}")
    return result


@router.post("/check_order")
async def check_order(request: Request):
    business, call = _ctx(request)
    args = await _body(request)
    order_id = str(args.get("order_id") or "GR-2045").upper()
    info = ORDER_BOOK.get(order_id)
    if not info:
        result = {"success": False, "message": f"Order {order_id} not found. Ask the caller to double-check the number on their invoice."}
    else:
        result = {"success": True, "order_id": order_id, "status": info["status"], "eta": info["window"], "items": info["items"]}
    _record(call, "check_order", args, result)
    _log(call, "order", f"Order {order_id} tracked", info.get("status", "") + " · " + info.get("window", ""))
    return result


@router.post("/cancel_order")
async def cancel_order(request: Request):
    business, call = _ctx(request)
    args = await _body(request)
    name = args.get("name") or "the customer"
    order_id = str(args.get("order_id") or "this order").upper()
    result = {
        "success": True,
        "message": f"Understood. {order_id} for {name} has been pulled from the load and cancelled. No penalty. We'll swing back next window.",
    }
    _record(call, "cancel_order", args, result)
    _log(call, "note", "Order cancelled", f"{name} · {order_id}")
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
        "message": "Confirmed. The produce manager will call back within 15 minutes. The issue is logged and flagged as urgent.",
    }
    _record(call, "escalate_to_human", args, result)
    _log(call, "escalation", "Escalated — manager callback queued", f"{reason[:80]} · {task['id'].upper()}")
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