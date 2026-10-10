"""Typed API and provider contracts."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ResearchRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=12, examples=["MSFT", "DEMO"])
    question: str = Field(default="Summarize this company's financial performance and risks.", max_length=700)
    years: int = Field(default=3, ge=1, le=5)
    provider: Literal["auto", "local", "cloud", "none"] = "auto"
    privacy: Literal["cloud_ok", "local_only"] = "cloud_ok"

    @field_validator("ticker")
    @classmethod
    def valid_ticker(cls, value: str) -> str:
        import re
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,11}", value):
            raise ValueError("Use a valid ticker symbol (letters, numbers, dot or hyphen).")
        return value


class FactSource(BaseModel):
    metric: str
    form: str
    accession: str
    filed: str
    period_end: date
    source_url: str


class AnnualFinancials(BaseModel):
    fiscal_year: int
    period_end: date
    revenue: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    assets: float | None = None
    liabilities: float | None = None
    equity: float | None = None
    revenue_growth_pct: float | None = None
    operating_margin_pct: float | None = None
    net_margin_pct: float | None = None
    sources: list[FactSource] = Field(default_factory=list)


class LLMResult(BaseModel):
    provider: Literal["ollama", "groq", "deterministic"]
    model: str
    text: str
    fallback_used: bool = False
    note: str | None = None


class ResearchResponse(BaseModel):
    ticker: str
    company: str
    cik: str | None
    data_kind: Literal["synthetic_demo", "sec_live"]
    generated_at: datetime
    financials: list[AnnualFinancials]
    summary: str
    llm: LLMResult
    data_source: str
    warnings: list[str] = Field(default_factory=list)
