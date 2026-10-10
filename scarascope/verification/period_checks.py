"""Pure guards for inconsistent reporting dates and year-over-year comparisons."""
from ..core.models import AnnualFinancials


def check_periods(rows: list[AnnualFinancials]) -> list[str]:
    """Returns problems rather than inventing comparisons for incompatible periods."""
    problems = []
    seen = set()
    for index, row in enumerate(rows):
        if row.period_end in seen:
            problems.append(f"Duplicate period ending {row.period_end}.")
        seen.add(row.period_end)
        if row.period_end.year != row.fiscal_year:
            problems.append(f"Fiscal label {row.fiscal_year} disagrees with {row.period_end}.")
        if index:
            earlier = rows[index - 1]
            if row.period_end >= earlier.period_end:
                problems.append(f"Financial periods are not ordered newest-first: {earlier.period_end}, {row.period_end}.")
            days = (earlier.period_end - row.period_end).days
            if not 330 <= days <= 400:
                problems.append(f"Cannot assume consecutive annual periods: {earlier.period_end}, {row.period_end} ({days} days).")
    return problems
