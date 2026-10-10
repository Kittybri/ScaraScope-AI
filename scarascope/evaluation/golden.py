"""Small deterministic golden cases; not a claim to external FinanceBench performance."""
from dataclasses import dataclass
from ..finance.calculations import ratio_pct
from ..finance.valuation import DCFInput,calculate_dcf

@dataclass(frozen=True)
class EvaluationCase:
    id: str
    label: str
    expected: float | None
    observed: float | None


def built_in_cases() -> list[EvaluationCase]:
    input_dcf=DCFInput(starting_unlevered_fcf=100,fcf_growth_pct=0,discount_rate_pct=10,terminal_growth_pct=0,forecast_years=1)
    return [
        EvaluationCase("growth","Revenue growth from 100 to 120",20.0,ratio_pct(20,100)),
        EvaluationCase("op_margin","Operating margin 30 / 150",20.0,ratio_pct(30,150)),
        EvaluationCase("loss_margin","Negative earnings  -20 / 200",-10.0,ratio_pct(-20,200)),
        EvaluationCase("missing","Missing denominator should stay missing",None,ratio_pct(10,None)),
        EvaluationCase("zero","Zero denominator should stay missing",None,ratio_pct(10,0)),
        EvaluationCase("dcf","Constant 100 cash flow, 10pct rate, terminal at end of Y1",1000.0,calculate_dcf(input_dcf).implied_enterprise_value),
    ]
