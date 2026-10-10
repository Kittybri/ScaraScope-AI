"""Transparent, bounded research plan. The model never executes arbitrary tools."""
from typing import Literal
from pydantic import BaseModel, Field

class ResearchTask(BaseModel):
    tool: Literal["sec_financials", "financial_ratios", "sec_filing_sections", "evidence_review", "report_draft"]
    purpose: str

class ResearchPlan(BaseModel):
    objective: str = Field(max_length=700)
    tasks: list[ResearchTask] = Field(max_length=6)
    limit: int = 6


def plan_research(question: str, include_filing_text: bool = True) -> ResearchPlan:
    tasks = [ResearchTask(tool="sec_financials",purpose="Retrieve annual US-GAAP company financial facts"),
             ResearchTask(tool="financial_ratios",purpose="Calculate ratios deterministically")]
    if include_filing_text:
        tasks.append(ResearchTask(tool="sec_filing_sections",purpose="Retrieve relevant 10-K management/risk sections"))
    tasks += [ResearchTask(tool="evidence_review",purpose="Validate arithmetic and evidence provenance"),
              ResearchTask(tool="report_draft",purpose="Compose evidence-limited research report")]
    return ResearchPlan(objective=question, tasks=tasks)
