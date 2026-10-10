"""Orchestrate independent company lookups and deterministic comparison."""
from ..core.config import Settings
from ..core.models import ResearchRequest
from ..data.sec.client import SECClient
from ..finance.comparisons import ComparisonResult, compare
from .research import run_research

async def compare_companies(left: str, right: str, settings: Settings, client: SECClient | None = None, years: int = 3) -> ComparisonResult:
    if left.upper() == right.upper():
        raise ValueError("Select two different tickers.")
    sec = client or SECClient(settings.sec_user_agent)
    l = await run_research(ResearchRequest(ticker=left, years=years, provider="none"), settings, sec_client=sec)
    r = await run_research(ResearchRequest(ticker=right, years=years, provider="none"), settings, sec_client=sec)
    return compare(l.ticker, l.company, l.financials, r.ticker, r.company, r.financials)
