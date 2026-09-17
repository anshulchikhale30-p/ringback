"""Thin client for the AssemblyAI Voice Agent API + LLM Gateway.

Everything in this module talks directly to AssemblyAI's REST/WebSocket
platform. The demo uses it for:
  * temporary-token minting (secure browser connections, no key leak),
  * stored voice-agent create/list/update (per-business agents),
  * session history + artifacts after a call (recording + timeline),
  * LLM Gateway analytics (summary / sentiment / intent / action items)
    generated from the live conversation.

Tool URLs point back at THIS server. AssemblyAI calls them server-side with the
model's arguments as a JSON body, so the business id is pinned as a query
param on each tool URL (query params in a tool url and the model's JSON args
are merged by the platform).
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from app.config import settings


def _headers() -> dict[str, str]:
    return {"Authorization": settings.assemblyai_api_key or ""}


def _auth_ok(resp: httpx.Response) -> bool:
    return resp.status_code in (200, 201)


# --------------------------------------------------------------------------
# Agents
# --------------------------------------------------------------------------
def tool_url(name: str, business_id: str, http_method: str = "POST") -> dict:
    """An AssemblyAI server-side HTTP tool pointed at this server."""
    return {
        "name": name,
        "description": "",
        "http": {
            "url": f"{settings.public_base_url}/tools/{name}?business_id={business_id}",
            "http_method": http_method,
        },
    }


def create_agent(
    name: str,
    system_prompt: str,
    business_id: str,
    voice: str | None = None,
    greeting: str | None = None,
    keyterms: list[str] | None = None,
    tools: list[dict] | None = None,
) -> dict:
    payload: dict[str, Any] = {
        "name": name,
        "system_prompt": system_prompt,
        "voice": {"voice_id": voice or settings.assemblyai_voice},
    }
    if greeting:
        payload["greeting"] = greeting
    if keyterms:
        payload["input"] = {"keyterms": keyterms}
    if tools:
        payload["tools"] = tools
    if not settings.public_base_url:
        # Tool URLs cannot be empty; drop tools until a public URL is set.
        payload.pop("tools", None)
    resp = httpx.post(
        f"{settings.agent_base_url}/v1/agents",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    if not _auth_ok(resp):
        raise RuntimeError(f"create_agent failed: {resp.status_code} {resp.text[:400]}")
    return resp.json()


def update_agent(agent_id: str, **fields: Any) -> dict:
    resp = httpx.put(
        f"{settings.agent_base_url}/v1/agents/{agent_id}",
        headers=_headers(),
        json=fields,
        timeout=30,
    )
    if not _auth_ok(resp):
        raise RuntimeError(f"update_agent failed: {resp.status_code} {resp.text[:400]}")
    return resp.json()


def get_agent(agent_id: str) -> dict:
    resp = httpx.get(
        f"{settings.agent_base_url}/v1/agents/{agent_id}",
        headers=_headers(),
        timeout=30,
    )
    return resp.json()


def list_agents() -> list[dict]:
    resp = httpx.get(
        f"{settings.agent_base_url}/v1/agents",
        headers=_headers(),
        timeout=30,
    )
    if not _auth_ok(resp):
        return []
    return resp.json().get("agents", resp.json().get("data", []))


# --------------------------------------------------------------------------
# Tokens (secure browser connections)
# --------------------------------------------------------------------------
def mint_token(expires_in_seconds: int = 300, max_session_duration_seconds: int = 900) -> str:
    resp = httpx.get(
        f"{settings.agent_base_url}/v1/token",
        params={
            "expires_in_seconds": expires_in_seconds,
            "max_session_duration_seconds": max_session_duration_seconds,
        },
        headers=_headers(),
        timeout=30,
    )
    if not _auth_ok(resp):
        raise RuntimeError(f"mint_token failed: {resp.status_code} {resp.text[:400]}")
    return resp.json()["token"]


# --------------------------------------------------------------------------
# Session history (recording + timeline via AssemblyAI)
# --------------------------------------------------------------------------
def list_sessions(limit: int = 25, agent_id: str | None = None) -> list[dict]:
    params: dict[str, Any] = {"limit": min(limit, 200)}
    if agent_id:
        params["agent_id"] = agent_id
    resp = httpx.get(
        f"{settings.agent_base_url}/v1/sessions",
        params=params,
        headers=_headers(),
        timeout=30,
    )
    if not _auth_ok(resp):
        return []
    return resp.json().get("sessions", [])


def get_session(session_id: str) -> dict:
    resp = httpx.get(
        f"{settings.agent_base_url}/v1/sessions/{session_id}",
        headers=_headers(),
        timeout=30,
    )
    if not _auth_ok(resp):
        raise RuntimeError(f"get_session failed: {resp.status_code} {resp.text[:400]}")
    data = resp.json()
    artifacts = {a.get("type"): a.get("url") for a in data.get("artifacts", [])}
    data["artifacts_map"] = artifacts
    return data


# --------------------------------------------------------------------------
# LLM Gateway (post-call analytics on the live transcript)
# --------------------------------------------------------------------------
def chat_json(
    messages: list[dict[str, str]],
    schema: dict[str, Any],
    model: str | None = None,
    max_tokens: int = 700,
) -> dict | None:
    """Structured chat completion through AssemblyAI's LLM Gateway.

    Returns parsed JSON, or None if the call fails (the app is designed to
    degrade gracefully).
    """
    payload = {
        "model": model or settings.analytics_model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": schema.get("name", "result"), "schema": schema, "strict": True},
        },
    }
    for auth in (settings.assemblyai_api_key, f"Bearer {settings.assemblyai_api_key}"):
        if not auth:
            continue
        try:
            resp = httpx.post(
                f"{settings.llm_gateway_url}/chat/completions",
                headers={"Authorization": auth},
                json=payload,
                timeout=60,
            )
            if resp.status_code == 401 and auth == settings.assemblyai_api_key:
                continue
            if resp.status_code != 200:
                return None
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception:
            return None
    return None


ANALYTICS_SCHEMA: dict[str, Any] = {
    "name": "call_analytics",
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "One or two sentence summary of the call."},
        "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
        "intent": {
            "type": "string",
            "enum": [
                "booking",
                "quote",
                "order_status",
                "support",
                "complaint",
                "information",
                "other",
            ],
        },
        "action_items": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Concrete follow-up actions the business must take.",
        },
        "needs_human": {
            "type": "boolean",
            "description": "True if a human should call back (complaints, cancellations, complex issues).",
        },
        "customer_name": {"type": "string", "description": "Customer name if mentioned, else empty string."},
    },
    "required": [
        "summary",
        "sentiment",
        "intent",
        "action_items",
        "needs_human",
        "customer_name",
    ],
    "additionalProperties": False,
}


def analyze_transcript(transcript: list[dict], business_name: str) -> dict | None:
    if not transcript:
        return None
    lines = "\n".join(f"[{m.get('role')}] {m.get('text')}" for m in transcript)
    messages = [
        {
            "role": "system",
            "content": (
                "You analyze phone calls answered by an AI voice agent for a small business. "
                "Return strict JSON per the provided schema. Be concise and actionable."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Business: {business_name}\n\n"
                "Conversation transcript:\n"
                f"{lines}\n\n"
                "Analyze the call."
            ),
        },
    ]
    return chat_json(messages, ANALYTICS_SCHEMA)


def wait_or_zero():
    return time.time()