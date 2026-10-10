"""FastAPI entry point. API documentation is available at /docs."""
from pathlib import Path
import logging
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .history import add_history, list_history
from .models import ResearchRequest, ResearchResponse
from .sec import SECError
from .service import run_research

logger = logging.getLogger(__name__)
app = FastAPI(title="ScaraScope AI", version="0.1.0", description="Source-grounded financial research and hybrid LLM provider routing")
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def get_settings() -> Settings:
    return Settings()


def require_api_key(x_api_key: str | None = Header(default=None), settings: Settings = Depends(get_settings)) -> None:
    if settings.app_api_key and not secrets.compare_digest(x_api_key or "", settings.app_api_key):
        raise HTTPException(status_code=401, detail="Missing or invalid API key.")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health(settings: Settings = Depends(get_settings)):
    return {"status": "ok", "version": "0.1.0", "sec_configured": settings.sec_ready,
            "ollama_enabled": settings.ollama_enabled, "groq_configured": bool(settings.groq_api_key),
            "auth_enabled": bool(settings.app_api_key)}


@app.get("/api/demo", response_model=ResearchResponse)
async def demo(settings: Settings = Depends(get_settings)):
    """Synthetic company preview; deliberately requires no keys or external services."""
    return await run_research(ResearchRequest(ticker="DEMO", provider="none"), settings)


@app.post("/api/research", response_model=ResearchResponse, dependencies=[Depends(require_api_key)])
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


@app.get("/api/history", dependencies=[Depends(require_api_key)])
async def history(limit: int = Query(default=10, ge=1, le=100), settings: Settings = Depends(get_settings)):
    return {"items": list_history(settings.history_db_path, limit)}
