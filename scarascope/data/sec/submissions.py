"""Validated SEC submissions metadata for historical-accession pinning.

No caller may supply an arbitrary filing URL. Only an accession listed in SEC's
submissions index for the requested CIK and form can be downloaded.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any

from .client import SECError

ACCESSION_PATTERN = r"\d{10}-\d{2}-\d{6}"
ARCHIVE_NAME_PATTERN = re.compile(r"CIK(\d{10})-submissions-\d{3}\.json")
DOCUMENT_PATTERN = re.compile(r"[A-Za-z0-9_.-]{1,130}\.(?:htm|html|txt)", re.I)
MAX_ARCHIVE_INDEXES = 12


@dataclass(frozen=True)
class FilingRecord:
    accession: str
    form: str
    document: str
    filed: str

    def url(self, cik: str) -> str:
        return (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                f"{self.accession.replace('-', '')}/{self.document}")


def choose_record(index: dict[str, Any], form: str, accession: str | None = None) -> FilingRecord | None:
    """Read SEC's parallel submission arrays; reject malformed matching metadata."""
    if not isinstance(index, dict):
        raise SECError("Malformed SEC submissions index.")
    fields = ("form", "accessionNumber", "primaryDocument", "filingDate")
    arrays = [index.get(field) for field in fields]
    if any(not isinstance(rows, list) for rows in arrays):
        raise SECError("Incomplete SEC submission fields.")
    count = len(arrays[0])
    if any(len(rows) != count for rows in arrays[1:]):
        raise SECError("Mismatched SEC submission field lengths.")
    for f, acc, document, filed in zip(*arrays):
        if (accession is None and f == form) or (accession is not None and acc == accession):
            if f != form:
                raise SECError("Requested SEC accession belongs to a different filing form.")
            if (not isinstance(acc, str) or not re.fullmatch(ACCESSION_PATTERN, acc)
                    or not isinstance(document, str) or not DOCUMENT_PATTERN.fullmatch(document)
                    or not isinstance(filed, str)):
                raise SECError("SEC returned invalid filing metadata.")
            try:
                date.fromisoformat(filed)
            except ValueError as exc:
                raise SECError("SEC returned an invalid filing date.") from exc
            return FilingRecord(acc, f, document, filed)
    return None


def archive_index_names(submissions: dict[str, Any], cik: str) -> list[str]:
    """Bound and validate archive page URLs BEFORE making any secondary requests."""
    groups = submissions.get("filings")
    if not isinstance(groups, dict):
        raise SECError("Malformed SEC submissions document.")
    entries = groups.get("files", [])
    if not isinstance(entries, list) or len(entries) > MAX_ARCHIVE_INDEXES:
        raise SECError("Too many or invalid SEC archive indexes; use a narrower archival data source.")
    names = []
    for entry in entries:
        name = entry.get("name") if isinstance(entry, dict) else None
        match = ARCHIVE_NAME_PATTERN.fullmatch(name) if isinstance(name, str) else None
        if not match or match.group(1) != cik:
            raise SECError("SEC returned an unsafe or mismatched historical index filename.")
        if name in names:
            raise SECError("SEC returned duplicate historical submission indexes.")
        names.append(name)
    return names
