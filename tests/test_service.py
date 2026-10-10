"""Test orchestration without calling SEC, Groq, Ollama, or Discord."""
from datetime import date
import pytest

from scarascope.core.config import Settings
from scarascope.core.models import AnnualFinancials, FactSource, LLMResult, ResearchRequest
from scarascope.services.research import run_research


class StubSEC:
    def __init__(self):
        self.calls = []

    async def get_company(self, ticker: str, years: int):
        self.calls.append((ticker, years))
        return (
            "Example Inc.", "0000000123", [
                AnnualFinancials(
                    fiscal_year=2025,
                    period_end=date(2025, 12, 31),
                    revenue=200,
                    operating_income=40,
                    net_income=20,
                    sources=[FactSource(
                        metric="revenue", form="10-K", accession="0001-25-000001",
                        filed="2026-02-01", period_end=date(2025, 12, 31),
                        source_url="https://www.sec.gov/Archives/edgar/data/123/1/index.html",
                    )],
                ),
                AnnualFinancials(
                    fiscal_year=2024, period_end=date(2024, 12, 31), revenue=100,
                ),
            ], "https://data.sec.gov/example",
        )


class StubRouter:
    def __init__(self):
        self.calls = []

    async def explain(self, request, system, prompt, fallback_text):
        self.calls.append((request, system, prompt, fallback_text))
        return LLMResult(provider="deterministic", model="none", text=fallback_text)


@pytest.mark.asyncio
async def test_headless_research_uses_injected_sources_and_financial_math():
    sec, router = StubSEC(), StubRouter()
    request = ResearchRequest(ticker="TEST", years=2, question="Summarize revenue")
    result = await run_research(request, Settings(), sec_client=sec, router=router)

    assert sec.calls == [("TEST", 2)]
    assert result.company == "Example Inc."
    assert result.data_kind == "sec_live"
    assert result.financials[0].revenue_growth_pct == 100.0
    assert result.financials[0].operating_margin_pct == 20.0
    assert result.financials[0].net_margin_pct == 10.0
    assert "SEC filing-derived" in result.summary
    assert "SEC source: revenue" in router.calls[0][2]
    assert "Do not claim to have reviewed narrative risk factors" in router.calls[0][2]
    assert result.financials[0].sources[0].accession == "0001-25-000001"


@pytest.mark.asyncio
async def test_demo_never_fetches_sec_and_forces_non_llm_explanation():
    sec, router = StubSEC(), StubRouter()
    result = await run_research(ResearchRequest(ticker="DEMO", provider="auto"), Settings(), sec_client=sec, router=router)
    assert sec.calls == []
    assert router.calls[0][0].provider == "none"
    assert result.data_kind == "synthetic_demo"
    assert "fictional" in result.summary.lower()
    assert result.financials[0].sources == []
