"""ASGI application composition. No financial or inference code lives here."""
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from ..core.config import Settings
from ..security.rate_limits import limiter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .routes import router
from .advanced import router as advanced_router
from .exports import router as export_router
from .watchlist import router as watchlist_router

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
app = FastAPI(title="ScaraScope AI", version="0.2.0", description="Source-grounded financial research and hybrid LLM provider routing")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(router)
app.include_router(advanced_router)
app.include_router(export_router)
app.include_router(watchlist_router)


@app.middleware("http")
async def demo_rate_limit(request: Request, call_next):
    """Protect API endpoints from accidental high-rate use on a single worker."""
    if request.url.path.startswith("/api/") and request.url.path not in {"/api/health"}:
        settings=Settings()
        address=request.client.host if request.client else "unknown"
        if not limiter.allow(address,settings.request_limit_per_minute):
            return JSONResponse({"detail":"Too many API requests; retry in a minute."},status_code=429,
                                headers={"Retry-After":"60"})
    return await call_next(request)


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIR / "index.html")
