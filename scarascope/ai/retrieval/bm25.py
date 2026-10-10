"""Dependency-free BM25 ranking over the same immutable evidence passages as lexical.

Uses standard Okapi BM25 with length normalization; zero query overlap abstains.
Scores are ranking scores, not probabilities or assertions of factual support.
"""
from __future__ import annotations

from collections import Counter
from math import log
from .lexical import EvidencePassage, STOP_WORDS, OVERLAP_CHARS
import re


def _tokens(text: str) -> list[str]:
    words = re.findall(r"(?:19|20)\d{2}|[a-z][a-z0-9]{2,}", text.lower())
    words += re.findall(r"\bfy((?:19|20)\d{2})\b", text.lower())
    return [word[:-1] if word.endswith('s') and not word.endswith('ss') else word
            for word in words if word not in STOP_WORDS]


def search_bm25(passages: list[EvidencePassage], question: str, limit: int = 5,
                *, k1: float = 1.2, b: float = 0.75) -> list[EvidencePassage]:
    """Search bounded, pre-extracted SEC evidence. No network calls or embeddings."""
    if not (0 < k1 <= 3 and 0 <= b <= 1):
        raise ValueError('Invalid BM25 parameters.')
    query = set(_tokens(question))
    if not query or not passages:
        return []
    documents = [Counter(_tokens(p.excerpt)) for p in passages]
    n = len(documents)
    average_length = sum(sum(d.values()) for d in documents) / n or 1
    document_frequency = Counter(word for doc in documents for word in doc)
    ranked: list[EvidencePassage] = []
    for passage, doc in zip(passages, documents):
        length = sum(doc.values())
        score = 0.0
        for term in query:
            tf = doc.get(term, 0)
            if tf:
                df = document_frequency[term]
                idf = log(1 + (n - df + 0.5) / (df + 0.5))
                score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * length / average_length))
        if score:
            ranked.append(passage.model_copy(update={'relevance_score': round(score, 6)}))
    ranked.sort(key=lambda p: (-p.relevance_score, p.accession, p.item, p.start_char))
    unique = []
    for passage in ranked:
        if any(other.accession == passage.accession and other.item == passage.item
               and abs(other.start_char - passage.start_char) < OVERLAP_CHARS * 2 for other in unique):
            continue
        unique.append(passage)
        if len(unique) >= max(1, min(limit, 8)):
            break
    return unique
