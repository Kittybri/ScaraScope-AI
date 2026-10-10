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
