"""RingBack AI — main FastAPI application.

An AssemblyAI Voice Agent that calls small-business missed callers back and
actually gets things done (wholesale orders, stock checks, price quotes,
delivery tracking, human escalation) through server-side HTTP tools, then feeds
every outcome into a live owner dashboard powered by AssemblyAI session history
+ LLM Gateway analytics.

Server route map (all API routes are defined BEFORE the static mount):
  /api/*              - the JSON API
  /tools/*            - HTTP tools the AssemblyAI Voice Agent calls
  / (static)          - landing page + demo + assets
"""

from __future__ import annotations

import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import assemblyai as aai
from app.config import settings
from app.demo_data import BUSINESS_SEEDS, DEMO_SCENARIOS, DOMAIN_KEYTERMS, VOICE_SYSTEM_PROMPT
from app.store import store
from app.tools import router as tools_router

# --------------------------------------------------------------------------
# Tool blueprints attached to every stored agent
# --------------------------------------------------------------------------
def _tool(name: str, description: str, business_id: str, parameters: dict | None = None) -> dict:
    tool = {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": parameters or {"type": "object", "properties": {}},
        "execution_mode": "interactive",
        "timeout_seconds": 30,
        "http": {
            "url": f"{settings.public_base_url}/tools/{name}?business_id={business_id}",
            "http_method": "POST",
        },
    }
    return tool


def _arg(
    name: str,
    description: str,
    typ: str = "string",
    examples: list | None = None,
    enum: list | None = None,
    required: bool = True,
) -> tuple[str, dict]:
    prop: dict = {"type": typ, "description": description}
    if examples:
        prop["examples"] = examples
    if enum:
        prop["enum"] = enum
    return name, {"prop": prop, "required": required}


def _build_params(*args) -> dict:
    props: dict = {}
    required: list = []
    for name, spec in args:
        props[name] = spec["prop"]
        if spec["required"]:
            required.append(name)
    return {"type": "object", "properties": props, "required": required}


def business_toolset(business_id: str) -> list[dict]:
    return [
        _tool(
            "get_business_info",
            "Get this business's services, hours, address, and pricing. Call this BEFORE answering anything about hours, location, services, or prices — never guess.",
            business_id,
        ),
        _tool(
            "check_stock",
            "Check same-day stock and today's market price for an item on the produce sheet. Call BEFORE confirming any availability or price — never guess.",
            business_id,
            _build_params(
                _arg("item", "Item to check (e.g., romaine, avocados, strawberries)", examples=["heirloom tomatoes"]),
            ),
        ),
        _tool(
            "place_order",
            "Place a wholesale produce order and return a confirmation number. Confirm items, quantities, and the delivery window with the caller out loud first, then call this.",
            business_id,
            _build_params(
                _arg("name", "Caller's name"),
                _arg("items", "Items and quantities (e.g., '50 lb romaine, 3 cases avocados')"),
                _arg("delivery_time", "Delivery window", examples=["tomorrow morning"]),
            ),
        ),
        _tool(
            "get_pricing_quote",
            "Create a wholesale / bulk pricing quote request for a restaurant group, caterer, or store. Logs details and queues a pricing sheet. Use for volume pricing, case quotes, weekly orders.",
            business_id,
            _build_params(
                _arg("name", "Caller's name"),
                _arg("items", "What needs pricing (e.g., 'heirloom tomatoes + blueberries')"),
                _arg("volume", "Order volume or account size", examples=["6 locations, weekly"], required=False),
                _arg("phone", "Caller's callback number", required=False),
            ),
        ),
        _tool(
            "check_order",
            "Check the status of a delivery order reference number. Use when a caller references an order id on their invoice.",
            business_id,
            _build_params(_arg("order_id", "The order reference number", examples=["GR-2045"], pattern="[A-Z]{2}-\\d{4}")),
        ),
        _tool(
            "cancel_order",
            "Cancel an existing produce order before it leaves the loading dock. Only call after confirming with the caller and restating items and delivery window.",
            business_id,
            _build_params(
                _arg("name", "Caller's name"),
                _arg("order_id", "The order reference number", examples=["GR-2045"], required=False),
            ),
        ),
        _tool(
            "escalate_to_human",
            "Flag the call as URGENT and queue a manager callback. MUST use for: damaged or short deliveries, credit/refund requests, complaints about produce quality, requests for supervisor/produce manager/owner, legal threats, or anything complex or emotional.",
            business_id,
            _build_params(
                _arg("reason", "One-sentence summary of why a human is needed"),
                _arg("urgency", "Priority", enum=["low", "high"], examples=["high"]),
            ),
        ),
        _tool(
            "notify_owner",
            "Send the owner a quick SMS alert during a call.",
            business_id,
            _build_params(_arg("message", "Short alert message")),
        ),
    ]


