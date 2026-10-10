"""No fake provider results are described as live runs."""
from __future__ import annotations
import pytest
from scarascope.evaluation.provider_probe import measure_provider, _percentile
from scarascope.ai.providers.base import ProviderError


class StubProvider:
    def __init__(self): self.times=0
    async def generate(self,system,prompt):
        self.times+=1
        if self.times==2: raise ProviderError("deliberate outage")
        return "4"


@pytest.mark.asyncio
async def test_probe_separates_success_and_failure_without_storing_outputs():
    p=StubProvider()
    report=await measure_provider(p,name="ollama",model="test-only-model",iterations=3)
    assert p.times==3 and report['invocations']==3 and report['successful']==2
    assert report['cost_usd'] is None and report['answer_accuracy'] is None
    assert all('output' not in row and 'prompt' not in row for row in report['cases'])
    assert report['p50_success_ms'] is not None
    with pytest.raises(ValueError):
        await measure_provider(p,name="groq",model="test-only-model",iterations=6)


def test_percentile_nearest_rank():
    assert _percentile([4,1,3,2],0.5)==2
    assert _percentile([4,1,3,2],0.95)==4
    assert _percentile([],0.95) is None


def test_live_probe_cli_refuses_nonconsensual_calls(monkeypatch):
    import sys
    from scarascope.evaluation.provider_probe import main
    for args in [
        ['probe','--provider','cloud'],
        ['probe','--provider','cloud','--confirm-live'],
        ['probe','--provider','local','--confirm-live','--iterations','6']
    ]:
        monkeypatch.setattr(sys,'argv',args)
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code!=0
