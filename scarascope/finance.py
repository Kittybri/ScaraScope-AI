"""Financial calculations are deterministic, not delegated to an LLM."""
from .models import AnnualFinancials


def ratio_pct(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return round((numerator / denominator) * 100.0, 2)


def enrich_financials(rows: list[AnnualFinancials]) -> list[AnnualFinancials]:
    """Newest first. Growth compares adjacent complete annual revenue periods."""
    for index, row in enumerate(rows):
        row.operating_margin_pct = ratio_pct(row.operating_income, row.revenue)
        row.net_margin_pct = ratio_pct(row.net_income, row.revenue)
        if index + 1 < len(rows):
            prev = rows[index + 1]
            if prev.revenue is not None and prev.revenue > 0 and row.revenue is not None:
                row.revenue_growth_pct = ratio_pct(row.revenue - prev.revenue, prev.revenue)
    return rows


def format_usd(amount: float | None) -> str:
    if amount is None:
        return "not available"
    if abs(amount) >= 1e9:
        return f"${amount / 1e9:,.2f}B"
    if abs(amount) >= 1e6:
        return f"${amount / 1e6:,.2f}M"
    return f"${amount:,.0f}"


def deterministic_summary(company: str, rows: list[AnnualFinancials], demo: bool) -> str:
    prefix = "FICTIONAL DEMO DATA. " if demo else "SEC filing-derived figures. "
    if not rows:
        return prefix + "No comparable annual financial data were found."
    latest = rows[0]
    pieces = [f"{prefix}{company} reported revenue of {format_usd(latest.revenue)} for the period ended {latest.period_end.isoformat()}."]
    if latest.revenue_growth_pct is not None:
        pieces.append(f"Revenue changed {latest.revenue_growth_pct:+.2f}% against the preceding available annual period.")
    if latest.operating_margin_pct is not None:
        pieces.append(f"Operating margin was {latest.operating_margin_pct:.2f}% (operating income divided by revenue).")
    if latest.net_margin_pct is not None:
        pieces.append(f"Net margin was {latest.net_margin_pct:.2f}% (net income divided by revenue).")
    pieces.append("Check the underlying annual filings, reporting periods, and accounting definitions before making decisions. This is research, not investment advice.")
    return " ".join(pieces)