def build_system_prompt(business: dict) -> str:
    return VOICE_SYSTEM_PROMPT.format(
        name=business.get("name", "the business"),
        services=", ".join(business.get("services", [])),
        hours=business.get("hours", "on listed business hours"),
        address=business.get("address", ""),
        service_note=business.get("service_note", ""),
        keywords=", ".join(DOMAIN_KEYTERMS),
    )


def provision_agent(business: dict, force: bool = False) -> dict:
    """Create (or update) the stored AssemblyAI voice agent for a business."""
    agent_id = business.get("agent_id")
    if agent_id and not force:
        try:
            aai.get_agent(agent_id)
            return business  # already provisioned
        except Exception:
            pass

    tools = business_toolset(business["id"])
    agent = aai.create_agent(
        name=f"RingBack - {business['name']}",
        system_prompt=build_system_prompt(business),
        business_id=business["id"],
        voice=settings.assemblyai_voice,
        greeting=business.get("greeting"),
        keyterms=DOMAIN_KEYTERMS,
        tools=tools,
    )
    return store.upsert_business({**business, "agent_id": agent["id"]})


def seed_demo_data() -> None:
    if not settings.seed_demo:
        return
    for seed in BUSINESS_SEEDS:
        existing = store.get_business(seed["id"])
        business = existing or store.upsert_business({**seed, "created_at": None})
        try:
            provision_agent(business)
        except Exception as exc:  # noqa: BLE001 - keep booting without a key
            business = store.get_business(seed["id"])
            business = store.upsert_business({**business, "provision_error": str(exc)[:200]})


@asynccontextmanager
async def lifespan(_: FastAPI):
    seed_demo_data()
    yield


app = FastAPI(title="RingBack AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tools_router)


# --------------------------------------------------------------------------
# Public config
# --------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ringback", "aa_configured": bool(settings.assemblyai_api_key)}


@app.get("/api/config")
def public_config():
    businesses = []
    for b in store.list_businesses():
        businesses.append(
            {
                "id": b["id"],
                "name": b["name"],
                "tagline": b.get("tagline", ""),
                "services": b.get("services", []),
                "agent_ready": bool(b.get("agent_id")),
            }
        )
    return {
        "app_name": settings.app_name,
        "tagline": settings.app_tagline,
        "scenarios": DEMO_SCENARIOS,
        "businesses": businesses,
        "aa_configured": bool(settings.assemblyai_api_key),
        "analytics_enabled": settings.analytics_model is not None,
        "avg_call_value": settings.avg_call_value,
    }


# --------------------------------------------------------------------------
# Agent management (the "2-minute setup" story)
# --------------------------------------------------------------------------
class BusinessIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    tagline: str = Field(default="", max_length=120)
    address: str = Field(default="", max_length=160)
    hours: str = Field(default="Monday-Friday 9 AM-5 PM", max_length=120)
    services: list[str] = Field(default=["general service"], max_length=12)
    greeting: str = Field(default="", max_length=300)


@app.post("/api/agents")
def create_business_agent(body: BusinessIn):
    business_id = "biz_" + "".join(c for c in body.name.lower() if c.isalnum())[:20]
    business = store.get_business(business_id)
    if business is None:
        business = store.upsert_business(
            {
                "id": business_id,
                "name": body.name,
                "tagline": body.tagline,
                "address": body.address,
                "hours": body.hours,
                "services": body.services,
                "service_note": "",
                "greeting": body.greeting or None,
            }
        )
        try:
            provision_agent(business)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"AssemblyAI agent provisioning failed: {exc}") from exc
        return {"business_id": business_id, "agent_id": business.get("agent_id"), "status": "provisioned"}

    updated = store.upsert_business({**business, "name": body.name, "tagline": body.tagline, "address": body.address, "hours": body.hours, "services": body.services})
    try:
        provision_agent(updated, force=True)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AssemblyAI agent provisioning failed: {exc}") from exc
    return {"business_id": business_id, "agent_id": updated.get("agent_id"), "status": "updated"}


@app.get("/api/agents")
def list_agent_status():
    out = []
    for b in store.list_businesses():
        out.append(
            {
                "business_id": b["id"],
                "name": b["name"],
                "agent_id": b.get("agent_id"),
                "ready": bool(b.get("agent_id")),
                "provision_error": b.get("provision_error"),
            }
        )
    return {"agents": out}


class TokenIn(BaseModel):
    business_id: str


