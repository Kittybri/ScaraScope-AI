"""Clearly labeled fictional finance data, usable with no credentials or internet."""
from datetime import date
from .models import AnnualFinancials


def demo_financials(years: int = 3) -> list[AnnualFinancials]:
    samples = [
        AnnualFinancials(fiscal_year=2023, period_end=date(2023, 12, 31), revenue=100_000_000, operating_income=12_000_000, net_income=9_000_000, assets=165_000_000, liabilities=84_000_000, equity=81_000_000),
        AnnualFinancials(fiscal_year=2024, period_end=date(2024, 12, 31), revenue=116_000_000, operating_income=17_400_000, net_income=13_000_000, assets=185_000_000, liabilities=90_000_000, equity=95_000_000),
        AnnualFinancials(fiscal_year=2025, period_end=date(2025, 12, 31), revenue=128_000_000, operating_income=21_760_000, net_income=16_000_000, assets=207_000_000, liabilities=96_000_000, equity=111_000_000),
    ]
    return samples[-years:][::-1]
