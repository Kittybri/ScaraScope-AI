"""SEC EDGAR companyfacts ingestion with filing provenance and period-aware extraction.

Public company facts: https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json
"""
from datetime import date
from typing import Any

import httpx

from .models import AnnualFinancials, FactSource

SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

# Choose among commonly used US GAAP concepts; these are NOT universal definitions.
CONCEPTS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss"],
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
}
FLOW_METRICS = {"revenue", "operating_income", "net_income"}


class SECError(Exception):
    """Expected EDGAR lookup failure, safe for user-facing error messages."""


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


class SECClient:
    def __init__(self, user_agent: str):
        self.user_agent = user_agent

    async def _get_json(self, client: httpx.AsyncClient, url: str) -> dict[str, Any]:
        try:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise SECError("Unexpected SEC response format.")
            return payload
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in (403, 429):
                raise SECError("SEC request was limited or denied. Try later and check SEC_USER_AGENT.") from exc
            raise SECError(f"SEC lookup returned HTTP {status}.") from exc
        except (httpx.RequestError, ValueError) as exc:
            raise SECError("Cannot retrieve SEC data right now. Check connectivity and retry.") from exc

    async def get_company(self, ticker: str, years: int) -> tuple[str, str, list[AnnualFinancials], str]:
        if not self.user_agent or "@" not in self.user_agent or "example.com" in self.user_agent.lower():
            raise SECError("Set SEC_USER_AGENT in .env with your actual name and contact email before live SEC requests.")
        async with httpx.AsyncClient(timeout=18, headers={"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate", "Accept": "application/json"}, follow_redirects=True) as client:
            companies = await self._get_json(client, SEC_TICKERS_URL)
            match = next((c for c in companies.values() if isinstance(c, dict) and str(c.get("ticker", "")).upper() == ticker), None)
            if not match:
                raise SECError(f"Ticker {ticker} was not found in the SEC company ticker directory.")
            cik = int(match["cik_str"])
            payload = await self._get_json(client, SEC_FACTS_URL.format(cik=cik))
            rows = extract_annual_financials(payload, years)
            if not rows:
                raise SECError(f"No comparable annual US-GAAP revenue facts were found for {ticker}.")
            return str(match["title"]), f"{cik:010d}", rows, SEC_FACTS_URL.format(cik=cik)
