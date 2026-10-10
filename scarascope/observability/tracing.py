"""Bounded, process-local API request diagnostics without sensitive content.

No request bodies, prompts, URL query strings, client IP addresses, auth
headers, filing excerpts or secrets are recorded. Restart clears history.
"""
from __future__ import annotations

from collections import Counter, deque
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from math import ceil
from threading import Lock
from uuid import uuid4

_current_run: ContextVar[str | None] = ContextVar("scarascope_run_id", default=None)
_lock = Lock()
_recent: deque[dict] = deque(maxlen=100)


def create_request_id() -> str:
    return "rs_" + uuid4().hex


def request_id() -> str | None:
    return _current_run.get()


def begin_request(value: str) -> Token:
    return _current_run.set(value)


def end_request(token: Token) -> None:
    _current_run.reset(token)


def record_http(run_id: str, route: str, method: str, status: int, duration_ms: float) -> None:
    # Caller must supply an allowlisted route template, not raw request paths.
    route = route.split("?", 1)[0].split("#", 1)[0]
    if not route.startswith("/api/"):
        route = "unknown"
    event = {
        "run_id": run_id,
        "at": datetime.now(timezone.utc).isoformat(),
        "route": route[:110],
        "method": method if method in {"GET", "POST", "PUT", "PATCH", "DELETE"} else "OTHER",
        "status_code": int(status),
        "latency_ms": round(max(0.0, duration_ms), 3),
    }
    with _lock:
        _recent.append(event)


def _percentile(values: list[float], percentage: float) -> float | None:
    if not values:
        return None
    return round(sorted(values)[max(0, ceil(percentage / 100 * len(values)) - 1)], 3)


def trace_snapshot(limit: int = 20) -> dict:
    with _lock:
        recent = list(_recent)
    by_status = Counter(
        "server_error" if r["status_code"] >= 500 else
        "client_error" if r["status_code"] >= 400 else "ok" for r in recent
    )
    latencies = [r["latency_ms"] for r in recent]
    return {
        "sample_size": len(recent),
        "status_counts": dict(by_status),
        "p50_ms": _percentile(latencies, 50),
        "p95_ms": _percentile(latencies, 95),
        "recent": list(reversed(recent[-max(1, min(limit, 50)):])),
        "scope": "Last 100 API requests in this process only. No retention or cross-worker aggregation.",
        "privacy": "No request payload, query string, IP, prompt, token, or full response is retained.",
    }
