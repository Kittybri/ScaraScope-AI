"""Tamper-evident snapshots of actual SEC-extracted sections (never fabricated excerpts).

Snapshots are downloaded intentionally by the operator; CI never fetches SEC data.
Hashes cover the actual extracted section text, not just a filename or source URL.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator
from ...data.sec.filings import FilingResearch, FilingSection

MAX_SNAPSHOT_BYTES = 2_500_000
MAX_SECTIONS = 6
_CIK = re.compile(r"\d{10}")
_ACCESSION = re.compile(r"\d{10}-\d{2}-\d{6}")
_DOC = re.compile(r"[A-Za-z0-9_.-]{1,130}\.(?:htm|html|txt)", re.I)


def canonical_digest(sections: list[FilingSection]) -> str:
    text = json.dumps([s.model_dump(mode="json") for s in sections], sort_keys=True,
                      ensure_ascii=True, separators=(",", ":"))
    return sha256(text.encode("utf-8")).hexdigest()


def validate_source_url(url: str, cik: str, accession: str) -> None:
    parsed = urlsplit(url)
    parts = parsed.path.split("/")
    expected_prefix = ["", "Archives", "edgar", "data", str(int(cik)), accession.replace("-", "")]
    if (parsed.scheme != "https" or parsed.netloc != "www.sec.gov" or parsed.query or parsed.fragment
            or len(parts) != 7 or parts[:6] != expected_prefix or not _DOC.fullmatch(parts[6])):
        raise ValueError("Snapshot source must be the matching canonical SEC filing archive URL.")


class FilingSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    cik: str
    accession: str
    form: str
    filing_url: str
    captured_at: datetime
    sections: list[FilingSection] = Field(min_length=1, max_length=MAX_SECTIONS)
    text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_integrity(self):
        if self.schema_version != 1 or not _CIK.fullmatch(self.cik) or not _ACCESSION.fullmatch(self.accession):
            raise ValueError("Invalid SEC snapshot identity or schema version.")
        if self.form not in ("10-K", "10-Q"):
            raise ValueError("Only 10-K / 10-Q snapshots are supported.")
        validate_source_url(self.filing_url, self.cik, self.accession)
        items = []
        for section in self.sections:
            items.append(section.item)
            if (section.filing_url != self.filing_url or section.accession != self.accession
                    or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", section.filed)
                    or not section.text.strip() or len(section.text) > 250_000):
                raise ValueError("Section metadata does not match its filing snapshot.")
        if len(set(items)) != len(items):
            raise ValueError("Duplicate filing section identifiers.")
        if canonical_digest(self.sections) != self.text_sha256:
            raise ValueError("Snapshot section-text digest mismatch.")
        return self


def make_snapshot(filing: FilingResearch, form: str, captured_at: datetime | None = None) -> FilingSnapshot:
    """Do not silently represent missing/extraction-failed filing sections as a corpus."""
    if not filing.accession or not filing.filing_url or not filing.sections:
        raise ValueError("SEC filing unavailable or no supported sections were extracted.")
    return FilingSnapshot(cik=filing.cik, accession=filing.accession, form=form,
                          filing_url=filing.filing_url,
                          captured_at=captured_at or datetime.now(timezone.utc),
                          sections=filing.sections,
                          text_sha256=canonical_digest(filing.sections))


def save_snapshot(snapshot: FilingSnapshot, file: Path) -> Path:
    file = Path(file)
    # Validate again rather than assuming caller cannot mutate Pydantic fields.
    content = snapshot.model_dump_json(indent=2) + "\n"
    if len(content.encode("utf-8")) > MAX_SNAPSHOT_BYTES:
        raise ValueError("SEC snapshot exceeds local size cap.")
    file.parent.mkdir(parents=True, exist_ok=True)
    if file.exists() or file.is_symlink():
        # Same accession with changed filing text must not silently invalidate gold evidence IDs.
        existing = load_snapshot(file)
        if existing.text_sha256 != snapshot.text_sha256 or existing.model_dump(exclude={"captured_at"}) != snapshot.model_dump(exclude={"captured_at"}):
            raise ValueError("Existing pinned snapshot differs; preserve the old file and review the change separately.")
        return file
    temporary = file.with_suffix(file.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(file)
    return file


def load_snapshot(file: Path) -> FilingSnapshot:
    file = Path(file)
    if file.is_symlink() or not file.is_file() or file.stat().st_size > MAX_SNAPSHOT_BYTES:
        raise ValueError("Snapshot is missing, oversized or a symbolic link.")
    return FilingSnapshot.model_validate_json(file.read_bytes())


def load_snapshots(folder: Path, *, maximum: int = 24) -> list[FilingSnapshot]:
    folder = Path(folder)
    if not folder.is_dir() or folder.is_symlink():
        return []
    files = sorted(folder.glob("*.json"))
    if len(files) > maximum:
        raise ValueError("Corpus has too many snapshots; narrow the inventory.")
    snapshots = [load_snapshot(file) for file in files]
    keys = [(s.cik, s.accession, s.form) for s in snapshots]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate filing snapshots in corpus.")
    return snapshots
