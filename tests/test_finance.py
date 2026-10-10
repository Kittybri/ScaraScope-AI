from datetime import date
from scarascope.finance.demo import demo_financials
from scarascope.finance.calculations import deterministic_summary, enrich_financials, ratio_pct
from scarascope.core.models import AnnualFinancials, ResearchRequest


def test_demo_is_fictional_and_calculations_are_correct():
    rows = enrich_financials(demo_financials(3))
    assert [r.fiscal_year for r in rows] == [2025, 2024, 2023]
    assert rows[0].revenue == 128_000_000
    assert rows[0].revenue_growth_pct == 10.34
    assert rows[0].operating_margin_pct == 17.0
    assert rows[-1].revenue_growth_pct is None
    assert "FICTIONAL DEMO" in deterministic_summary("fictional", rows, True)


def test_no_math_when_denominator_is_zero_or_metric_missing():
    assert ratio_pct(12, 0) is None
    assert ratio_pct(None, 3) is None
    row = AnnualFinancials(fiscal_year=2024, period_end=date(2024, 12, 31), revenue=0, operating_income=5)
    assert enrich_financials([row])[0].operating_margin_pct is None


def test_ticker_validation():
    assert ResearchRequest(ticker=" msft ").ticker == "MSFT"
    try:
        ResearchRequest(ticker="../danger")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid ticker accepted")
