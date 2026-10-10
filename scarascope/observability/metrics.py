"""In-process, non-sensitive operational counters for portfolio demonstrations."""
from collections import Counter, deque
from threading import Lock
from datetime import datetime, timezone

_lock = Lock()
_counters = Counter()
_recent = deque(maxlen=60)

def record(event: str, *, provider: str = "", milliseconds: float | None = None):
    # Never collect prompts, responses, user identifiers, or credentials here.
    with _lock:
        _counters[event] += 1
        _recent.append({"at":datetime.now(timezone.utc).isoformat(), "event":event,
                        "provider":provider,"latency_ms":round(milliseconds,2) if milliseconds is not None else None})

def snapshot() -> dict:
    with _lock:
        return {"counters":dict(_counters),"recent":list(_recent),
                "note":"Per-process diagnostic counters. Reset on restart; do not contain research text or API keys."}
