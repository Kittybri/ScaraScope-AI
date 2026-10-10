"""Conservative instruction-like content screening at the retrieval trust boundary.

This is a defense-in-depth filter, not proof against prompt injection. A detected
instruction only disables optional LLM synthesis; evidence remains inspectable.
"""
from __future__ import annotations

import re
from typing import Protocol


class Excerpt(Protocol):
    excerpt: str


_INJECTION_MARKERS = (
    re.compile(r"\bignore\s+(?:all\s+)?(?:previous|prior|system|developer)\s+instructions?\b", re.I),
    re.compile(r"\b(?:reveal|print|disclose)\s+(?:the\s+)?(?:system|developer)\s+prompt\b", re.I),
    re.compile(r"\b(?:send|exfiltrate|upload)\s+(?:the\s+)?(?:api\s+keys?|secrets?|credentials?)\b", re.I),
    re.compile(r"\b(?:you\s+are\s+now|new\s+system\s+instructions?)\b", re.I),
    re.compile(r"\b(?:execute|invoke|run)\s+(?:the\s+)?(?:tool|shell|command)\b", re.I),
)


def suspicious_source_instructions(sources: list[Excerpt]) -> bool:
    return any(pattern.search(source.excerpt) for source in sources for pattern in _INJECTION_MARKERS)
