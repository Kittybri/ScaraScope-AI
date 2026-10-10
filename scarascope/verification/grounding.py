"""Conservative claim-to-cited-excerpt checks, not semantic entailment.

Checks numeric tokens *against the evidence cited by that sentence* instead of
allowing an unrelated retrieved passage to justify a claim. It does NOT infer
units, resolve textual contradictions or verify unstated numerical derivations.
"""
from __future__ import annotations

import re
from typing import Protocol
from .sentences import cited_sentences


class Passage(Protocol):
    label: str
    excerpt: str


_LABEL = re.compile(r'\[E\d+\]')
_NUMERIC = re.compile(r'(?<![\w])\$?\d[\d,]*(?:\.\d+)?%?')


def _numbers(text: str) -> set[str]:
    without_citations = _LABEL.sub('', text)
    return {token.replace(',', '') for token in _NUMERIC.findall(without_citations)}


def check_sentence_grounding(answer: str, sources: list[Passage]) -> list[str]:
    """Return visible failures; empty list is only *syntactic/numeric* validation."""
    by_label = {f'[{p.label}]':p.excerpt for p in sources}
    problems=[]
    if not by_label:
        return ['No evidence sources were provided.']
    merged = cited_sentences(answer)
    if not merged:
        return ['Empty answer.']
    for number,fragment in enumerate(merged,1):
        cited=set(_LABEL.findall(fragment))
        nums=_numbers(fragment)
        # Introductory non-claim text may omit citations; claims with numbers may not.
        if nums and not cited:
            problems.append(f'Sentence {number} has uncited numerical claims.')
            continue
        if not cited:
            continue
        missing=cited-by_label.keys()
        if missing:
            problems.append(f'Sentence {number} cites unknown evidence labels.')
            continue
        source_numbers=set().union(*(_numbers(by_label[key]) for key in cited))
        unsupported=nums-source_numbers
        if unsupported:
            problems.append(f'Sentence {number} uses numbers not present in its cited evidence: '
                            + ', '.join(sorted(unsupported)[:5]))
    return problems
