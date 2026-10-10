"""Exact financial calculations and safeguards, no external services."""
from datetime import date
import pytest
from pydantic import ValidationError
from scarascope.finance.valuation import DCFInput,calculate_dcf,dcf_sensitivity
from scarascope.finance.comparisons import compare
from scarascope.core.models import AnnualFinancials
from scarascope.evaluation.benchmark import run_benchmark

def test_constant_cash_flow_dcf_matches_perpetuity():
    spec=DCFInput(starting_unlevered_fcf=100,fcf_growth_pct=0,discount_rate_pct=10,terminal_growth_pct=0,forecast_years=5)
    result=calculate_dcf(spec)
    assert result.implied_enterprise_value==1000.0
    assert result.terminal_share_pct>50
    assert len(result.forecast)==5

def test_discount_rate_must_exceed_terminal_growth():
    with pytest.raises(ValidationError):
        DCFInput(starting_unlevered_fcf=100,fcf_growth_pct=0,discount_rate_pct=3,terminal_growth_pct=4)

def test_dcf_sensitivity_has_five_by_five_values():
    spec=DCFInput(starting_unlevered_fcf=100,fcf_growth_pct=1,discount_rate_pct=10,terminal_growth_pct=2)
    result=dcf_sensitivity(spec)
    assert len(result.enterprise_values)==5
    assert all(len(row)==5 for row in result.enterprise_values)
    assert result.enterprise_values[2][2]==calculate_dcf(spec).implied_enterprise_value

def test_company_compare_different_period_warning_and_missing_values():
    left=[AnnualFinancials(fiscal_year=2025,period_end=date(2025,6,30),revenue=200,operating_margin_pct=20)]
    right=[AnnualFinancials(fiscal_year=2025,period_end=date(2025,12,31),revenue=150)]
    result=compare("AAA","A Inc",left,"BBB","B Inc",right)
    assert result.metrics[0].difference==50
    assert next(x for x in result.metrics if x.label=="Operating margin").difference is None
    assert any("year-end" in x for x in result.caveats)

def test_benchmark_is_labeled_and_reproducible():
    report=run_benchmark()
    assert report.passed==report.total
    assert report.total>=6
    assert report.accuracy_pct==100.0
    assert "not an LLM" in report.limitation
