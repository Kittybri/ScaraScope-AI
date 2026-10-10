# Engineering validation: reproducible benchmarks

ScaraScope's **Engineering Lab** at `/engineering` runs entirely offline. Results are **test outcomes**, not marketing estimates. This release provides reproducible evidence for deterministic financial processing, not a score for free-form LLM reasoning or live EDGAR correctness.

## Datasets and their actual scopes

| Suite | Cases | Source | What a passing score measures |
| --- | ---: | --- | --- |
| Historical financial figures | 34 | Fixed figures from Microsoft FY2024 and Apple FY2023 SEC 10-K financial statements | Matching amounts, computed margins and YoY growth, reporting-period checks, source-metadata structure |
| Arithmetic | 6 | Hand-authored deterministic edge cases | Percentage calculations, missing values, simplified DCF |
| Lexical retrieval | 5 | Synthetic text passages | Keyword matching, selection and no-match abstention |
| Provider reliability | 6 | Simulated Groq/Ollama stubs | Fallback decisions, privacy boundaries and no-key graceful degradation |

The historical values are manually transcribed into [`scarascope/evaluation/datasets/sec_annual_reference_v1.json`](../scarascope/evaluation/datasets/sec_annual_reference_v1.json). The independently **recorded expected results** are compared to the actual Python engine outputs, rather than having the system derive both expected and actual from the same function. The source files are:

- [Microsoft FY2024 Form 10-K, Consolidated Statements of Income](https://www.sec.gov/Archives/edgar/data/789019/000095017024087843/msft-20240630.htm), figures for FY2022–FY2024, **USD millions**.
- [Apple FY2023 Form 10-K, Consolidated Statements of Operations](https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm), figures for FY2021–FY2023, **USD millions**.

The source date and accession of the *containing filing* are preserved alongside each three-year comparison. A 2024 10-K can contain audited FY2022 figures, so the accession does not equal each individual year's original first filing. The references are historical, **not current forecasts**, not live API snapshots, and not a complete dataset of public companies.

## Run and reproduce

```bash
pip install -e '.[test]'
python -m pytest -q
python -m scarascope.evaluation.runner --fail-on-regression
# Optional named result:
python -m scarascope.evaluation.runner --fail-on-regression --output data/benchmarks/my-test.json
uvicorn scarascope.api:app --reload
# Visit http://127.0.0.1:8000/engineering
```

The command prints JSON and creates a timestamped file inside `data/benchmarks/` by default. This directory is ignored by Git. Each run includes generated time, runtime version, dataset SHA-256, expected values, observed values, failures and limitations. In CI, JSON is attached as a downloadable workflow artifact (not committed results).

The Engineering Lab API is read-only and shares the application's API-key policy:

- `GET /api/engineering/benchmark` evaluates all key-free suites in memory.
- `GET /api/engineering/history` reads bounded local CLI-generated JSON summaries.
- `GET /api/engineering/runtime` shows live per-process counters (benchmarks do not increment these counters).

## What these scores **do not** prove

A 34/34 score says **all 34 tests on this fixed historical dataset passed**. It does not imply 100% accounting taxonomy coverage, audit the figures in a new SEC response, verify paragraph-level citations, or test the quality of financial research written by an LLM. The scores also do not establish production availability, inference latency, or cost. The same research corpus used for development is not a held-out real-world QA evaluation.

The new citation guard rejects missing/unknown evidence labels and **numeric claims not copied from the retrieved excerpts**. It cannot verify paraphrased qualitative statements, correctly derived calculations, or whether every claimed causal relationship follows from the cited text. Source metadata validation confirms canonical SEC domains/accession and period consistency, **not** the truth of the filing text. Both are safeguards, not an LLM factual-certification service.

## Future external evaluations

Next, assemble a human-reviewed, held-out set of questions with dated source passages and gold labels; calculate recall@k, answer relevance, citation attribution, unanswerable-question abstention, and factual precision separately. Evaluate against representative public SEC filings and actual Ollama/Groq calls. Record model versions, response times, provider errors, token use, runtime, sample size, budget and failure examples. Only report true measured data. Check evaluation dataset licensing before redistributing it.
