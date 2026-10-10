"""Hybrid BM25 and local semantic search via rank fusion, not model inference."""
from __future__ import annotations

from .bm25 import search_bm25
from .lexical import EvidencePassage, OVERLAP_CHARS
from .semantic import EmbeddingEncoder, search_semantic


def search_hybrid(passages: list[EvidencePassage], question: str, encoder: EmbeddingEncoder,
                  limit: int = 5, *, rrf_k: int = 60) -> list[EvidencePassage]:
    if rrf_k < 1:
        raise ValueError("rrf_k must be positive.")
    limit = max(1, min(8, limit))
    sparse = search_bm25(passages, question, limit=8)
    dense = search_semantic(passages, question, encoder, limit=8)
    originals: dict[str, EvidencePassage] = {}
    scores: dict[str, float] = {}
    for ranked in (sparse, dense):
        for position, passage in enumerate(ranked, start=1):
            originals[passage.evidence_id] = passage
            scores[passage.evidence_id] = scores.get(passage.evidence_id, 0) + 1.0 / (rrf_k + position)
    ordered = sorted(originals.values(), key=lambda p: (-scores[p.evidence_id], p.accession, p.item, p.start_char))
    output = []
    for passage in ordered:
        if any(passage.accession == old.accession and passage.item == old.item
               and abs(passage.start_char - old.start_char) < OVERLAP_CHARS * 2 for old in output):
            continue
        output.append(passage.model_copy(update={"relevance_score": round(scores[passage.evidence_id], 6)}))
        if len(output) == limit:
            break
    return output
