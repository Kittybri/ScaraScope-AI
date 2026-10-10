"""Small per-process demo request limiter; not distributed abuse protection."""
from collections import deque
from threading import Lock
from time import monotonic

class RequestLimiter:
    def __init__(self):
        self._lock = Lock()
        self._buckets: dict[str, deque[float]]={}

    def allow(self, identity: str, limit: int) -> bool:
        now=monotonic()
        with self._lock:
            # Bound total identities and memory for demonstration deployments.
            if len(self._buckets)>1500:
                self._buckets={k:v for k,v in self._buckets.items() if v and now-v[-1]<60}
            if len(self._buckets)>2000 and identity not in self._buckets:
                return False
            times=self._buckets.setdefault(identity,deque())
            while times and now-times[0]>=60:
                times.popleft()
            if len(times)>=limit:
                return False
            times.append(now)
            return True

limiter=RequestLimiter()
