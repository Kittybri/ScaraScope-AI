"""Metadata-only review-readiness report for an operator's pinned SEC corpus.

Counts review attestations and detects absent justification. It cannot attest
that either human read the actual filing, or that the answer is correct.
"""
from __future__ import annotations

from .annotations import Annotation, validate_annotations
from .snapshots import FilingSnapshot


def review_audit(cases: list[Annotation], snapshots: list[FilingSnapshot]) -> dict:
    counts = validate_annotations(cases, snapshots)
    gaps = []
    for case in cases:
        issues = []
        if case.review_status != "reviewed":
            issues.append("unreviewed")
        else:
            if not (case.reviewer_notes or "").strip():
                issues.append("first_review_missing_rationale")
            if not case.second_reviewer:
                issues.append("second_review_pending")
        if issues:
            gaps.append({"id":case.id,"split":case.split,"checks":issues})
    return {"status":"metadata_review_only", "cases":len(cases),
            "reviewed":counts["reviewed"],"second_reviewed":counts["second_reviewed"],
            "development_issuers":len(counts["dev_issuers"]),
            "heldout_issuers":len(counts["heldout_issuers"]),
            "gaps":gaps,
            "limitation":"Reviewer aliases and notes are self-reported; no independent human review is established by this audit."}
