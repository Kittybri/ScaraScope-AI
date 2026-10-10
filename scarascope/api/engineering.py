"""Read-only Engineering Lab API. Run benchmark on demand, no secrets/network calls."""
from fastapi import APIRouter, Depends
from .dependencies import require_api_key
from ..evaluation.runner import run_all, recent_reports
from ..observability.metrics import snapshot

router = APIRouter(prefix="/api/engineering", tags=["Engineering Lab"], dependencies=[Depends(require_api_key)])


@router.get("/benchmark")
async def benchmark():
    return await run_all()


@router.get("/history")
async def history():
    return {"items":recent_reports(), "note":"Local CLI-generated JSON reports, not live monitoring."}


@router.get("/runtime")
async def runtime():
    return snapshot()
