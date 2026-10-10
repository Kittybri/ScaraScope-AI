"""Network boundary for SEC ticker directory and Company Facts API."""
from typing import Any
import httpx

from ...core.models import AnnualFinancials
from .constants import SEC_FACTS_URL, SEC_TICKERS_URL
from .extraction import extract_annual_financials


class SECError(Exception):
    """Expected EDGAR lookup failure safe for user-facing error messages."""


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
