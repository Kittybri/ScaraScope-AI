"""Headless research use case shared by HTTP and optional clients."""
from datetime import datetime, timezone

from ..core.config import Settings
from ..core.models import ResearchRequest, ResearchResponse
from ..finance.demo import demo_financials
from ..finance.calculations import deterministic_summary, enrich_financials
from ..ai.router import ModelRouter
from ..ai.prompts import SYSTEM_PROMPT, build_financial_prompt
from ..data.sec import SECClient


async def run_research(request: ResearchRequest, settings: Settings, sec_client: SECClient | None = None, router: ModelRouter | None = None) -> ResearchResponse:
    demo = request.ticker == "DEMO"
    if demo:
        company, cik, rows, data_source = "ScaraScope Example Corporation (fictional)", None, demo_financials(request.years), "Synthetic sample data: no SEC filing or real company"
    else:
        company, cik, rows, data_source = await (sec_client or SECClient(settings.sec_user_agent)).get_company(request.ticker, request.years)
    rows = enrich_financials(rows)
    base_text = deterministic_summary(company, rows, demo)
    if demo:
        # Never represent a fabricated example as actual AI/SEC research.
        llm_result = await (router or ModelRouter(settings)).explain(
            ResearchRequest(ticker=request.ticker, years=request.years, question=request.question, provider="none", privacy=request.privacy),
            SYSTEM_PROMPT, "", base_text,
        )
        warnings = ["All DEMO figures and the company are fictional. They are not SEC data."]
    else:
        llm_result = await (router or ModelRouter(settings)).explain(request, SYSTEM_PROMPT, build_financial_prompt(company, request.ticker, request.question, rows), base_text)
        warnings = ["US-GAAP tags and period matching may vary by filer. Always inspect source filings before relying on figures.", "Risk factors and market prices are not retrieved in this MVP."]
    if llm_result.provider == "deterministic" and not demo:
        warnings.append("Generated a rule-based summary; LLM was not used. See routing note.")
    return ResearchResponse(
        ticker=request.ticker, company=company, cik=cik,
        data_kind="synthetic_demo" if demo else "sec_live",
        generated_at=datetime.now(timezone.utc), financials=rows,
        summary=llm_result.text, llm=llm_result, data_source=data_source,
        warnings=warnings,
    )
