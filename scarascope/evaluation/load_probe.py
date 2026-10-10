"""Bounded, opt-in loopback load probe for reproducible demo API latency.

No outbound targets, price claims or uncontrolled traffic. A local or injected
ASGI transport is required. This is not a production load test.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
from statistics import median
from time import perf_counter
from urllib.parse import urlparse
import httpx


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = math.ceil(percentile * len(ordered)) - 1
    return round(ordered[max(0, rank)], 3)


async def probe_local_api(*, url: str = "http://127.0.0.1:8000", requests: int = 20,
                          concurrency: int = 2, transport: httpx.AsyncBaseTransport | None = None,
                          endpoint: str = "/api/demo") -> dict:
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"} \
            or parsed.username or parsed.password or parsed.path not in {"", "/"} \
            or parsed.query or parsed.fragment or parsed.port is None:
        raise ValueError("Load probe accepts only explicit localhost HTTP URLs with a port.")
    if not 1 <= requests <= 100 or not 1 <= concurrency <= 8:
        raise ValueError("Use 1–100 requests and 1–8 concurrent workers.")
    if endpoint not in {"/api/health", "/api/demo"}:
        raise ValueError("Only public, deterministic read-only demo endpoints may be probed.")
    semaphore = asyncio.Semaphore(concurrency)
    records: list[tuple[int | None, float]] = []
    key = os.getenv('SCARASCOPE_API_KEY', '').strip()
    headers = {'X-API-Key': key} if key else {}
    async with httpx.AsyncClient(base_url=url, timeout=8.0, transport=transport, headers=headers,
                                 follow_redirects=False) as client:
        async def one():
            async with semaphore:
                start = perf_counter()
                status = None
                try:
                    response = await client.get(endpoint)
                    status = response.status_code
                except httpx.RequestError:
                    pass
                records.append((status, (perf_counter() - start) * 1000))
        began = perf_counter()
        await asyncio.gather(*(one() for _ in range(requests)))
        elapsed = perf_counter() - began
    latencies = [timing for _, timing in records]
    errors = sum(status is None or status >= 400 for status, _ in records)
    return {'target': 'loopback-only', 'endpoint': endpoint, 'requests': len(records),
            'concurrency': concurrency, 'errors': errors,
            'success_rate': round((len(records)-errors)/len(records), 4),
            'latency_ms': {'p50': round(median(latencies),3), 'p95': _percentile(latencies,0.95),
                           'max': round(max(latencies),3)},
            'throughput_requests_per_second': round(len(records)/max(elapsed, 0.000001),3),
            'limitations': 'Loopback demo endpoint only. Does not measure live SEC, LLM generation, provider costs or production scalability.'}


def main():
    parser = argparse.ArgumentParser(description='ScaraScope bounded localhost API probe')
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--requests', type=int, default=20)
    parser.add_argument('--concurrency', type=int, default=2)
    parser.add_argument('--endpoint', choices=['/api/demo','/api/health'], default='/api/demo')
    args = parser.parse_args()
    print(json.dumps(asyncio.run(probe_local_api(url=args.url, requests=args.requests,
                          concurrency=args.concurrency, endpoint=args.endpoint)), indent=2))


if __name__ == '__main__':
    main()
