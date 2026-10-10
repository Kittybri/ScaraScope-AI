"""Auditable, deliberately incomplete financial-answer verification.

This module detects syntactic, numeric, unit and fiscal-period mismatches. It
cannot infer qualitative entailment, denominators, causality or investment merit.
Never label the output as independently verified financial correctness.
"""
from __future__ import annotations

import re
from typing import Protocol

from pydantic import BaseModel, Field

from .citations import check_answer_citations
from .grounding import check_sentence_grounding
from .numeric_context import check_cited_units
from .sentences import cited_sentences


class Evidence(Protocol):
    label: str
    excerpt: str


_LABEL = re.compile(r"\[E\d+\]")
_YEAR = re.compile(r"\b(?:FY\s*|fiscal\s+(?:year\s+)?)(20\d{2}|19\d{2})\b", re.I)


class ClaimAudit(BaseModel):
    status: str  # rejected, needs_semantic_review, or extractive
    checked_sentences: int = 0
    cited_sentences: int = 0
    unreferenced_sentences: int = 0
    explicit_periods: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=lambda: [
        "Numeric, unit, fiscal-period and citation matching do not prove semantic entailment.",
        "Causal interpretations, derived ratios, denominators and other qualitative claims need review.",
    ])


def check_cited_periods(answer: str, sources: list[Evidence]) -> list[str]:
    """Reject only explicit FY references absent from that sentence's cited text.

    Dates in SEC text can be numerous; a *present* FY does not establish that
    an associated value belongs to that year. Such cases still need review.
    """
    by_label = {f"[{s.label}]": s.excerpt for s in sources}
    problems = []
    fragments = cited_sentences(answer)
    for position, fragment in enumerate(fragments, 1):
        years = set(_YEAR.findall(_LABEL.sub("", fragment)))
        if not years:
            continue
        labels = set(_LABEL.findall(fragment))
        if not labels or not labels.issubset(by_label):
            problems.append(f"Sentence {position} has an unverified fiscal year reference.")
            continue
        cited_years = set().union(*[set(_YEAR.findall(by_label[x])) for x in labels])
        if cited_years and not years.issubset(cited_years):
            problems.append(f"Sentence {position} cites a passage without its claimed fiscal year.")
    return problems


def audit_generated_answer(answer: str, sources: list[Evidence], *, extractive: bool = False) -> ClaimAudit:
    """Return an explainable audit with no invented confidence or support score."""
    if extractive:
        return ClaimAudit(status="extractive", checked_sentences=0)
    fragments = cited_sentences(answer)
    cited = sum(bool(_LABEL.search(f)) for f in fragments)
    issues = list(dict.fromkeys([
        *check_answer_citations(answer, sources),
        *check_sentence_grounding(answer, sources),
        *check_cited_units(answer, sources),
        *check_cited_periods(answer, sources),
    ]))
    # A nontrivial uncited sentence could contain unsupported qualitative
    # claims even when it contains no numbers. Treat it as review-needed.
    unreferenced = sum(
        bool(re.search(r"\b[a-zA-Z]{4,}\b", _LABEL.sub("", f))) and not _LABEL.search(f)
        for f in fragments
    )
    if unreferenced:
        issues.append(f"{unreferenced} substantive sentence(s) lack evidence citations.")
    years = sorted(set(_YEAR.findall(_LABEL.sub("", answer))))
    return ClaimAudit(
        status="rejected" if issues else "needs_semantic_review",
        checked_sentences=len(fragments), cited_sentences=cited,
        unreferenced_sentences=unreferenced, explicit_periods=years,
        issues=issues,
    )
