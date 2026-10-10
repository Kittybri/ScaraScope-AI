# Interview-ready, six-minute ScaraScope AI demo

**Purpose:** show reproducible engineering decisions, not the largest possible bot-command collection. This is a script; run it on a working machine beforehand and do not claim any result you cannot reproduce.

1. **0:00–0:40, problem and architecture.** Open the repository README. Financial AI can state the wrong fiscal year or invent supporting citations. This project separates SEC retrieval, Python arithmetic, optional inference, and verification into modules.
2. **0:40–1:40, offline financial demo.** Run `uvicorn scarascope.api:app --reload`, enter `DEMO`, and produce a research report. Clearly point out that these financial figures are **fictional**. Explain that live issuer lookup requires your own SEC contact User-Agent and functioning network.
3. **1:40–2:40, evidence-grounded question.** Use *Ask a filing* to compare the `lexical` and `bm25` options for a demo question. Show the evidence label and explain that citation formatting is not the same as semantic support. Test an impossible question and discuss abstention failures.
4. **2:40–4:10, Engineering Lab.** Visit `/engineering`, run the benchmark, show measured Recall@k/MRR and the visible misses. The held-out benchmark has 14 questions, **not** a large independent human-audited set, and reconstructed passages are not full filings. Show the JSON artifact's dataset hashes and source links.
5. **4:10–5:10, failures/privacy.** Run offline pytest reliability cases and explain simulated timeouts and `local_only` behavior. These use test doubles and are not proof of live cloud uptime. Do not demonstrate unconfigured Groq/Ollama performance as real measurements.
6. **5:10–6:00, tradeoffs and next experiment.** Show how BM25 improves the small reference ranking task but does not fix all unanswerable questions. The next controlled experiment is a genuinely independent, full-filing SEC corpus with factual QA annotations and model-level verification.

Before each demo: `python -m pytest -q`; `python -m scarascope.evaluation.runner --fail-on-regression`; confirm GitHub Actions is passing. Never publish API keys or personal credentials in screenshots.

## v0.8 interview extension: show review integrity, not invented accuracy

After showing the existing fixture benchmark, open `/engineering`, locate the **Real-filing evaluation readiness** area and enable **Require independent second review**. If local reviewed SEC data is absent, the system reports `not_evaluated` rather than promoting the reconstructed-table score to real SEC/LLM accuracy. Explain that the audit CLI lists unreviewed questions and missing reviewer rationales, while a pinned-baseline comparison refuses changed source hashes, question sets or denominators. See [REVIEW_PROTOCOL.md](REVIEW_PROTOCOL.md).

For a strong live example once you have reviewed source data, run a real-corpus strict benchmark, save its JSON, and reproduce the baseline comparison. Be prepared to show question-level misses and clarify that exact-passage retrieval is not equivalent to verifying arbitrary AI-written prose. Never claim independent review was performed unless it actually was.
