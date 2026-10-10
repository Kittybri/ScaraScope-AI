"""Common sentence segmentation that attaches trailing evidence labels to claims."""
from __future__ import annotations
import re

_BOUNDARY = re.compile(r"(?<=[.!?])\s+|\n+")
_ONLY_CITATIONS = re.compile(r"(?:\[E\d+\]\s*)+")


def cited_sentences(answer: str) -> list[str]:
    parts = [part.strip() for part in _BOUNDARY.split(answer.strip()) if part.strip()]
    merged: list[str] = []
    for part in parts:
        if merged and _ONLY_CITATIONS.fullmatch(part):
            merged[-1] += " " + part
        else:
            merged.append(part)
    return merged
