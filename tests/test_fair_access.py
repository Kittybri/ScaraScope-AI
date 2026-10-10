import pytest
from scarascope.data.sec.fair_access import SECRequestGate

@pytest.mark.asyncio
async def test_sec_cache_and_expiry():
    gate=SECRequestGate(0)
    assert gate.get("x") is None
    gate.put("x",{"value":1},60)
    assert gate.get("x")=={"value":1}
    gate.put("y",{"value":2},-1)
    assert gate.get("y") is None

@pytest.mark.asyncio
async def test_sec_pacing_runs_without_external_network():
    gate=SECRequestGate(0.001)
    await gate.wait();await gate.wait()
