"""Thin HTTP routes; research logic belongs in services, never here."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query

from .dependencies import get_settings, require_api_key
from ..core.config import Settings
from ..core.models import ResearchRequest, ResearchResponse
from ..data.sec import SECError
from ..services.research import run_research
from ..storage.history import add_history, list_history

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/health")
async def health(settings: Settings = Depends(get_settings)):
    return {"status": "ok", "version": "0.4.0", "sec_configured": settings.sec_ready,
            "ollama_enabled": settings.ollama_enabled, "groq_configured": bool(settings.groq_api_key),
            "auth_enabled": bool(settings.app_api_key), "auth_required": settings.require_auth}


@router.get("/api/demo", response_model=ResearchResponse)
async def demo(settings: Settings = Depends(get_settings)):
    """Synthetic company preview; deliberately requires no keys or external services."""
    return await run_research(ResearchRequest(ticker="DEMO", provider="none"), settings)


@router.post("/api/research", response_model=ResearchResponse, dependencies=[Depends(require_api_key)])
async def research(request: ResearchRequest, settings: Settings = Depends(get_settings)):
    if request.privacy == "local_only" and request.provider == "cloud":
        raise HTTPException(status_code=400, detail="Cloud provider conflicts with local-only privacy.")
    try:
        result = await run_research(request, settings)
    except SECError as exc:
        raise HTTPException(status_code=503 if "Cannot retrieve" in str(exc) or "limited" in str(exc) else 422, detail=str(exc)) from exc
    try:
        add_history(settings.history_db_path, result.ticker, result.data_kind, result.llm.provider)
    except OSError:
        logger.warning("Could not write local research history", exc_info=False)
    return result


@router.get("/api/history", dependencies=[Depends(require_api_key)])
async def history(limit: int = Query(default=10, ge=1, le=100), settings: Settings = Depends(get_settings)):
    return {"items": list_history(settings.history_db_path, limit)}
