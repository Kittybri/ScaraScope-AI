"""Opt-in semantic ranking with a locally installed sentence embedding model.

No model download occurs in this module. A local model directory must be given
explicitly; no cloud embedding API is used. Similarity is NOT evidence of support.
"""
from __future__ import annotations

from math import isfinite, sqrt
from pathlib import Path
from typing import Protocol, Sequence

from .lexical import EvidencePassage, OVERLAP_CHARS, MAX_INDEXED_CHUNKS


class EmbeddingEncoder(Protocol):
    def encode(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...


class LocalSentenceEncoder:
    """Load only a model already installed on disk. No silent HF download."""

    def __init__(self, model_path: str):
        path = Path(model_path).expanduser().resolve()
        if not path.is_dir():
            raise ValueError("Semantic search needs an existing local model directory; see SCARASCOPE_EMBEDDING_MODEL_PATH.")
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ValueError("Install the optional local embedding dependencies: pip install -e '.[semantic]'.") from exc
        # Limit the loaded model to a local directory. Disallow remote model code.
        self.model = SentenceTransformer(str(path), local_files_only=True, trust_remote_code=False)

    def encode(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        return self.model.encode(list(texts), convert_to_numpy=True, show_progress_bar=False).tolist()


def _normalized(vector: Sequence[float]) -> list[float] | None:
    values = [float(x) for x in vector]
    if not values or len(values) > 4096 or not all(isfinite(x) for x in values):
        raise ValueError("Embedding model returned invalid or oversized vectors.")
    magnitude = sqrt(sum(x * x for x in values))
    if magnitude == 0:
        return None
    return [x / magnitude for x in values]


def search_semantic(passages: list[EvidencePassage], question: str, encoder: EmbeddingEncoder,
                    limit: int = 5, *, minimum_similarity: float = 0.35) -> list[EvidencePassage]:
    """Rank by cosine similarity; threshold is provisional, not calibrated accuracy."""
    if not 0 <= minimum_similarity <= 1:
        raise ValueError("Invalid similarity threshold.")
    if not question.strip() or not passages:
        return []
    if len(passages) > MAX_INDEXED_CHUNKS:
        raise ValueError("Semantic indexing limit exceeded.")
    vectors = encoder.encode([question, *[p.excerpt for p in passages]])
    if len(vectors) != len(passages) + 1:
        raise ValueError("Embedding model returned the wrong number of vectors.")
    query = _normalized(vectors[0])
    if query is None:
        return []
    ranked = []
    for passage, raw in zip(passages, vectors[1:]):
        doc = _normalized(raw)
        if doc is None or len(doc) != len(query):
            raise ValueError("Embedding dimension mismatch or zero vector.")
        score = sum(x * y for x, y in zip(query, doc))
        if score >= minimum_similarity:
            ranked.append(passage.model_copy(update={"relevance_score": round(score, 6)}))
    ranked.sort(key=lambda p: (-p.relevance_score, p.accession, p.item, p.start_char))
    output = []
    for passage in ranked:
        if any(passage.accession == previous.accession and passage.item == previous.item
               and abs(passage.start_char - previous.start_char) < OVERLAP_CHARS * 2 for previous in output):
            continue
        output.append(passage)
        if len(output) >= max(1, min(limit, 8)):
            break
    return output
