"""Issuer-held-out retrieval scoring with strict reviewer gating.

No model-answer accuracy is claimed: exact passage retrieval and abstention only.
"""
from __future__ import annotations
from hashlib import sha256
import json
from time import perf_counter
from ...ai.retrieval import chunk_sections, search_passages, search_bm25, search_semantic, search_hybrid
from ...ai.retrieval.semantic import EmbeddingEncoder
from .annotations import Annotation, validate_annotations
from .snapshots import FilingSnapshot


def compare_corpus(snapshots: list[FilingSnapshot], cases: list[Annotation], *,
                   split: str = "heldout", encoder: EmbeddingEncoder | None = None) -> dict:
    if split not in {"dev", "heldout"}:
        raise ValueError("Invalid corpus evaluation split.")
    integrity = validate_annotations(cases, snapshots)
    questions = [c for c in cases if c.split == split]
    reviewed = [c for c in questions if c.review_status == "reviewed"]
    snapshot_index = {(s.cik, s.accession): s for s in snapshots}
    dataset_hash = sha256(json.dumps([c.model_dump() for c in cases], sort_keys=True).encode()).hexdigest()
    manifest = {"benchmark":"real_sec_extracted_filing_passage_retrieval_v1", "split":split,
                "source_kind":"SEC-extracted filing sections from pinned downloaded snapshots",
                "dataset_sha256":dataset_hash,
                "snapshot_digests":{f"{s.cik}:{s.accession}":s.text_sha256 for s in snapshots},
                "questions_in_split":len(questions), "reviewed_in_split":len(reviewed),
                "excluded_unreviewed":len(questions)-len(reviewed),"review":integrity,
                "status":"not_evaluated", "methods":{},
                "limitations":["Only exact passage retrieval and empty-result abstention are measured; not LLM answer accuracy.",
                               "Review labels are attributed to reviewer aliases; no independent double-review is guaranteed.",
                               "Extraction and chunking can omit or alter SEC HTML structure; offsets are in normalized extracted text.",
                               "No unreviewed questions are included in accuracy denominators."]}
    if not reviewed:
        return manifest
    answerable = sum(c.answerable for c in reviewed)
    unanswerable = len(reviewed)-answerable
    if not answerable or not unanswerable:
        manifest["limitations"].append("Both answerable and unanswerable reviewed questions required for scores.")
        return manifest
    methods = {"lexical":search_passages, "bm25":search_bm25}
    if encoder is not None:
        methods["semantic"] = lambda passages, q, limit: search_semantic(passages,q,encoder,limit)
        methods["hybrid"] = lambda passages, q, limit: search_hybrid(passages,q,encoder,limit)
    for name, search in methods.items():
        hits = {1:0,3:0,5:0}
        rr = 0.0
        abstained = 0
        by_case = []
        total_ms = 0.0
        for case in reviewed:
            # Constrain retrieval to the intended filing; no accidental cross-issuer answer matching.
            passages = chunk_sections(snapshot_index[case.cik,case.accession].sections)
            started = perf_counter()
            ranked = search(passages,case.question,limit=5)
            total_ms += (perf_counter()-started)*1000
            ids = [p.evidence_id for p in ranked]
            if case.answerable:
                matching = [i for i,k in enumerate(ids) if k in case.gold_evidence_ids]
                rank = min(matching)+1 if matching else None
                if rank:
                    rr += 1/rank
                    for k in hits:
                        hits[k] += rank<=k
                ok = bool(rank and rank<=5)
            else:
                rank = None
                ok = not bool(ids)
                abstained += ok
            by_case.append({"id":case.id,"answerable":case.answerable,
                            "rank":rank,"passed":ok,"retrieved_evidence_ids":ids[:5],
                            "gold_evidence_ids":case.gold_evidence_ids})
        manifest["methods"][name] = {"metrics":{
            "recall_at_1":round(hits[1]/answerable,4),
            "recall_at_3":round(hits[3]/answerable,4),
            "recall_at_5":round(hits[5]/answerable,4),
            "mrr_at_5":round(rr/answerable,4),
            "abstention_accuracy":round(abstained/unanswerable,4),
            "answerable":answerable,"unanswerable":unanswerable,
            "correct_abstentions":abstained},
            "average_retrieval_ms":round(total_ms/len(reviewed),3),"cases":by_case}
    manifest["status"]="evaluated"
    return manifest
