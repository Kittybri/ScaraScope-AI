# v0.5 Source-linked financial Q&A retrieval benchmark

## What was tested

The v0.5 release provides a repeatable comparison of **lexical term matching vs. Okapi BM25**, both operating over *exactly the same* 18 synthetic reference-table passages. The passages are reconstructed mechanically from pre-recorded SEC-source-linked Microsoft FY2022–24 and Apple FY2021–23 income statement figures in `scarascope/evaluation/datasets/sec_annual_reference_v1.json`. They are **not raw 10-K paragraphs or newly downloaded XBRL**. Original SEC URLs and accession numbers are retained to make the financial reference verifiable.

Two frozen, question-level datasets exist:

- `qa_dev_v1.jsonl`: 17 manually phrased questions, including three intentionally unanswerable examples.
- `qa_heldout_v1.jsonl`: 14 different questions, including two intentionally unanswerable examples (12 answerable). Questions have separate IDs. An **earlier draft of held-out questions was inspected** during development of fiscal-year tokenization, so its scores were discarded. The published held-out question set was frozen *after* that change, and BM25 parameters and tokenization were **not modified after evaluating the replacement set**. This is still a small author-created test, not independently verified or external. Underlying source issuers, financial periods, and values **are shared across splits**, so this is **not** issuer-held-out or external/generalization testing. The QA fixtures were authored for this project and haven't been independently human-audited.

Each answerable case has an **exact gold document ID**, value in USD millions, original SEC accession and filing URL. Dataset loader validates source URLs, accessions and figures against the frozen reference dataset; duplicate or malformed cases fail loudly.

## Results for the initial v0.5 local run

| Held-out metric | Lexical baseline | BM25 |
| --- | ---: | ---: |
| Recall@1 | 16.67% | 66.67% |
| Recall@3 | 66.67% | 100.00% |
| Recall@5 | 66.67% | 100.00% |
| MRR@5 | 0.3889 | 0.8333 |
| Correctly empty results on unanswerable questions | 1/2 | 1/2 |

**These are retrieval-ranking outcomes for 12 answerable and 2 unanswerable constructed examples, not LLM answer accuracy.** One unanswerable financial question was incorrectly matched by both methods. A small fixture corpus and year-token improvements in BM25 account for much of the measured lift; results should not be extrapolated to real SEC 10-K HTML, diverse companies, full filings, financial reasoning, or current markets. Runtime depends on hardware; the benchmark separately records local ranking time in milliseconds but does not represent network, API or generation latency.

Run fresh measured results:

```bash
python -m pytest -q
python -m scarascope.evaluation.runner --fail-on-regression
```

Then open `http://127.0.0.1:8000/engineering` and click **Run offline benchmark**, or call the authenticated `GET /api/engineering/retrieval-comparison` endpoint. Each JSON result records the frozen dataset SHA-256, source-reference SHA-256, corpus size, question count, source URLs, metric denominators, per-question rankings and failures. CI uploads benchmark JSON and pytest JUnit artifacts. Two regression gates prevent BM25 from being worse than the lexical baseline on held-out Recall@3 and empty-result abstention; **passing the gates is not a declaration that either method is accurate enough for deployment**.

## Grounding improvements

`verification/grounding.py` checks explicit **numerical tokens in each sentence against only the cited evidence labels for that sentence**, closing the earlier loophole where a number found in an unrelated retrieved excerpt could pass. Missing labels, unknown labels and unsupported numbers trigger deterministic passage-only fallback. This is a **conservative syntactic/number check**, not natural-language entailment, correct accounting, semantic units, implied arithmetic, or proof a cited passage supports a qualitative statement. Test fixtures include injected instructions and misleading number placements.

## Honest next validation step

Prepare an independently manually reviewed, multi-issuer full-filing question set with stable original passage locators, then evaluate semantic answer quality and refusal behavior on real Ollama/Groq responses. Do not choose a default retriever based solely on these reconstructed snippets. The document-Q&A API keeps **lexical as the default**, with experimental BM25 opt-in on the dashboard or using `retrieval_strategy="bm25"`.
