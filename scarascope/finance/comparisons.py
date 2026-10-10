"""Pure, deterministic cross-company comparisons, with explicit missing values."""
from pydantic import BaseModel, Field
from ..core.models import AnnualFinancials, FactSource

class ComparisonMetric(BaseModel):
    label: str
    left_value: float | None
    right_value: float | None
    difference: float | None
    unit: str

class CompanySnapshot(BaseModel):
    ticker: str
    company: str
    period_end: str
    fiscal_year: int
    sources: list[FactSource] = Field(default_factory=list)

class ComparisonResult(BaseModel):
    left: CompanySnapshot
    right: CompanySnapshot
    metrics: list[ComparisonMetric]
    caveats: list[str]

_METRICS = (
    ("Revenue", "revenue", "USD"),
    ("Operating income", "operating_income", "USD"),
    ("Net income", "net_income", "USD"),
    ("Revenue growth", "revenue_growth_pct", "percent"),
    ("Operating margin", "operating_margin_pct", "percent"),
    ("Net margin", "net_margin_pct", "percent"),
    ("Total assets", "assets", "USD"),
    ("Total liabilities", "liabilities", "USD"),
)

def compare(left_ticker: str, left_company: str, left: list[AnnualFinancials],
            right_ticker: str, right_company: str, right: list[AnnualFinancials]) -> ComparisonResult:
    if not left or not right:
        raise ValueError("Both companies need at least one annual period.")
    l, r = left[0], right[0]
    differences = []
    for name, field, unit in _METRICS:
        a, b = getattr(l, field), getattr(r, field)
        differences.append(ComparisonMetric(label=name, left_value=a, right_value=b,
                                            difference=round(a - b, 2) if a is not None and b is not None else None,
                                            unit=unit))
    caveats = ["Comparisons are arithmetic differences, not judgments or recommendations.",
               "Accounting policies, segment definitions, and fiscal periods may differ."]
    if l.period_end != r.period_end:
        caveats.append("Fiscal year-end dates are different; figures are not for identical periods.")
    return ComparisonResult(
        left=CompanySnapshot(ticker=left_ticker, company=left_company, fiscal_year=l.fiscal_year,
                             period_end=l.period_end.isoformat(), sources=l.sources),
        right=CompanySnapshot(ticker=right_ticker, company=right_company, fiscal_year=r.fiscal_year,
                              period_end=r.period_end.isoformat(), sources=r.sources),
        metrics=differences, caveats=caveats,
    )
