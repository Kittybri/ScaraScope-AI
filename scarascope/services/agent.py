"""Bounded financial research orchestration with explicit tool traces and warnings.

No code execution by LLM, no stock recommendations, no unbounded agent loops.
"""
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field
from ..ai.agents.planner import ResearchPlan, plan_research
from ..ai.agents.verification import VerificationResult, verify_financials, verify_excerpts
from ..core.config import Settings
from ..core.models import ResearchRequest, ResearchResponse
from ..data.sec import SECClient
from ..data.sec.filings import FilingClient, FilingResearch
from .research import run_research

class AgentStep(BaseModel):
    tool: str
    status: Literal["completed", "unavailable", "failed"]
    detail: str

class AgentReport(BaseModel):
    generated_at: datetime
    plan: ResearchPlan
    research: ResearchResponse
    filing: FilingResearch
    verification: VerificationResult
    steps: list[AgentStep] = Field(default_factory=list)
    executive_summary: str
    limitations: list[str] = Field(default_factory=list)

async def research_company(request: ResearchRequest, settings: Settings,
                           sec_client: SECClient | None = None,
                           filing_client: FilingClient | None = None,
                           router=None, include_filing_text: bool = True) -> AgentReport:
    plan = plan_research(request.question, include_filing_text and request.ticker != "DEMO")
    steps: list[AgentStep] = []
    result = await run_research(request, settings, sec_client=sec_client, router=router)
    steps.extend([AgentStep(tool="sec_financials",status="completed",detail=f"Loaded {len(result.financials)} annual periods ({result.data_kind})."),
                  AgentStep(tool="financial_ratios",status="completed",detail="Ratios computed in Python without LLM arithmetic.")])
    filing = FilingResearch(cik=result.cik or "", warnings=[])
    if include_filing_text and result.cik and result.data_kind == "sec_live":
        try:
            filing = await (filing_client or FilingClient(settings.sec_user_agent)).research(result.cik, request.question)
        except Exception:
            # A failure in optional narrative retrieval should not discard verified financial facts.
            filing = FilingResearch(cik=result.cik, warnings=["Filing narrative retrieval failed. No narrative evidence is available."])
        steps.append(AgentStep(tool="sec_filing_sections",status="completed" if filing.evidence else "unavailable",
                               detail=f"Retrieved {len(filing.evidence)} text excerpts from a recent 10-K; see section locators."))
    numeric = verify_financials(result.financials, synthetic=result.data_kind=="synthetic_demo")
    quotes = verify_excerpts(filing.sections, filing.evidence)
    issues = [*numeric.issues, *quotes.issues]
    verified = VerificationResult(passed=not issues, checks=numeric.checks+quotes.checks, issues=issues)
    steps.append(AgentStep(tool="evidence_review",status="completed" if verified.passed else "failed",
                           detail=f"Checked {verified.checks} arithmetic/source assertions; {len(issues)} issue(s)."))
    summary = result.summary
    if filing.evidence:
        summary += f" Retrieved {len(filing.evidence)} 10-K passages for independent review. These are evidence excerpts, not independently verified narrative conclusions."
    steps.append(AgentStep(tool="report_draft",status="completed",detail="Prepared research summary with caveats and source records."))
    limitations = [*result.warnings,*filing.warnings,*verified.limitations]
    if not filing.evidence:
        limitations.append("No retrieved narrative passages: do not infer management or filing risk statements from ratios alone.")
    return AgentReport(generated_at=datetime.now(timezone.utc),plan=plan,research=result,
                       filing=filing,verification=verified,steps=steps,executive_summary=summary,
                       limitations=limitations)
