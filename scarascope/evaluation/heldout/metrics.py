"""Transparent, denominator-preserving retrieval metrics with exact-document gold labels."""
from __future__ import annotations


def score_ranking(ranked: list[list[str]], gold: list[str | None]) -> dict:
    if len(ranked) != len(gold) or not ranked:
        raise ValueError('Rankings and gold labels must be equally sized and nonempty.')
    answerable = sum(doc is not None for doc in gold)
    missing = len(gold) - answerable
    if not answerable or not missing:
        raise ValueError('Both answerable and unanswerable cases are required.')
    hit = {k: 0 for k in (1, 3, 5)}
    reciprocal = 0.0
    exact_abstentions = 0
    for ids, expected in zip(ranked, gold):
        if expected is None:
            exact_abstentions += not ids
            continue
        for k in hit:
            hit[k] += expected in ids[:k]
        if expected in ids:
            reciprocal += 1 / (ids.index(expected) + 1)
    return {
        'total':len(gold), 'answerable':answerable,'unanswerable':missing,
        'recall_at_1':round(hit[1]/answerable,4),
        'recall_at_3':round(hit[3]/answerable,4),
        'recall_at_5':round(hit[5]/answerable,4),
        'mrr_at_5':round(reciprocal/answerable,4),
        'abstention_accuracy':round(exact_abstentions/missing,4),
        'correct_abstentions':exact_abstentions,
    }
