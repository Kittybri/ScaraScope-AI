"""Explicit, on-demand SEC filing change checks; never claim background alerts."""
from datetime import date
from pydantic import BaseModel, Field
import httpx
from ..core.config import Settings
from ..data.sec.client import SECClient, SECError
from ..data.sec.constants import SEC_TICKERS_URL
from ..data.sec.filings import SUBMISSIONS_URL
from ..storage.watchlist import get_watches, update_accession

class FilingChange(BaseModel):
    ticker: str
    accession: str | None = None
    form: str | None = None
    filed: str | None = None
    is_new_since_previous_check: bool = False
    status: str

class WatchScan(BaseModel):
    items: list[FilingChange] = Field(default_factory=list)
    caveat: str = "On-demand check only. First check establishes a baseline; subsequent checks identify a changed latest accession. No scheduled polling or alerts."

class SECMonitor:
    def __init__(self, settings: Settings):
        self.settings=settings

    async def latest(self, ticker: str) -> tuple[str,str,str]:
        if not self.settings.sec_ready:
            raise SECError("SEC_USER_AGENT is required for live watchlist checks.")
        sec=SECClient(self.settings.sec_user_agent)
        async with httpx.AsyncClient(timeout=18,follow_redirects=False,headers={"User-Agent":self.settings.sec_user_agent}) as client:
            directory=await sec._get_json(client,SEC_TICKERS_URL)
            match=next((record for record in directory.values() if isinstance(record,dict) and record.get("ticker","").upper()==ticker),None)
            if not match:raise SECError(f"Ticker {ticker} not found in SEC directory.")
            recent=(await sec._get_json(client,SUBMISSIONS_URL.format(cik=int(match["cik_str"]))))["filings"]["recent"]
            for index,form in enumerate(recent["form"]):
                if form in {"10-K","10-Q","8-K"}:
                    return str(recent["accessionNumber"][index]),form,str(recent["filingDate"][index])
        raise SECError(f"No tracked filings found for {ticker}.")

async def scan_watches(settings: Settings, monitor: SECMonitor | None = None) -> WatchScan:
    probe=monitor or SECMonitor(settings)
    items=[]
    # Bounded on-demand scans; protects SEC access and demo infrastructure.
    for watch in get_watches(settings.history_db_path)[:10]:
        ticker=watch["ticker"]
        try:
            accession,form,filed=await probe.latest(ticker)
            changed=update_accession(settings.history_db_path,ticker,accession)
            items.append(FilingChange(ticker=ticker,accession=accession,form=form,filed=filed,
                                      is_new_since_previous_check=changed,
                                      status="changed" if changed else "baseline or unchanged"))
        except SECError as exc:
            items.append(FilingChange(ticker=ticker,status=f"unavailable: {exc}"))
    return WatchScan(items=items)
