"""Transparent illustrative enterprise DCF; never invent starting cash flow."""
from math import isfinite
from pydantic import BaseModel, Field, model_validator

class DCFInput(BaseModel):
    starting_unlevered_fcf: float = Field(gt=0, description="Explicit annual unlevered free cash flow (USD), supplied by user")
    fcf_growth_pct: float = Field(ge=-80, le=100, description="Annual cash flow growth assumption, not a prediction")
    discount_rate_pct: float = Field(gt=0, le=60)
    terminal_growth_pct: float = Field(ge=-20, le=20)
    forecast_years: int = Field(default=5, ge=1, le=10)

    @model_validator(mode="after")
    def check_terminal(self):
        if self.discount_rate_pct <= self.terminal_growth_pct:
            raise ValueError("Discount rate must exceed terminal growth rate.")
        return self

class ForecastRow(BaseModel):
    year: int
    projected_fcf: float
    present_value: float

class DCFResult(BaseModel):
    assumptions: DCFInput
    forecast: list[ForecastRow]
    discounted_cash_flows: float
    terminal_value: float
    discounted_terminal_value: float
    implied_enterprise_value: float
    terminal_share_pct: float
    disclaimer: str = "Illustrative enterprise DCF using user-supplied assumptions, not a price target or investment recommendation. No net-debt bridge or share count included."

def calculate_dcf(spec: DCFInput) -> DCFResult:
    growth = spec.fcf_growth_pct / 100
    discount = spec.discount_rate_pct / 100
    terminal_growth = spec.terminal_growth_pct / 100
    future = []
    undiscounted_pvs = []
    fcf = spec.starting_unlevered_fcf
    for year in range(1, spec.forecast_years + 1):
        fcf *= (1 + growth)
        pv = fcf / (1 + discount) ** year
        undiscounted_pvs.append(pv)
        future.append(ForecastRow(year=year, projected_fcf=round(fcf, 2),
                                  present_value=round(pv, 2)))
    terminal = fcf * (1 + terminal_growth) / (discount - terminal_growth)
    terminal_pv = terminal / (1 + discount) ** spec.forecast_years
    operating_pv = sum(undiscounted_pvs)
    enterprise = operating_pv + terminal_pv
    if not all(isfinite(v) for v in (terminal, terminal_pv, enterprise)):
        raise ValueError("The assumptions produced non-finite values.")
    return DCFResult(assumptions=spec, forecast=future,
                     discounted_cash_flows=round(operating_pv, 2),
                     terminal_value=round(terminal, 2),
                     discounted_terminal_value=round(terminal_pv, 2),
                     implied_enterprise_value=round(enterprise, 2),
                     terminal_share_pct=round(100 * terminal_pv / enterprise, 2))

class SensitivityResult(BaseModel):
    discount_rates_pct: list[float]
    terminal_growth_rates_pct: list[float]
    enterprise_values: list[list[float | None]]

def dcf_sensitivity(spec: DCFInput, rate_step: float = 1.0, terminal_step: float = 0.5) -> SensitivityResult:
    rates = [round(spec.discount_rate_pct + delta * rate_step, 2) for delta in (-2,-1,0,1,2)]
    growths = [round(spec.terminal_growth_pct + delta * terminal_step, 2) for delta in (-2,-1,0,1,2)]
    values = []
    for discount in rates:
        row = []
        for growth in growths:
            if discount <= 0 or discount <= growth:
                row.append(None)
                continue
            variant = spec.model_copy(update={"discount_rate_pct":discount,"terminal_growth_pct":growth})
            row.append(calculate_dcf(variant).implied_enterprise_value)
        values.append(row)
    return SensitivityResult(discount_rates_pct=rates, terminal_growth_rates_pct=growths, enterprise_values=values)
