"""Manual watchlist bookkeeping; not a background notification service."""
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel, Field, field_validator
from .dependencies import get_settings, require_api_key
from ..core.config import Settings
from ..storage.watchlist import add_watch,delete_watch,get_watches
from ..services.monitor import scan_watches

router=APIRouter(prefix="/api/watchlist",dependencies=[Depends(require_api_key)])
class WatchTicker(BaseModel):
    ticker: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9.-]{0,11}$")
    @field_validator("ticker")
    @classmethod
    def normalize(cls,value):return value.upper()

@router.get("")
async def list_watch(settings:Settings=Depends(get_settings)):
    return {"items":get_watches(settings.history_db_path),"note":"Manual watchlist. No scheduled SEC polling or alerts yet."}

@router.post("")
async def add(req:WatchTicker,settings:Settings=Depends(get_settings)):
    if len(get_watches(settings.history_db_path))>=50 and req.ticker not in {x["ticker"] for x in get_watches(settings.history_db_path)}:
        raise HTTPException(status_code=422,detail="Watchlist limited to 50 tickers.")
    add_watch(settings.history_db_path,req.ticker)
    return {"saved":req.ticker}

@router.delete("/{ticker}")
async def remove(ticker:str,settings:Settings=Depends(get_settings)):
    req=WatchTicker(ticker=ticker)
    delete_watch(settings.history_db_path,req.ticker)
    return {"removed":req.ticker}

@router.post("/check")
async def check(settings:Settings=Depends(get_settings)):
    return await scan_watches(settings)
