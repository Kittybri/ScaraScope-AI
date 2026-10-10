"""Per-run public-source fingerprints, timings and inference metadata.

No request prompt, full passage content, personal documents, tokens or secrets are
stored in the manifest. This is per-response evidence, not persistent tracing.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4
from pydantic import BaseModel, Field

from ..ai.retrieval.lexical import EvidencePassage


class EvidenceFingerprint(BaseModel):
    evidence_id: str
    accession: str
    excerpt_sha256: str
    start_char: int


class RunProvenance(BaseModel):
    run_id: str = Field(default_factory=lambda: "rs_" + uuid4().hex)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    retrieval_strategy: str
    privacy_policy: str
    form: str
    accession: str | None = None
    references: list[EvidenceFingerprint] = Field(default_factory=list)
    provider: str = "none"
    model: str = "none"
    retrieval_ms: float = 0.0
    generation_ms: float = 0.0
    total_ms: float = 0.0
    benchmarked: bool = False


def fingerprint(passage: EvidencePassage) -> EvidenceFingerprint:
    return EvidenceFingerprint(evidence_id=passage.evidence_id, accession=passage.accession,
                               start_char=passage.start_char,
                               excerpt_sha256=sha256(passage.excerpt.encode("utf-8")).hexdigest())
