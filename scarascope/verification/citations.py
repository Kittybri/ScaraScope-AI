"""Bounded checks for document answer citation IDs and unsupported numerical claims."""
import re
from typing import Protocol


class _Passage(Protocol):
    label: str
    excerpt: str


_TOKEN = re.compile(r"(?<![A-Za-z])(?<!\[E)(?<!\w)\$?\d[\d,]*(?:\.\d+)?%?")


def check_answer_citations(answer: str, sources: list[_Passage]) -> list[str]:
    valid = {f"[{p.label}]" for p in sources}
    cited = set(re.findall(r"\[E\d+\]", answer))
    malformed = set(re.findall(r"\[E[^\]\n]*\]", answer)) - cited
    problems = []
    if malformed or not cited or not cited.issubset(valid):
        problems.append("Missing, malformed, or unknown evidence reference.")
    # This checks only exact explicit numeric claims, not textual entailment or derived ratios.
    prose = re.sub(r"\[E\d+\]", "", answer)
    present = set()
    for passage in sources:
        present.update(_TOKEN.findall(passage.excerpt))
    numbers = set(_TOKEN.findall(prose))
    unexpected = numbers - present
    if unexpected:
        problems.append("Numerical claim not found verbatim in cited excerpts: " + ", ".join(sorted(unexpected)[:5]))
    return problems
