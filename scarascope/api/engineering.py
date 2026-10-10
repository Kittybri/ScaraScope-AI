"""Read-only Engineering Lab API. Run benchmark on demand, no secrets/network calls."""
from fastapi import APIRouter, Depends, HTTPException
from .dependencies import require_api_key
from ..evaluation.runner import run_all, recent_reports
from ..evaluation.heldout.evaluator import compare_retrievers
from ..ai.retrieval.semantic import LocalSentenceEncoder
from ..core.config import Settings
from .dependencies import get_settings
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


@router.get("/retrieval-comparison")
async def retrieval_comparison(include_semantic: bool = False, settings: Settings = Depends(get_settings)):
    """Run offline ranking; only opt-in preinstalled local embeddings when selected."""
    if not include_semantic:
        return compare_retrievers(split="heldout")
    if not settings.embedding_model_path:
        raise HTTPException(status_code=400, detail="Configure SCARASCOPE_EMBEDDING_MODEL_PATH to compare semantic retrieval.")
    try:
        encoder = LocalSentenceEncoder(settings.embedding_model_path)
        return compare_retrievers(split="heldout", encoder=encoder)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
