"""Conservative per-process SEC pacing and TTL cache.

Not a distributed limiter; deployments with multiple workers need centralized coordination.
"""
import asyncio
import time
from typing import Any

class SECRequestGate:
    def __init__(self, min_spacing_seconds: float = 0.4):
        self.min_spacing_seconds = min_spacing_seconds
        self._lock=asyncio.Lock()
        self._last=0.0
        self._cache: dict[str,tuple[float,dict[str,Any]]] = {}

    async def wait(self):
        async with self._lock:
            now=time.monotonic()
            delay=self.min_spacing_seconds - (now-self._last)
            if delay>0:await asyncio.sleep(delay)
            self._last=time.monotonic()

    def get(self,url: str) -> dict | None:
        hit=self._cache.get(url)
        if hit and hit[0]>time.monotonic():
            return hit[1]
        self._cache.pop(url,None)
        return None

    def put(self,url: str,document:dict,ttl_seconds:float):
        if len(self._cache)>64:
            self._cache.clear()
        self._cache[url]=(time.monotonic()+ttl_seconds,document)

SEC_GATE=SECRequestGate()