@app.post("/api/token")
def mint_voice_token(body: TokenIn):
    """Mint a one-time temporary token so the browser can open the Voice Agent
    WebSocket without ever seeing the API key."""
    business = store.get_business(body.business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    if not business.get("agent_id"):
        try:
            provision_agent(business)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Agent not provisioned: {exc}") from exc
    token = aai.mint_token(
        expires_in_seconds=settings.token_ttl_seconds,
        max_session_duration_seconds=settings.max_session_seconds,
    )
    return {
        "token": token,
        "agent_id": business.get("agent_id"),
        "expires_in_seconds": settings.token_ttl_seconds,
        "max_session_duration_seconds": settings.max_session_seconds,
    }


# --------------------------------------------------------------------------
# Call lifecycle
# --------------------------------------------------------------------------
class SimulateCallIn(BaseModel):
    scenario_id: str
    customer_name: str = Field(default="", max_length=80)
    phone: str = Field(default="", max_length=40)


@app.post("/api/simulate-call")
def simulate_call(body: SimulateCallIn):
    scenario = next((s for s in DEMO_SCENARIOS if s["id"] == body.scenario_id), None)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    business = store.get_business(scenario["business_id"])
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    call = store.create_call(
        scenario["business_id"],
        scenario_id=scenario["id"],
        scenario_title=scenario["title"],
        customer_name=body.customer_name or scenario["customer_name"],
        phone=body.phone or scenario["phone"],
        topic=scenario["description"],
        first_line=scenario["first_line"],
        business_name=business["name"],
    )
    store.add_call_event(call["id"], "missed", f"Missed call detected", f"{call['phone']} tried {business['name']}'s line for 12s")
    store.add_call_event(call["id"], "callback", "RingBack dialing caller", "Took over in 3.2s after the missed call")
    return call


@app.post("/api/calls/{call_id}/answer")
def answer_call(call_id: str):
    call = store.get_call(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    call = store.update_call(call_id, status="talking", answered_at=time.strftime("%Y-%m-%d %H:%M:%S"))
    store.add_call_event(call_id, "connect", "Caller answered, voice agent live", "Streaming via AssemblyAI Voice Agent API")
    return call


class TranscriptIn(BaseModel):
    transcript: list[dict] = Field(default_factory=list)
    aa_session_id: str = Field(default="", max_length=120)
    duration_s: float | None = None


@app.post("/api/calls/{call_id}/transcript")
def end_call_with_transcript(call_id: str, body: TranscriptIn):
    call = store.get_call(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    duration = body.duration_s if body.duration_s is not None else len(body.transcript) * 6
    fields = {
        "transcript": body.transcript,
        "aa_session_id": body.aa_session_id or call.get("aa_session_id"),
        "status": "completed" if not call.get("needs_human") else "escalated",
        "ended_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_s": round(duration, 1),
    }
    call = store.finish_call(call_id, **fields)
    store.add_call_event(call_id, "complete", "Call completed" + (" — escalated to human" if fields["status"] == "escalated" else ""), f"{round(duration,1)}s conversation")
    if fields["aa_session_id"]:
        threading.Thread(target=_analyze, args=(call_id,), daemon=True).start()
    return call


def _analyze(call_id: str) -> None:
    call = store.get_call(call_id)
    if not call:
        return
    result = aai.analyze_transcript(call.get("transcript", []), call.get("business_name", "the business"))
    if not result:
        store.add_call_event(call_id, "note", "Analytics pending", "Transcript captured; LLM Gateway skipped")
        return
    store.update_call(
        call_id,
        summary=result.get("summary"),
        sentiment=result.get("sentiment"),
        intent=result.get("intent"),
        action_items=result.get("action_items", []),
        needs_human=(call.get("needs_human") or result.get("needs_human", False)),
    )
    store.add_call_event(call_id, "analytics", f"Call analyzed — {result.get('sentiment','?')}", result.get("summary", "")[:160])


@app.get("/api/calls/{call_id}")
def get_call(call_id: str):
    call = store.get_call(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


# --------------------------------------------------------------------------
# Owner dashboard
# --------------------------------------------------------------------------
@app.get("/api/calls")
def list_calls(limit: int = 30):
    return {"calls": store.list_calls(limit)}


@app.get("/api/dashboard")
def dashboard():
    return store.dashboard_metrics(avg_call_value=settings.avg_call_value)


@app.get("/api/orders")
def orders(limit: int = 20):
    return {"orders": store.list_orders(limit)}


@app.get("/api/quotes")
def quotes(limit: int = 20):
    return {"quotes": store.list_quotes(limit)}


@app.get("/api/tasks")
def tasks(limit: int = 20):
    return {"tasks": store.list_tasks(limit)}


# --------------------------------------------------------------------------
# AssemblyAI session history (recordings + timelines)
# --------------------------------------------------------------------------
@app.get("/api/sessions")
def sessions(limit: int = 20):
    try:
        sessions = aai.list_sessions(limit=max(1, min(limit, 100)))
    except Exception:
        return {"sessions": []}
    return {"sessions": sessions}


@app.get("/api/sessions/{session_id}")
def session_detail(session_id: str):
    try:
        return aai.get_session(session_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# --------------------------------------------------------------------------
# Static frontend (mounted last so it can't shadow the API)
# --------------------------------------------------------------------------
from fastapi.responses import FileResponse as _FileResponse


@app.get("/demo", include_in_schema=False)
def demo_page():
    return _FileResponse("public/demo.html")


app.mount("/", StaticFiles(directory="public", html=True), name="static")


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=False)


if __name__ == "__main__":
    main()