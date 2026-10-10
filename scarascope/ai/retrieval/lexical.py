"""Transparent lexical retrieval over bounded chunks, without embeddings or an LLM.

This is sparse retrieval-augmented generation, not semantic vector search. It
operates on SEC filing sections previously retrieved from official SEC URLs.
Each passage retains exact contiguous text and a section-relative character offset.
"""
from __future__ import annotations

from hashlib import sha256
import re
from pydantic import BaseModel, Field
from ...data.sec.filings import FilingSection

MAX_CHUNK_CHARS = 1000
OVERLAP_CHARS = 120
MAX_INDEXED_CHUNKS = 1200
STOP_WORDS = frozenset({
    "what", "which", "where", "when", "these", "those", "there", "about", "their", "does",
    "have", "from", "with", "this", "that", "please", "explain", "describe", "provide", "show",
    "tell", "company", "filing", "annual", "quarterly", "report", "and", "for", "how", "are",
    "into", "were", "was", "the", "our", "they", "its", "your", "would", "could", "should",
})


def terms(text: str) -> set[str]:
    words = re.findall(r"[a-z][a-z0-9]{2,}", text.lower())
    return {w[:-1] if w.endswith("s") and not w.endswith("ss") else w
            for w in words if w not in STOP_WORDS}


class EvidencePassage(BaseModel):
    evidence_id: str
    item: str
    section_title: str
    excerpt: str = Field(max_length=MAX_CHUNK_CHARS)
    filing_url: str
    accession: str
    filed: str
    locator: str
    start_char: int = Field(ge=0)
    relevance_score: float = 0.0


def chunk_sections(sections: list[FilingSection]) -> list[EvidencePassage]:
    passages: list[EvidencePassage] = []
    for section in sections:
        content = section.text
        at = 0
        while at < len(content) and len(passages) < MAX_INDEXED_CHUNKS:
            end = min(len(content), at + MAX_CHUNK_CHARS)
            if end < len(content):
                split_at = content.rfind(" ", at + MAX_CHUNK_CHARS // 2, end)
                if split_at > at:
                    end = split_at
            # Exact substring so evidence can be independently checked against source text.
            raw = content[at:end]
            if raw.strip():
                identifier = sha256(f"{section.accession}|{section.item}|{at}|{raw}".encode()).hexdigest()[:16]
                passages.append(EvidencePassage(
                    evidence_id=identifier, item=section.item, section_title=section.title,
                    excerpt=raw, filing_url=section.filing_url, accession=section.accession,
                    filed=section.filed, locator=section.locator, start_char=at,
                ))
            if end >= len(content):
                break
            at = max(at + 1, end - OVERLAP_CHARS)
    return passages


def search_passages(passages: list[EvidencePassage], question: str, limit: int = 5) -> list[EvidencePassage]:
    query = terms(question)
    if not query:
        return []
    ranked = []
    for passage in passages:
        words = terms(passage.excerpt)
        overlap = words & query
        if not overlap:
            continue
        coverage = len(overlap) / len(query)
        # Lexical ranking with query coverage. No invented relevance probabilities.
        frequency = sum(min(3, len(re.findall(rf"\b{re.escape(term)}s?\b", passage.excerpt.lower()))) for term in overlap)
        score = round(coverage * 10 + len(overlap) * 2 + frequency * 0.1, 3)
        ranked.append(passage.model_copy(update={"relevance_score": score}))
    ranked.sort(key=lambda p: (-p.relevance_score, p.accession, p.item, p.start_char))
    # Avoid returning neighboring overlapping chunks when they contain mostly the same text.
    unique = []
    for passage in ranked:
        if any(existing.accession == passage.accession and existing.item == passage.item
               and abs(existing.start_char - passage.start_char) < OVERLAP_CHARS * 2 for existing in unique):
            continue
        unique.append(passage)
        if len(unique) >= max(1, min(limit, 8)):
            break
    return unique
