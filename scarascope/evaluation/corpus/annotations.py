"""Reviewer-gated labels: unreviewed gold answers must never enter accuracy scores."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .snapshots import FilingSnapshot
from ...ai.retrieval.lexical import chunk_sections

MAX_ANNOTATION_BYTES = 500_000


class Annotation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9_]{6,72}$")
    split: Literal["dev", "heldout"]
    cik: str = Field(pattern=r"^\d{10}$")
    accession: str = Field(pattern=r"^\d{10}-\d{2}-\d{6}$")
    question: str = Field(min_length=12, max_length=300)
    answerable: bool
    gold_evidence_ids: list[str] = Field(default_factory=list, max_length=8)
    gold_answer: str | None = Field(default=None, max_length=500)
    review_status: Literal["unreviewed", "reviewed"] = "unreviewed"
    reviewer: str | None = Field(default=None, max_length=80)
    reviewer_notes: str | None = Field(default=None, max_length=800)

    @model_validator(mode="after")
    def check_status(self):
        if self.review_status == "reviewed":
            if not self.reviewer or not self.reviewer.strip():
                raise ValueError("Reviewed labels require an identifiable reviewer alias.")
            if self.answerable and (not self.gold_evidence_ids or not self.gold_answer):
                raise ValueError("Answerable reviewed cases need an answer and exact evidence IDs.")
            if not self.answerable and (self.gold_evidence_ids or self.gold_answer):
                raise ValueError("Unanswerable reviewed cases cannot contain fabricated gold evidence.")
        return self


def load_annotations(file: Path) -> tuple[list[Annotation], str]:
    file = Path(file)
    if file.is_symlink() or not file.is_file() or file.stat().st_size > MAX_ANNOTATION_BYTES:
        raise ValueError("Annotation file missing, oversized or a symbolic link.")
    raw = file.read_bytes()
    items = [Annotation.model_validate(json.loads(row)) for row in raw.decode("utf-8").splitlines() if row.strip()]
    if not items or len({c.id for c in items}) != len(items):
        raise ValueError("Empty annotation set or duplicate question IDs.")
    return items, sha256(raw).hexdigest()


def validate_annotations(cases: list[Annotation], snapshots: list[FilingSnapshot],
                         *, require_issuer_holdout: bool = True) -> dict:
    inventory = {(snap.cik, snap.accession): snap for snap in snapshots}
    documents = {(snap.cik, snap.accession):
                 {p.evidence_id: p for p in chunk_sections(snap.sections)} for snap in snapshots}
    dev = {case.cik for case in cases if case.split == "dev"}
    held = {case.cik for case in cases if case.split == "heldout"}
    if require_issuer_holdout and dev & held:
        raise ValueError("Issuer leakage: dev and held-out must use disjoint CIKs.")
    for case in cases:
        key = (case.cik, case.accession)
        if key not in inventory:
            raise ValueError(f"Question {case.id} has no matching pinned snapshot.")
        passages = documents[key]
        if case.review_status == "reviewed":
            if len(case.gold_evidence_ids) != len(set(case.gold_evidence_ids)):
                raise ValueError(f"Duplicate gold evidence in {case.id}.")
            if any(gid not in passages for gid in case.gold_evidence_ids):
                raise ValueError(f"Question {case.id} references evidence missing from the pinned filing.")
    return {"reviewed":sum(c.review_status == "reviewed" for c in cases),
            "unreviewed":sum(c.review_status != "reviewed" for c in cases),
            "dev_issuers":sorted(dev), "heldout_issuers":sorted(held)}
