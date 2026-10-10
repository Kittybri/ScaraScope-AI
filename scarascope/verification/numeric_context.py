"""Conservative syntax-level numeric-unit audit against *cited* passages.

This does not judge prose entailment or arithmetic. It flags clear percentage
and currency-unit swaps, a common financial hallucination failure mode.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
from typing import Protocol

class CitedSource(Protocol):
    label: str
    excerpt: str

_LABEL = re.compile(r"\[E\d+\]")
_VALUE = re.compile(r"(?<![\w.])(?P<currency>\$)?(?P<number>\d[\d,]*(?:\.\d+)?)\s*(?P<percent>%|percent\b|percentage\s+points?\b)?", re.I)
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")


def tokens(text: str) -> set[tuple[str, str]]:
    result = set()
    for match in _VALUE.finditer(_LABEL.sub("",text)):
        try:
            number = str(Decimal(match.group("number").replace(",", "")).normalize())
        except InvalidOperation:
            continue
        unit = "percent" if match.group("percent") else "USD" if match.group("currency") else "bare"
        result.add((number,unit))
    return result


def check_cited_units(answer: str, sources: list[CitedSource]) -> list[str]:
    """Report claim-number/unit combinations unsupported by corresponding citations.

    Bare numbers are too ambiguous to prove units; only reject explicit `%` / `$`
    claims when the cited text has the same value in an explicitly incompatible form.
    """
    by_label={f"[{p.label}]":p.excerpt for p in sources}
    problems=[]
    for position,fragment in enumerate(_SENTENCE.split(answer.strip()),1):
        cites=set(_LABEL.findall(fragment))
        if not cites or not cites.issubset(by_label):
            continue  # citation and uncited-numeric checks are enforced separately
        evidence=set().union(*(tokens(by_label[label]) for label in cites))
        for num,unit in tokens(fragment):
            if unit=="bare":
                continue
            alternatives={u for n,u in evidence if n==num}
            if alternatives and unit not in alternatives:
                problems.append(f"Sentence {position} has unsupported explicit {unit} unit for value {num}.")
    return problems
