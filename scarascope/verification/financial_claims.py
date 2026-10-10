"""Structured financial claim checks; does not validate unrestricted LLM prose."""
from dataclasses import dataclass
from math import isclose, isfinite
from ..core.models import AnnualFinancials
from .period_checks import check_periods
from .source_validation import check_financial_sources

_ALLOWED = {"revenue", "operating_income", "net_income", "operating_margin_pct", "net_margin_pct", "revenue_growth_pct"}


@dataclass(frozen=True)
class FinancialClaim:
    fiscal_year: int
    metric: str
    value: float
    unit: str


def check_claim(claim: FinancialClaim, rows: list[AnnualFinancials], *, source_required: bool = True) -> list[str]:
    issues = check_periods(rows)
    if source_required:
        issues.extend(check_financial_sources(rows))
    if claim.metric not in _ALLOWED:
        return issues + ["Unsupported metric type."]
    expected_unit = "percent" if claim.metric.endswith("_pct") else "USD_millions"
    if claim.unit != expected_unit:
        issues.append(f"Unit mismatch: expected {expected_unit}.")
    row = next((r for r in rows if r.fiscal_year == claim.fiscal_year), None)
    if row is None:
        return issues + [f"Fiscal year {claim.fiscal_year} not in available evidence."]
    actual = getattr(row, claim.metric)
    if actual is None or not isfinite(claim.value) or not isfinite(actual):
        return issues + ["Claim has a missing or nonfinite financial value."]
    if not isclose(actual, claim.value, abs_tol=0.011 if expected_unit == "percent" else 0.0001, rel_tol=0):
        issues.append(f"Value mismatch for {claim.metric} in FY{claim.fiscal_year}.")
    return issues
