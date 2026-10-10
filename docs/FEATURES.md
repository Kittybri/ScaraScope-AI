# ScaraScope AI: feature inventory (v0.2)

ScaraScope is a **portfolio research prototype**, not a validated financial adviser,
a commercial market-data feed, or a production-ready multi-tenant service.

## Available locally without keys

| Feature | UI | Endpoint | Notes |
|---|---|---|---|
| Synthetic financial report | Main dashboard | `GET /api/demo`, `POST /api/research` with `DEMO` | Clearly fictional numbers |
| Bounded research-agent plan | Research toolkit | `POST /api/agent/research` | Explicit fixed tools and trace, not unrestricted autonomous LLM tool execution |
| Financial verifier | Agent response | Part of `POST /api/agent/research` | Checks ratios and metadata; **not** an AI factuality certificate |
| DCF scenario and 5x5 sensitivity | Research toolkit | `POST /api/valuation/dcf` | Requires **user-supplied** unlevered FCF and assumptions |
| Research reports | Research toolkit | `POST /api/reports/research.pdf` or `...xlsx` | Excel contains readable formulas and source sheets |
| Arithmetic benchmark | Research toolkit | `GET /api/evaluation/deterministic` | 6 fixed golden tests, not FinanceBench or LLM reasoning scores |
| Manual watchlist | Research toolkit | `/api/watchlist` | SQLite state, no background alerts |
| In-process telemetry | API only | `GET /api/diagnostics` | Operational metadata only, no prompts/keys |

## Live-data features (require SEC contact User-Agent and internet)

- Company Facts annual metrics and filing-level source references.
- Two-company **latest annual period** side-by-side comparison. Differences are arithmetic, not risk-adjusted rankings. Reporting dates and accounting policies may differ.
- Item 1A and Item 7 **best-effort** 10-K HTML extraction with small keyword-matched excerpts and section-level locators. Many filings cannot be parsed with this simple method; no evidence means no risk-factor claims.
- Explicit on-demand watchlist check for the most recently published 10-K, 10-Q or 8-K. The first check establishes a baseline; later checks detect an accession change. **No scheduler, alerts, email or continuous monitoring.** Checks process up to ten tickers per run.

## Optional AI capabilities

- Groq API adapter and local Ollama adapter, each configured with `.env` variables.
- Rule-based routing and provider fallback. If `privacy=local_only`, Groq is never used.
- Provider connectivity probe: `GET /api/providers/status` queries local Ollama metadata only, if enabled. Groq configuration status is reported without spending tokens.
- In-process fallback/success statistics. For budget accounting, concurrency handling, and model-quality evaluation, further work is required.

## Deliberately not claimed as complete

- Accurate paragraph-anchored citations for arbitrary PDF/HTML filings.
- Independent verification of all LLM-generated assertions.
- Comprehensive SEC accounting taxonomy coverage or XBRL reconciliation.
- Search of private or subscription-only financial research documents.
- Arbitrary-purpose autonomous agents, brokerage connectivity, trades or investment recommendations.
- Live market prices, share-count-based stock valuation, forecasting or investment signals.
- Scheduled research alerts, tenant-level privacy, user login, billing, or commercial readiness.
- Oracle Cloud deployment or a live, authenticated laptop tunnel.

## Hands-on demo

1. Start the API and use `DEMO` to run the baseline and the research agent.
2. Download the PDF and Excel. Inspect the actual Excel formulas rather than trusting a language model to calculate ratios.
3. Try a DCF with 100 million USD starting unlevered FCF, 3% growth, 10% discount rate and 2% terminal growth. Change discount rates to see sensitivity.
4. Use `/docs` for the deterministic evaluation endpoint. Review the case-by-case expected and observed values.
5. Configure SEC contact information for real company facts, then compare two public companies or run the best-effort filing-text reader.
6. Optionally configure Ollama and Groq. Use the router tests to demonstrate failover and the enforced local-only privacy boundary.
