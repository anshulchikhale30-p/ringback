"""Tiny JSON-file-backed store.

Good enough for a hackathon: fast to build, survives app restarts on the
free tier, and keeps all demo data on the server so the owner dashboard can
animate in real time while a call is live.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from typing import Any


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


class Store:
    def __init__(self, path: str = "data/store.json") -> None:
        self.path = path
        self.lock = threading.RLock()
        self.data: dict[str, Any] = {
            "businesses": {},
            "calls": {},
            "orders": [],
            "quotes": [],
            "tasks": [],
            "active_call_by_business": {},
        }
        self._load()

    # ---- persistence ------------------------------------------------------
    def _load(self) -> None:
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
        except Exception:  # pragmatic: never crash on a corrupt file
            self.data.update(
                {
                    "businesses": {},
                    "calls": {},
                    "orders": [],
                    "quotes": [],
                    "tasks": [],
                    "active_call_by_business": {},
                }
            )

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, default=str)
        os.replace(tmp, self.path)

    # ---- helpers ----------------------------------------------------------
    def new_id(self, prefix: str = "id") -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    # ---- businesses -------------------------------------------------------
    def upsert_business(self, business: dict) -> dict:
        with self.lock:
            bid = business["id"]
            existing = self.data["businesses"].get(bid)
            merged = {**(existing or {}), **business}
            merged["updated_at"] = _now()
            self.data["businesses"][bid] = merged
            self._save()
            return merged

    def get_business(self, business_id: str) -> dict | None:
        with self.lock:
            return self.data["businesses"].get(business_id)

    def list_businesses(self) -> list[dict]:
        with self.lock:
            return [dict(b) for b in self.data["businesses"].values()]

    # ---- calls ------------------------------------------------------------
    def create_call(self, business_id: str, **fields: Any) -> dict:
        call_id = self.new_id("call")
        with self.lock:
            call = {
                "id": call_id,
                "business_id": business_id,
                "status": "ringing",
                "created_at": _now(),
                "answered_at": None,
                "ended_at": None,
                "duration_s": None,
                "events": [],
                "tool_calls": [],
                "transcript": [],
                "summary": None,
                "sentiment": None,
                "intent": None,
                "action_items": [],
                "needs_human": False,
                "order_id": None,
                "quote_id": None,
                "aa_session_id": None,
                **fields,
            }
            self.data["calls"][call_id] = call
            self.data["active_call_by_business"][business_id] = call_id
            self._save()
            return dict(call)

    def get_call(self, call_id: str) -> dict | None:
        with self.lock:
            c = self.data["calls"].get(call_id)
            return dict(c) if c else None

    def update_call(self, call_id: str, **fields: Any) -> dict | None:
        with self.lock:
            call = self.data["calls"].get(call_id)
            if call is None:
                return None
            call.update(fields)
            self._save()
            return dict(call)

    def add_call_event(self, call_id: str, type_: str, title: str, detail: str = "") -> dict | None:
        with self.lock:
            call = self.data["calls"].get(call_id)
            if call is None:
                return None
            event = {"t": _now(), "type": type_, "title": title, "detail": detail}
            call["events"].append(event)
            self._save()
            return dict(call)

    def add_tool_call(self, call_id: str, name: str, args: dict, result: dict) -> None:
        with self.lock:
            call = self.data["calls"].get(call_id)
            if call is None:
                return
            call["tool_calls"].append(
                {
                    "t": _now(),
                    "name": name,
                    "args": args,
                    "result": result,
                }
            )
            self._save()

    def active_call_for(self, business_id: str) -> dict | None:
        with self.lock:
            call_id = self.data["active_call_by_business"].get(business_id)
            if not call_id:
                return None
            return self.get_call(call_id)

    def finish_call(self, call_id: str, **fields: Any) -> dict | None:
        with self.lock:
            call = self.data["calls"].get(call_id)
            if call is None:
                return None
            call.update(fields)
            self._clear_active(call)
            self._save()
            return dict(call)

    def _clear_active(self, call: dict) -> None:
        bid = call.get("business_id")
        if bid and self.data["active_call_by_business"].get(bid) == call["id"]:
            del self.data["active_call_by_business"][bid]

    # ---- derived records ----------------------------------------------------
    def create_order(self, call: dict, **fields: Any) -> dict:
        order_id = self.new_id("ord")
        with self.lock:
            order = {
                "id": order_id,
                "call_id": call["id"],
                "business_id": call.get("business_id"),
                "created_at": _now(),
                "status": "confirmed",
                **fields,
            }
            self.data["orders"].append(order)
            existing_call = self.data["calls"].get(call["id"])
            if existing_call is not None:
                existing_call["order_id"] = order_id
            self._save()
            return dict(order)

    def create_price_quote(self, call: dict, **fields: Any) -> dict:
        quote_id = self.new_id("qt")
        with self.lock:
            quote = {
                "id": quote_id,
                "call_id": call["id"],
                "business_id": call.get("business_id"),
                "created_at": _now(),
                "status": "pending_approval",
                **fields,
            }
            self.data["quotes"].append(quote)
            existing_call = self.data["calls"].get(call["id"])
            if existing_call is not None:
                existing_call["quote_id"] = quote_id
            self._save()
            return dict(quote)

    def create_task(self, call: dict, **fields: Any) -> dict:
        task_id = self.new_id("task")
        with self.lock:
            task = {
                "id": task_id,
                "call_id": call["id"],
                "business_id": call.get("business_id"),
                "created_at": _now(),
                "status": "open",
                **fields,
            }
            self.data["tasks"].append(task)
            self._save()
            return dict(task)

    # ---- dashboards ---------------------------------------------------------
    def list_calls(self, limit: int = 30) -> list[dict]:
        with self.lock:
            calls = [dict(c) for c in self.data["calls"].values()]
        calls.sort(key=lambda c: c.get("created_at") or "", reverse=True)
        return calls[:limit]

    def list_orders(self, limit: int = 20) -> list[dict]:
        with self.lock:
            o = [dict(x) for x in self.data["orders"]]
        o.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return o[:limit]

    def list_price_quotes(self, limit: int = 20) -> list[dict]:
        with self.lock:
            q = [dict(x) for x in self.data["quotes"]]
        q.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return q[:limit]

    def list_tasks(self, limit: int = 20) -> list[dict]:
        with self.lock:
            t = [dict(x) for x in self.data["tasks"]]
        t.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return t[:limit]

    def dashboard_metrics(self, avg_call_value: int = 125) -> dict:
        with self.lock:
            calls = list(self.data["calls"].values())
            orders = list(self.data["orders"])
            quotes = list(self.data["quotes"])
            tasks = [t for t in self.data["tasks"] if t.get("status") == "open"]
        completed = [c for c in calls if c.get("status") in ("completed", "escalated")]
        recovered = [c for c in completed if not c.get("needs_human")]
        sentiments = [c.get("sentiment") for c in completed if c.get("sentiment")]
        positive = sentiments.count("positive")
        revenue = len(recovered) * avg_call_value
        return {
            "calls_handled": len(completed),
            "calls_total": len(calls),
            "orders": len(orders),
            "quotes": len(quotes),
            "open_tasks": len(tasks),
            "positive_sentiment": positive,
            "sentiment_total": len(sentiments),
            "revenue_saved": revenue,
            "avg_call_value": avg_call_value,
        }


store = Store(os.getenv("RINGBACK_DATA_FILE", "data/store.json"))