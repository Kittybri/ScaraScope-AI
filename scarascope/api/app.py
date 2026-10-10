"""ASGI application composition. No financial or inference code lives here."""
from pathlib import Path
from time import perf_counter
from ..observability.tracing import create_request_id, begin_request, end_request, record_http
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
from .documents import router as document_router
from .engineering import router as engineering_router

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
app = FastAPI(title="ScaraScope AI", version="0.9.0", description="Source-grounded financial research and hybrid LLM provider routing")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(router)
app.include_router(advanced_router)
app.include_router(export_router)
app.include_router(watchlist_router)
app.include_router(document_router)
app.include_router(engineering_router)


@app.middleware("http")
async def demo_rate_limit(request: Request, call_next):
    """Protect API endpoints from accidental high-rate use on a single worker."""
    if not request.url.path.startswith("/api/"):
        return await call_next(request)
    started = perf_counter()
    run_id = create_request_id()
    token = begin_request(run_id)
    status_code = 500
    try:
        # Fail on oversized declared API bodies before routing. This bound is
        # not a substitute for reverse-proxy streaming/body size limits.
        declared = request.headers.get("content-length")
        if declared and (not declared.isdigit() or int(declared) > 65536):
            response = JSONResponse({"detail":"API request body exceeds 64 KiB."}, status_code=413)
        elif request.url.path not in {"/api/health"} and not limiter.allow(
                request.client.host if request.client else "unknown", Settings().request_limit_per_minute):
            response = JSONResponse({"detail":"Too many API requests; retry in a minute."},
                                    status_code=429, headers={"Retry-After":"60"})
        else:
            response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = run_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response
    finally:
        route = request.scope.get("route")
        template = getattr(route, "path", "unknown")
        record_http(run_id, template, request.method, status_code,
                    (perf_counter() - started) * 1000)
        end_request(token)


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/engineering", include_in_schema=False)
async def engineering_lab():
    return FileResponse(STATIC_DIR / "engineering" / "index.html")
