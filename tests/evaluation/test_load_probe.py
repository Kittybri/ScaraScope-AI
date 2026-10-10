"""Ensure the optional load test remains bounded, deterministic and loopback-only."""
import pytest
import httpx
from scarascope.api import app
from scarascope.evaluation.load_probe import probe_local_api


@pytest.mark.asyncio
async def test_probe_measures_real_asgi_demo_without_outbound_requests():
    results = await probe_local_api(url='http://127.0.0.1:8000',requests=8,
            concurrency=2,transport=httpx.ASGITransport(app=app))
    assert results['requests']==8
    assert results['errors']==0
    assert results['success_rate']==1
    assert results['latency_ms']['p95'] >= 0
    assert results['throughput_requests_per_second'] > 0
    assert 'Does not measure' in results['limitations']


@pytest.mark.asyncio
@pytest.mark.parametrize('url', [
    'https://www.google.com:443','http://www.sec.gov:80','http://192.168.1.1:8000',
    'http://localhost:8000/evil','http://127.0.0.1:8000@evil.example:80',
    'http://localhost:8000?forward=https://example.com','http://127.0.0.1',
])
async def test_probe_refuses_nonlocal_targets(url):
    with pytest.raises(ValueError,match='localhost'):
        await probe_local_api(url=url,requests=1)


@pytest.mark.asyncio
async def test_probe_rejects_unbounded_workloads():
    with pytest.raises(ValueError,match='100'):
        await probe_local_api(requests=101)
    with pytest.raises(ValueError,match='workers'):
        await probe_local_api(concurrency=9)
    with pytest.raises(ValueError,match='read-only'):
        await probe_local_api(endpoint='/api/documents/ask')
