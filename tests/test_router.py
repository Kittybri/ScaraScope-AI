import pytest

from scarascope.core.config import Settings
from scarascope.core.models import ResearchRequest
from scarascope.ai.providers.base import ProviderError
from scarascope.ai.router import ModelRouter, is_complex


class FakeProvider:
    def __init__(self, answer=None):
        self.answer = answer
        self.calls = 0
    async def generate(self, system, prompt):
        self.calls += 1
        if self.answer is None:
            raise ProviderError("offline")
        return self.answer


def settings(**kwargs):
    return Settings(ollama_enabled=True, groq_api_key="test-key", **kwargs)


@pytest.mark.asyncio
async def test_auto_simple_uses_ollama():
    local, cloud = FakeProvider("from local"), FakeProvider("from cloud")
    result = await ModelRouter(settings(), local, cloud).explain(ResearchRequest(ticker="MSFT"), "system", "prompt", "rules")
    assert result.provider == "ollama"
    assert local.calls == 1 and cloud.calls == 0


@pytest.mark.asyncio
async def test_local_timeout_falls_back_to_groq():
    local, cloud = FakeProvider(), FakeProvider("from cloud")
    result = await ModelRouter(settings(), local, cloud).explain(ResearchRequest(ticker="MSFT"), "system", "prompt", "rules")
    assert result.provider == "groq" and result.fallback_used
    assert local.calls == cloud.calls == 1


@pytest.mark.asyncio
async def test_local_only_never_sends_to_groq():
    local, cloud = FakeProvider(), FakeProvider("private data leaked")
    req = ResearchRequest(ticker="MSFT", privacy="local_only", question="complex financial scenario valuation")
    result = await ModelRouter(settings(), local, cloud).explain(req, "system", "private data", "rules")
    assert result.provider == "deterministic"
    assert "privacy" in result.note.lower()
    assert cloud.calls == 0


@pytest.mark.asyncio
async def test_complex_prefers_cloud_then_local_on_failure():
    local, cloud = FakeProvider("local fallback"), FakeProvider()
    req = ResearchRequest(ticker="MSFT", question="compare detailed financial trends")
    result = await ModelRouter(settings(), local, cloud).explain(req, "sys", "prompt", "rules")
    assert is_complex(req.question, 3)
    assert result.provider == "ollama" and result.fallback_used
    assert cloud.calls == local.calls == 1


@pytest.mark.asyncio
async def test_unconfigured_providers_use_rule_based():
    result = await ModelRouter(Settings(ollama_enabled=False, groq_api_key="")).explain(ResearchRequest(ticker="MSFT"), "system", "prompt", "rule-based")
    assert result.provider == "deterministic" and result.text == "rule-based"


@pytest.mark.asyncio
async def test_cloud_forbidden_under_local_only():
    with pytest.raises(ValueError, match="local-only"):
        await ModelRouter(settings()).explain(ResearchRequest(ticker="MSFT", provider="cloud", privacy="local_only"), "sys", "prompt", "rules")
