"""Reproducible dependency-free provider-outage checks; credentials never used."""
from ..ai.providers.base import ProviderError
from ..ai.router import ModelRouter
from ..core.config import Settings
from ..core.models import ResearchRequest


class _Stub:
    def __init__(self, answer: str | None):
        self.answer = answer
        self.calls = 0

    async def generate(self, system: str, prompt: str) -> str:
        self.calls += 1
        if self.answer is None:
            raise ProviderError("simulated provider outage")
        return self.answer


async def run_reliability_checks() -> dict:
    settings = Settings(ollama_enabled=True, groq_api_key="non-secret-fixture")
    cases = [
        ("prefer_local", "auto", "cloud_ok", "local-response", "cloud-response", "ollama", 0),
        ("local_outage_cloud_fallback", "auto", "cloud_ok", None, "cloud-response", "groq", 1),
        ("local_only_outage_no_leak", "auto", "local_only", None, "cloud-response", "deterministic", 0),
        ("cloud_outage_local_fallback", "cloud", "cloud_ok", "local-response", None, "ollama", 1),
        ("both_providers_unavailable", "auto", "cloud_ok", None, None, "deterministic", 1),
    ]
    outcomes = []
    for label, preference, privacy, local_value, cloud_value, expected, cloud_calls in cases:
        local, cloud = _Stub(local_value), _Stub(cloud_value)
        request = ResearchRequest(ticker="DEMO", provider=preference, privacy=privacy, question="Summarize the given facts")
        result = await ModelRouter(settings, local=local, cloud=cloud, record_metrics=False).explain(request, "system", "sensitive fixture", "safe fallback")
        passed = result.provider == expected and cloud.calls == cloud_calls
        if label == "local_only_outage_no_leak":
            passed = passed and result.text == "safe fallback" and local.calls == 1
        outcomes.append({"id":label,"expected_provider":expected,"observed_provider":result.provider,
                         "cloud_calls":cloud.calls,"passed":passed})
    # A policy conflict must fail before contacting either provider.
    local, cloud = _Stub("local"), _Stub("cloud")
    blocked = False
    try:
        await ModelRouter(settings, local, cloud, record_metrics=False).explain(
            ResearchRequest(ticker="DEMO", provider="cloud", privacy="local_only"), "system", "private", "safe")
    except ValueError:
        blocked = local.calls == cloud.calls == 0
    outcomes.append({"id":"reject_explicit_cloud_local_only", "expected_provider":"rejected",
                     "observed_provider":"rejected" if blocked else "not_rejected", "cloud_calls":cloud.calls, "passed":blocked})
    passed = sum(case["passed"] for case in outcomes)
    return {"suite":"simulated_provider_reliability", "passed":passed,"total":len(outcomes),
            "results":outcomes,
            "scope":"In-process fake provider outages and privacy guards. NOT live Groq/Ollama latency, availability, cost or production resiliency."}
