"""ASGI application composition. No financial or inference code lives here."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .routes import router

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
app = FastAPI(title="ScaraScope AI", version="0.1.0", description="Source-grounded financial research and hybrid LLM provider routing")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(router)


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIR / "index.html")
