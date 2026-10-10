"""Read-only Engineering Lab API. Run benchmark on demand, no secrets/network calls."""
from fastapi import APIRouter, Depends, HTTPException
from .dependencies import require_api_key
from ..evaluation.runner import run_all, recent_reports
from ..evaluation.heldout.evaluator import compare_retrievers
from ..ai.retrieval.semantic import LocalSentenceEncoder
from ..core.config import Settings
from .dependencies import get_settings
from ..observability.metrics import snapshot
from ..evaluation.corpus.snapshots import load_snapshots
from ..evaluation.corpus.annotations import load_annotations, validate_annotations
from ..evaluation.corpus.scoring import compare_corpus
from ..evaluation.corpus.cli import DEFAULT_CORPUS

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


@router.get("/corpus-status")
async def corpus_status():
    """Local corpus readiness only, never arbitrary path reads or automatic SEC fetches."""
    note = "No live SEC requests are made; no unreviewed labels count as accuracy results."
    try:
        snaps = load_snapshots(DEFAULT_CORPUS)
        file = DEFAULT_CORPUS / "questions.jsonl"
        counts = {"reviewed": 0, "unreviewed": 0, "second_reviewed": 0}
        if file.is_file():
            labels, digest = load_annotations(file)
            counts = validate_annotations(labels, snaps)
            counts["annotation_sha256"] = digest
        return {"snapshots":len(snaps), "sources":[{"cik":s.cik,"form":s.form,
                    "accession":s.accession,"digest":s.text_sha256} for s in snaps],
                "annotations":counts, "note":note}
    except (ValueError, OSError) as exc:
        # Deliberately surface only the category of local review/corpus error, not paths or text.
        return {"snapshots":0,"sources":[],"annotations":{},
                "note":"Corpus validation failed; check the local snapshot and annotation files.",
                "validation_error":type(exc).__name__}


@router.get("/corpus-evaluation")
async def corpus_evaluation(require_second_review: bool = False):
    """Evaluate only reviewed, pinned local evidence; return no fabricated metrics.

    Paths cannot be selected by HTTP users. The results contain IDs and metrics,
    never raw source text, sensitive prompts, or arbitrary local file content.
    """
    file = DEFAULT_CORPUS / "questions.jsonl"
    if not file.is_file():
        return {"status":"not_evaluated","review_policy":
                "two_reviewers" if require_second_review else "one_reviewer",
                "methods":{}, "reason":"No local reviewed SEC question file is installed."}
    try:
        snapshots = load_snapshots(DEFAULT_CORPUS)
        labels, annotation_digest = load_annotations(file)
        report = compare_corpus(snapshots, labels, require_second_review=require_second_review)
        report["annotation_file_sha256"] = annotation_digest
        return report
    except (ValueError, OSError):
        return {"status":"not_evaluated", "methods":{},
                "reason":"Local SEC evidence or annotation validation failed.",
                "review_policy":"two_reviewers" if require_second_review else "one_reviewer"}
