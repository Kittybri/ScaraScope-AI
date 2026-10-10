"""Explicit, reproducible SEC intake plans. No URLs are fetched from plan input.

All network calls still go through FilingClient's SEC manifest verification, URL
allowlist, size caps and pacing. Plan links act only as identity assertions.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...data.sec.filings import FilingClient
from .annotations import Annotation, validate_annotations
from .snapshots import (
    FilingSnapshot, load_snapshot, load_snapshots, make_snapshot,
    save_snapshot, validate_source_url,
)


class QuestionSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=16, max_length=300)
    presumed_answerable: bool


class PlannedFiling(BaseModel):
    model_config = ConfigDict(extra="forbid")
    issuer: str = Field(min_length=2, max_length=60)
    cik: str = Field(pattern=r"^\d{10}$")
    accession: str = Field(pattern=r"^\d{10}-\d{2}-\d{6}$")
    form: Literal["10-K", "10-Q"]
    split: Literal["dev", "heldout"]
    expected_filing_url: str
    questions: list[QuestionSeed] = Field(min_length=2, max_length=10)

    @model_validator(mode="after")
    def check_source(self):
        validate_source_url(self.expected_filing_url, self.cik, self.accession)
        if len({x.question.strip().casefold() for x in self.questions}) != len(self.questions):
            raise ValueError("A filing plan contains duplicate questions.")
        return self


class IntakePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    filings: list[PlannedFiling] = Field(min_length=2, max_length=12)

    @model_validator(mode="after")
    def check_holdout(self):
        keys = [(x.cik, x.accession, x.form) for x in self.filings]
        if len(set(keys)) != len(keys):
            raise ValueError("Duplicate accession in intake plan.")
        dev = {x.cik for x in self.filings if x.split == "dev"}
        heldout = {x.cik for x in self.filings if x.split == "heldout"}
        if not dev or not heldout or dev & heldout:
            raise ValueError("Intake plan requires issuer-disjoint dev and heldout groups.")
        return self


def load_intake_plan(path: Path) -> tuple[IntakePlan, str]:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64000:
        raise ValueError("Intake plan is missing, oversized or a symbolic link.")
    raw = path.read_bytes()
    plan = IntakePlan.model_validate_json(raw)
    return plan, sha256(raw).hexdigest()


def _expected_snapshots(plan: IntakePlan, snapshots: list[FilingSnapshot]) -> list[FilingSnapshot]:
    index = {(s.cik, s.accession, s.form): s for s in snapshots}
    selected = []
    for item in plan.filings:
        snap = index.get((item.cik, item.accession, item.form))
        if snap is None:
            raise ValueError(f"Intake incomplete: no pinned snapshot for {item.issuer} {item.accession}.")
        if snap.filing_url != item.expected_filing_url:
            raise ValueError("Pinned snapshot URL differs from the versioned intake plan.")
        selected.append(snap)
    return selected


async def collect_intake(plan: IntakePlan, folder: Path, user_agent: str,
                         *, client: FilingClient | None = None) -> dict:
    """Download every planned accession, verify all identities, then write snapshots.

    Does not publish gold answers, mark reviews complete, or send filing text to
    an AI model. Filings are fetched in sequence under the existing SEC gate.
    """
    if not user_agent or "@" not in user_agent or "example.com" in user_agent.lower():
        raise ValueError("Configure a genuine SEC_USER_AGENT contact email before SEC intake.")
    client = client or FilingClient(user_agent)
    snapshots = []
    for item in plan.filings:
        filing = await client.research(item.cik, "risk operations revenue", form=item.form,
                                       accession=item.accession)
        snap = make_snapshot(filing, item.form)
        if (snap.cik != item.cik or snap.accession != item.accession or snap.form != item.form
                or snap.filing_url != item.expected_filing_url):
            raise ValueError("SEC filing does not match the pinned intake plan.")
        snapshots.append(snap)
    folder = Path(folder)
    # Preflight existing targets before writing new files. A changed extraction
    # cannot silently overwrite a source already used to assign evidence IDs.
    paths = [folder / f"{s.cik}_{s.accession}_{s.form}.json" for s in snapshots]
    for target, snap in zip(paths, snapshots):
        if target.is_symlink():
            raise ValueError("Refusing to replace a symbolic link snapshot.")
        if target.exists() and load_snapshot(target).model_dump(exclude={"captured_at"}) != snap.model_dump(exclude={"captured_at"}):
            raise ValueError("Existing pinned evidence changed; review extraction differences before replacing.")
    for target, snap in zip(paths, snapshots):
        save_snapshot(snap, target)
    return {"status":"collected_unreviewed", "filings":len(paths),
            "snapshots":[{"cik":s.cik,"accession":s.accession,"form":s.form,
                          "source_text_sha256":s.text_sha256,"file":str(p)}
                         for s,p in zip(snapshots,paths)],
            "reviewed_questions":0,
            "limitation":"Live source retrieval and local integrity do not establish human-reviewed gold answers."}


def question_drafts(plan: IntakePlan, snapshots: list[FilingSnapshot]) -> list[Annotation]:
    _expected_snapshots(plan, snapshots)
    questions = []
    for spec in plan.filings:
        for index, seed in enumerate(spec.questions, start=1):
            questions.append(Annotation(
                id=f"q_{spec.cik}_{spec.accession.replace('-', '')}_{index:02d}",
                split=spec.split, cik=spec.cik, accession=spec.accession,
                question=seed.question, answerable=seed.presumed_answerable,
                review_status="unreviewed", gold_evidence_ids=[], gold_answer=None,
                reviewer_notes="DRAFT: answerability and exact evidence must be independently checked."))
    validate_annotations(questions, snapshots)
    return questions


def write_drafts(annotations: list[Annotation], output: Path) -> Path:
    """Never overwrite a reviewer-edited annotation file."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x",encoding="utf-8") as stream:
        for a in annotations:
            stream.write(a.model_dump_json() + "\n")
    return output
