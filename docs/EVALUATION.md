# Evaluation methodology

**Version 0.4 update:** See [BENCHMARKS.md](BENCHMARKS.md) for the new, source-linked historical financial fixture dataset (34 cases), synthetic retrieval and provider reliability suites, benchmark CLI/JSON artifacts and `/engineering` dashboard. These are independent offline test scores, not LLM correctness metrics.

# Evaluation methodology

`python -m scarascope.evaluation.benchmark` evaluates a **small deterministic golden suite**.
It checks six arithmetic/edge cases including division by zero, negative income,
revenue growth and a DCF perpetuity. It is a smoke test, not evidence that a
language model answers real securities-analysis questions correctly.

The regression suite, `python -m pytest -q`, covers:

- SEC XBRL period selection and provenance.
- Revenue/margin calculations, cross-company comparisons, and DCF assumptions.
- Fictional offline demo and headless research orchestration.
- Provider fallback, local-only privacy and error handling.
- HTML filing-text section and excerpt validation using synthetic fixtures.
- PDF/Excel exports and spreadsheet formula safety.
- Watchlist baseline vs. change check with a stub SEC provider.
- API authentication, route validation and request throttling.
- Module dependency boundaries to prevent a monolithic bot implementation.

## To report credible LLM quality numbers later

1. Choose a public benchmark (e.g. FinanceBench) and review dataset license.
2. Build a *held-out* set of SEC questions with authoritative values and evidence.
3. Log evaluation outcomes only, not private financial prompts. Report denominator and unsupported-question abstentions.
4. Evaluate hallucinated numerical values, retrieval relevance, citation support, provider fallback, latency percentiles and total model spending **independently**.
5. Compare Ollama and Groq on the same test split. Report missing-provider cases transparently rather than counting them as successes.
6. Do not label arithmetic fixture accuracy as financial reasoning or LLM accuracy.

## v0.3 document Q&A evaluation

`GET /api/evaluation/retrieval` runs five **fictional, deterministic** lexical
retrieval and abstention cases. They test whether a small fixture returns the
expected item/section. They are *not* an LLM factual accuracy score or evidence
of performance on FinanceBench, live EDGAR, or proprietary documents.

`tests/test_document_qa.py` also checks passage offsets are exact substrings,
invalid citation IDs trigger extractive fallback, absent evidence prevents
unsupported model calls, both 10-K and 10-Q parsing paths, privacy routing,
validation errors, and the static browser integration. Citation validation
checks reference label structure only. Even a response containing valid `[E1]`
can misstate what the evidence says; all investment-critical narrative claims
still require human review or stronger independently evaluated claim-level checks.

**Next evidence-based steps:** Construct a held-out human-annotated corpus of
real filings and report recall@k, unsupported-question abstention, correct
reporting-period retrieval, citation attribution precision, provider latency,
and model-cost estimates with explicit denominators. Do not advertise fixture
scores as live-document or LLM reasoning scores.
