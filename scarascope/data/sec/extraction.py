"""Pure SEC XBRL annual financial extraction with source provenance."""
from datetime import date
from typing import Any
from ...core.models import AnnualFinancials, FactSource
from .constants import SEC_FACTS_URL

# Common US GAAP concepts. These are not universal filing definitions.
CONCEPTS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss"],
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
}
FLOW_METRICS = {"revenue", "operating_income", "net_income"}


def _annual_facts(units: list[dict[str, Any]], flow: bool) -> list[dict[str, Any]]:
    matched = []
    for item in units:
        if item.get("form") != "10-K" or "end" not in item or not isinstance(item.get("val"), (int, float)):
            continue
        try:
            end = date.fromisoformat(item["end"])
            if flow:
                start = date.fromisoformat(item["start"])
                duration = (end - start).days
                if duration < 300 or duration > 380:
                    continue
            else:
                if item.get("start"):
                    continue
        except (ValueError, TypeError, KeyError):
            continue
        matched.append(item)
    return matched


def _metric_values(facts: dict[str, Any], names: list[str], flow: bool) -> dict[str, dict[str, Any]]:
    """Take last-filed valid annual fact for each period, preferring listed concepts."""
    result: dict[str, dict[str, Any]] = {}
    for concept in names:
        obj = facts.get(concept, {})
        units = obj.get("units", {}).get("USD", [])
        for item in _annual_facts(units, flow):
            end = item["end"]
            if end not in result or item.get("filed", "") > result[end].get("filed", ""):
                result[end] = {**item, "_concept": concept}
        # Prevent a lower-priority concept overriding available periods, but allow gap filling.
        if result:
            break
    # Different revenue tagging across years can leave holes; fill from alternative tags.
    for concept in names[1:]:
        for item in _annual_facts(facts.get(concept, {}).get("units", {}).get("USD", []), flow):
            result.setdefault(item["end"], {**item, "_concept": concept})
    return result


def extract_annual_financials(companyfacts: dict[str, Any], years: int = 3) -> list[AnnualFinancials]:
    gaap = companyfacts.get("facts", {}).get("us-gaap", {})
    values = {key: _metric_values(gaap, concepts, key in FLOW_METRICS) for key, concepts in CONCEPTS.items()}
    # Anchor all row periods to annual revenue facts; don't mix unmatched dates.
    periods = sorted(values["revenue"], reverse=True)[:years]
    cik = int(companyfacts.get("cik", 0))
    out: list[AnnualFinancials] = []
    for period in periods:
        period_end = date.fromisoformat(period)
        data: dict[str, Any] = {"fiscal_year": period_end.year, "period_end": period_end}
        sources: list[FactSource] = []
        for metric in CONCEPTS:
            item = values[metric].get(period)
            if item is None:
                continue
            # Revenue/income should align on both start and end dates.
            if metric in FLOW_METRICS and item.get("start") != values["revenue"][period].get("start"):
                continue
            data[metric] = float(item["val"])
            accession = item.get("accn", "")
            if accession and cik:
                filing_link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{accession}-index.html"
            else:
                filing_link = SEC_FACTS_URL.format(cik=cik)
            sources.append(FactSource(metric=metric, form="10-K", accession=accession, filed=item.get("filed", ""), period_end=period_end, source_url=filing_link))
        data["sources"] = sources
        out.append(AnnualFinancials(**data))
    return out


