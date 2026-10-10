# ScaraScope v0.8: independent evidence review and regression protocol

This document describes **how to produce a defensible accuracy claim**.
It does not claim that the reviewed corpus, human sign-off or measured AI quality
already exists. Locally generated questions are *unreviewed by default*.

## Review a real SEC source, not a generated draft

1. Configure a real `SEC_USER_AGENT`, then follow [REAL_SEC_CORPUS.md](REAL_SEC_CORPUS.md) to ingest 10-K/10-Q extracted sections for at least two issuers. Inspect the original SEC accession, form, filed date and **full section text**. Downloaded snapshots stay in gitignored `data/sec-corpus/`.
2. Freeze the accession- and SHA-256-pinned snapshot. Use the corpus inventory to inspect source-derived passage IDs. A historical SEC link alone does not establish a verified paragraph quote or gold answer.
3. For a development question, have the first reviewer validate the factual answer, fiscal period, unit, and direct support in the exact passage ID. Set `review_status=reviewed`, `reviewer`, `reviewer_notes`, and, where applicable, `gold_answer` and `gold_evidence_ids`. For unanswerable cases do not invent any evidence IDs.
4. A **different person** should independently assess the original filing and the labels without being primed by the first review. Record their different alias in `second_reviewer` and their reasoning in `second_review_notes` **after agreement or documented reconciliation**. An alias is only a self-attestation and does not prove identity or independence. We intentionally do not let software invent this step.
5. Reserve different issuers, not merely different question phrasing, for `heldout`. Do not modify ranking configuration or prompts after observing held-out results. If a held-out failure leads to tuning, retire that set and freeze a new evaluation set.
6. Report numerator, denominator, model/retriever, corpus hash, accession hashes and failure details. Separately label retrieval scores, source correctness and live AI answer accuracy. Human review is not implied by green CI or lint checks.

## Audit your evidence without producing accuracy scores

```bash
python -m scarascope.evaluation.corpus.cli inventory --corpus data/sec-corpus
python -m scarascope.evaluation.corpus.cli audit \
  --corpus data/sec-corpus --annotations data/sec-corpus/questions.jsonl \
  --output data/benchmarks/review-audit.json
```

The metadata-only audit flags `unreviewed`, `first_review_missing_rationale`, and `second_review_pending` by question ID. It shows self-reported review counts only, not answer correctness. Review the data and source documents yourself before changing labels.

## Run strict issuer-held-out retrieval evaluation

```bash
python -m scarascope.evaluation.corpus.cli evaluate \
  --corpus data/sec-corpus --annotations data/sec-corpus/questions.jsonl \
  --split heldout --require-second-review \
  --output data/benchmarks/heldout-baseline.json
```

When the strict set contains no reviewed answerable cases or no reviewed unanswerable cases, the command exits nonzero with `status=not_evaluated` and no scores. Cases without a second review are excluded from scores. Both reviewers must be different aliases with written notes.

To detect regressions **on exactly the same corpus, dataset and review policy**:

```bash
python -m scarascope.evaluation.corpus.cli evaluate \
  --corpus data/sec-corpus --annotations data/sec-corpus/questions.jsonl \
  --split heldout --require-second-review \
  --baseline data/benchmarks/heldout-baseline.json \
  --fail-on-regression --output data/benchmarks/heldout-new.json
```

If any shared Recall@1/3/5, MRR@5 or abstention metric decreases, the CLI exits with code **3**. Comparing different source hashes, splits, question sets, review policies, denominators or retriever sets is **rejected**, not silently accepted as a comparable result. Same-corpus scores remain *retrieval-only*; no LLM correctness is proven.

## Financial claim checking limitations

The document-answer route now separately inspects explicit `%` and `$` claims against **their cited excerpt** in addition to existing number/citation checks. Numeric equality and compatible symbols are only syntactic signals. A statement can pass these checks while using a wrong context, misleading denominator or unsupported causal relationship. Verify consequential AI claims manually and build gold answer labels for fuller evaluations.

## Engineering Lab

The `/engineering` view has a **separate real-corpus comparison panel** and a checkbox to require two reviewers. When there is no reviewed local SEC corpus, it displays `not_evaluated`; the fictional/reconstructed benchmark scores are never substituted for it.

**Security:** Do not commit raw downloaded filings without reviewing redistribution rights, private prompts, local provider credentials or application logs. The corpus and private benchmark reports should remain under `data/` (gitignored). No API call will ingest live documents just by viewing the Engineering Lab.
