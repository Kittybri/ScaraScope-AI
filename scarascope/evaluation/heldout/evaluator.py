"""Head-to-head lexical / BM25 evaluation on identical recorded-fact passages.

No language model or live SEC endpoint is called. Question-held-out scores
measure ranking and empty retrieval; they do not measure answers or semantic truth.
"""
from __future__ import annotations

import time
from ..financial_accuracy import load_reference
from ...ai.retrieval.semantic import EmbeddingEncoder, search_semantic
from ...ai.retrieval.hybrid import search_hybrid
from ...ai.retrieval import chunk_sections, search_passages, search_bm25
from .dataset import load_questions, reference_sections, validate_gold
from .metrics import score_ranking


def compare_retrievers(*, split: str = 'heldout', encoder: EmbeddingEncoder | None = None) -> dict:
    if split not in {'dev', 'heldout'}:
        raise ValueError('Unknown QA split.')
    data, reference_hash = load_reference()
    sections, documents = reference_sections(data)
    questions, qa_hash = load_questions(split)
    validate_gold(questions, documents)
    passages = chunk_sections(sections)
    methods = {'lexical':search_passages, 'bm25':search_bm25}
    if encoder is not None:
        methods['semantic'] = lambda docs, question, limit: search_semantic(docs, question, encoder, limit)
        methods['hybrid'] = lambda docs, question, limit: search_hybrid(docs, question, encoder, limit)
    results = {}
    for method, retrieval in methods.items():
        rankings = []
        cases = []
        total_ns = 0
        for case in questions:
            start = time.perf_counter_ns()
            hits = retrieval(passages, case.question, limit=5)
            total_ns += time.perf_counter_ns() - start
            ids = [p.item for p in hits]
            rankings.append(ids)
            cases.append({'id':case.id, 'question':case.question, 'answerable':case.answerable,
                          'gold_document_id':case.gold_document_id, 'retrieved_document_ids':ids,
                          'rank':(ids.index(case.gold_document_id)+1 if case.gold_document_id in ids else None)
                                 if case.answerable else None,
                          'passed':case.gold_document_id in ids[:5] if case.answerable else not bool(ids)})
        results[method] = {'metrics':score_ranking(rankings,[c.gold_document_id for c in questions]),
                           'average_retrieval_ms':round(total_ns/len(questions)/1_000_000,3),
                           'cases':cases}
    return {'benchmark':'source_linked_reconstructed_reference_qa_v1','split':split,
            'dataset_sha256':qa_hash, 'reference_sha256':reference_hash,
            'documents':len(passages), 'question_count':len(questions),
            'source_urls':sorted({doc['source_url'] for doc in documents.values()}),
            'methods':results,
            'semantic_evaluated': encoder is not None,
            'semantic_note':('Optional local model evaluated on the same reconstructed passages; no raw SEC or LLM scoring.'
                             if encoder is not None else 'Not evaluated. Supply an installed local embedding model to measure semantic and hybrid retrieval.'),
            'limitations':[
                'Question-held-out split over reference values already present in the project, not an external independent test corpus.',
                'Document passages are reconstructed from SEC-source-linked statement figures, not downloaded filing paragraphs.',
                'Measures exact-document recall, ranking and empty-result abstention; NOT answer accuracy or LLM grounding.',
                'Timing includes local ranking only; no model, index loading, network latency or dollar-cost measurement.'
            ]}
