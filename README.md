# ScaraScope AI

**A source-grounded financial research assistant and hybrid LLM engineering portfolio project.** Built independently (not connected with my personal projects Scaramouche and Wanderer), with a headless Python/FastAPI backend, browser dashboard, optional Discord client, and pluggable Ollama/Groq inference.

> **Status:** v0.4 modular prototype, not a trading platform or investment adviser. Oracle hosting and Groq credentials are **not configured** in the repository. The no-key demo uses **fictional** financial information. Live financial results use the SEC's XBRL Company Facts data, not an exhaustively indexed filing corpus.


## New in v0.4: Engineering Lab and auditable offline benchmarks

- **Engineering Lab at `/engineering`** (once running locally at `http://127.0.0.1:8000/engineering`): a separate, responsive engineering dashboard, backed by actual on-demand test outcomes rather than invented statistics.
- **34 historical SEC-source-linked financial benchmark cases**, using fixed figures from Apple's FY2023 and Microsoft's FY2024 10-K filings; expected answers are recorded in a versioned dataset and compared to Python calculations. **Not** a live SEC XBRL extraction or LLM reasoning benchmark.
- **6 arithmetic / 5 synthetic lexical retrieval / 6 simulated provider reliability cases** with independent denominators and explicit limitations.
- **New `verification/` package** for structured financial claims, reporting-period alignment, SEC source metadata and document citation-label/numeric-claim checks. These do **not** establish unrestricted LLM semantic accuracy.
- **Reproducible JSON reports** and a CLI runner, local report history, GitHub Actions benchmark artifacts, and tests of intentional erroneous values, citations, source URLs, dates and privacy failures.
- **Provider evaluation isolation:** fake benchmark outages do not inflate the application’s real inference counters.

Try it without API keys:

```bash
python -m scarascope.evaluation.runner --fail-on-regression
uvicorn scarascope.api:app --reload
# Then visit http://127.0.0.1:8000/engineering
```

Read the [Benchmarks and Evidence Guide](docs/BENCHMARKS.md) and [Engineering Case Study](docs/ENGINEERING_CASE_STUDY.md). Scores from fixed fixtures are never presented as real-world AI answering accuracy.


## New in v0.2: modular financial research toolkit

- **Research agent:** explicit bounded research plan and step trace, mathematical/source metadata verification, and optional best-effort 10-K Item 1A / 7 evidence snippets. No arbitrary model tool execution.
- **Company comparison:** side-by-side latest annual SEC financial metrics, with warnings for fiscal-period mismatches.
- **DCF scenario analysis:** user-supplied unlevered free cash flow, discount/terminal growth assumptions and a 5 × 5 sensitivity grid. **Not a stock price target.**
- **PDF and XLSX reports:** generated on demand, including SEC source links, caveats, and spreadsheet formulas.
- **Evaluation:** keyless, reproducible six-case arithmetic suite; separate unit/integration regression tests.
- **Operational features:** per-process SEC pacing/caching, privacy-aware LLM statistics, Ollama reachability diagnostics, API throttling and optional strict-auth setting.
- **Manual watchlist:** saved ticker metadata and on-demand latest filing change checks; no scheduled notifications yet.

Read [Feature Inventory](docs/FEATURES.md), [Security Notes](docs/SECURITY.md), [Evaluation Guide](docs/EVALUATION.md) and [Architecture](docs/ARCHITECTURE.md).

**Quickest demo:** Run the app, type `DEMO`, click **Run research agent**, then **Download PDF** or **Download Excel**. DCF, evaluation and watchlist controls are in the Research Toolkit below the original financial-analysis panel.

## What works today

| Capability | Status |
| --- | --- |
| Responsive browser dashboard | Implemented |
| Best-effort cited SEC document Q&A (10-K and 10-Q) | Implemented with lexical passages, optional Groq/Ollama synthesis, evidence-label checks and an offline fictional DEMO; **not** paragraph-anchored/semantically verified |
| Offline DEMO (clearly fictional; no API keys) | Implemented |
| Lookup by US-listed ticker and ingest SEC annual XBRL facts | Implemented; requires valid SEC contact User-Agent and network |
| Revenue, operating income, net income, assets, liabilities, equity | Extracted where tagged in US GAAP; missing values shown explicitly |
| YoY revenue growth, operating margin, net margin | Deterministic Python calculations |
| SEC filing accession/source links | Implemented (filing-level provenance, **not paragraph-level** citations) |
| Local Ollama / Groq cloud provider adapters | Implemented; require respective configurations |
| Rule-based task-complexity routing and provider fallback | Implemented |
| `local_only` privacy mode (never fallback to cloud) | Implemented and tested |
| Local SQLite research history | Metadata only; no prompt or report content stored |
| Optional Discord `!scope` command | Implemented as API client |
| Automated pytest suite, GitHub Actions, Docker | Included |
| Bounded research agent and verification trace | Implemented (rule-driven, not autonomous tool generation) |
| Company comparison and illustrative DCF | Implemented |
| PDF/Excel downloads, watchlist, evaluation tools | Implemented |
| Best-effort Item 1A / Item 7 filing sections | Implemented; dependent on source format |

**Not yet implemented:** robust full-text document RAG/embeddings, paragraph-level citations, XBRL calculation linkbase reconciliation, precision-grade financial validation across every accounting taxonomy, streaming responses, user accounts, multi-tenant isolation, cross-worker rate limiting and production cloud deployment. Financial summaries should be reviewed against their sources.

## Quick start (no secrets required)

```bash
# Python 3.11+; inside a clone of this repository
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -e '.[test]'
cp .env.example .env            # Windows: copy .env.example .env
uvicorn scarascope.api:app --reload --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. Use ticker **DEMO** and click **Run financial analysis**. The UI, numbers, chart, and explanation work entirely offline using explicitly **fictional** data.

Interactive API docs: <http://127.0.0.1:8000/docs>. `GET /api/demo` never requires configuration.

### Enable real SEC financial data

1. Edit `.env` and replace the placeholder `SEC_USER_AGENT` with **your real application name and contact email**. The SEC uses this to identify automated traffic.
2. Restart the API and enter a US-listed ticker such as `MSFT` or `AAPL`.
3. The application queries the SEC ticker directory and [Company Facts endpoint](https://www.sec.gov/search-filings/edgar-application-programming-interfaces). The response is public information, no SEC API key needed.
4. Respect SEC fair-access guidance. This prototype is intended for low-volume research, not mass scraping.

Data selection is intentionally conservative: annual `10-K` USD US-GAAP facts anchored to the revenue reporting-period end, with 300–380 day periods for flow metrics. It cannot normalize every accounting edge case; companies with differing tags or non-US-GAAP filings may be unsupported.

### Enable Groq (optional)

Add to `.env`:

```dotenv
GROQ_API_KEY=put-your-own-key-here
GROQ_MODEL=openai/gpt-oss-20b
```

Use a separate project key when available. Verify the model is currently offered on your Groq plan; provider catalogs change. Groq receives the research question and selected public financial facts for **cloud-eligible** requests. Avoid placing private documents in a request you authorize for cloud processing.

### Enable Ollama (optional)

On your laptop, install [Ollama](https://ollama.com/) and fetch a model, e.g. `ollama pull llama3.2:3b`. Ensure local generation works first. Then in `.env`:

```dotenv
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:3b
LOCAL_TIMEOUT_SECONDS=25
```

When the FastAPI service is later hosted on Oracle Cloud, `127.0.0.1` will be the **Oracle VM**, not your laptop. Set up an authenticated private network (such as Tailscale) and restrict Ollama's listener so that **only your backend** can reach it. Never publicly expose port `11434` or your home router to serve Ollama. Timeouts are configurable for your laptop's real inference speed.

### Routing behavior

- `provider=auto`: routine questions → Ollama first; complex/multi-year analytical requests → Groq first.
- If the preferred provider is off, unconfigured, or fails, the other provider is attempted **only if cloud transfer is allowed**.
- `privacy=local_only`: Ollama only, **never Groq**, even if Ollama goes offline.
- No configured/working provider: deterministic, explicitly labeled non-LLM summary. The numerical data pipeline still works.
- `provider=none`: use rule-based explanation explicitly.
- `DEMO`: always use fictional numbers and a deterministic explanation to prevent mistaken attribution to real companies.

This is a rule-based complexity heuristic for the portfolio MVP, **not** a trained classifier. A failed model response does not automatically imply that its financial claims were correct or verified. Provider-wide outages and quota limits can still affect AI explanations.

## API examples

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/demo

# No SEC credentials required when ticker=DEMO:
curl -X POST http://127.0.0.1:8000/api/research \
  -H 'Content-Type: application/json' \
  -d '{"ticker":"DEMO","years":3,"provider":"auto","privacy":"cloud_ok"}'

# Once SEC_USER_AGENT is configured, replace DEMO with MSFT:
# curl -X POST ... -d '{"ticker":"MSFT","years":3}'
```

To protect research and history requests with a token, set `SCARASCOPE_API_KEY` in `.env`, restart, and pass an `X-API-Key` header (or enter the key in the browser's API-key field). **Configure this before any publicly accessible deployment.** API tokens are never part of committed source code.

## Ask a filing (v0.3 document intelligence)

The dashboard includes an **Ask a filing** panel. It runs independently of the
financial-statement analysis and can search extracted sections of the most
recent SEC **10-K** or **10-Q** using lexical retrieval. Use `DEMO` to explore
fictional filing passages with **no external calls or API keys**.

```bash
# Works offline with fictional evidence and deterministic citations
curl -X POST http://127.0.0.1:8000/api/documents/ask \
  -H 'Content-Type: application/json' \
  -d '{"ticker":"DEMO","question":"What cybersecurity risks are described?","form":"10-K","provider":"none"}'

# After configuring SEC_USER_AGENT, query live SEC 10-K passages:
# curl -X POST http://127.0.0.1:8000/api/documents/ask \
#   -H 'Content-Type: application/json' \
#   -d '{"ticker":"MSFT","question":"What cybersecurity risks are described?","form":"10-K"}'
```

The result has `answer`, `status`, `provider`, `evidence` (E1/E2 source labels,
SEC accession, URL, section title and normalized text offset), and limitations.
If no passage matches, it abstains instead of inventing a filing statement.
If an LLM supplies unknown or missing reference labels, the answer is replaced
with source excerpts. **Reference checks reject unknown labels and explicit numeric claims missing from the evidence, but do not establish the semantic accuracy of
LLM-written prose.** SEC URLs open the filing, not guaranteed precise paragraph
anchors. Section extraction can fail for unusual SEC HTML, and lexical matching
can miss synonyms. Large or PDF-only filings may remain unsupported.

`GET /api/evaluation/retrieval` runs five synthetic keyword-retrieval and
abstention regression cases. It is **not** a live financial QA accuracy score.
See `docs/EVALUATION.md` for the scope of the tests.

## Optional Discord interface

This thin client calls the same FastAPI backend; the financial engine does not depend on Discord.

```bash
pip install -e '.[discord]'
# Set DISCORD_BOT_TOKEN in .env; enable Message Content Intent in Discord developer portal.
python -m scarascope.discord_bot
```

Commands: `!scope DEMO`, `!scope MSFT`, and `!scopehelp`. Run FastAPI separately first. For a separate deployment, set `SCARASCOPE_API_URL` to its authenticated, private URL.

## Architecture and project structure

**Strictly modular:** financial math, network ingestion, AI, report generation, agent planning, persistence and interfaces live in separate packages. There is no giant bot file.

```text
scarascope/
  api/                 app.py, routes.py, advanced.py, exports.py, watchlist.py, dependencies.py
  ai/                  router.py, prompts.py, availability.py
    providers/          groq.py, ollama.py, base.py
    agents/             planner.py, verification.py
  core/                config.py, models.py
  data/sec/            client.py, extraction.py, filings.py, fair_access.py
  finance/             calculations.py, comparisons.py, valuation.py, demo.py
  services/            research.py, agent.py, comparison.py, monitor.py
  reports/             pdf.py, excel.py
  evaluation/          benchmark.py, golden.py
  security/            rate_limits.py
  observability/       metrics.py
  storage/             history.py, watchlist.py
  adapters/discord/    bot.py
  static/              Browser UI scripts, styles and HTML
tests/                   Independent pytest modules and mock SEC fixtures
docs/                    Architecture, features, evaluation and security notes
```

**Dependency direction:** API/Discord adapt requests; `services/` coordinates domain and providers; `finance/` does math; `data/sec/` owns EDGAR integration; `ai/providers/` owns inference. See [Architecture Guide](docs/ARCHITECTURE.md).

**Existing commands remain valid:** `uvicorn scarascope.api:app --reload` and `python -m scarascope.discord_bot`.

## Testing

```bash
pip install -e '.[test]'
python -m pytest -q
python -m compileall -q scarascope
```

Tests simulate provider failures and offline Ollama, verify privacy boundaries, check SEC period matching, and exercise keyless demo endpoints. They do **not** require paid APIs, live SEC access, or a running Ollama server.

## Deployment and security notes

- Docker: `docker compose up --build`. The Compose port binds to `127.0.0.1` only. Put an authenticated HTTPS reverse proxy in front when deploying publicly.
- Set `SCARASCOPE_API_KEY` and `SCARASCOPE_REQUIRE_AUTH=true` before public deployment. `SCARASCOPE_REQUESTS_PER_MINUTE=60` tunes the current in-process throttle.
- **Do not assume an open Oracle VM is safe**. Configure HTTPS, firewall/security groups, credentials, and request-level rate limiting before exposing it. CORS is intentionally not broadly enabled.
- SQLite stores only ticker, data type, inference provider, and timestamp. It does not implement per-user isolation; do not expose the history endpoint in a multi-user setup without adding identities and access controls.
- The application is **informational**; it does not automate trades or provide tailored investment advice. Legal/compliance review would be required before operating a paid adviser-like product.
- The SEC pipeline uses public filing *facts* and a **best-effort**, separately retrieved 10-K Item 1A/7 section reader. It does not claim verified paragraph-level RAG, stock prices or private filing access.

## Next milestones

1. Verify live 10-K extraction across a diverse SEC corpus; add robust full-text RAG, paragraph anchors and explicit claim-evidence checking.
2. Benchmark Ollama on the actual laptop; build the authenticated Oracle-to-laptop private connection when Oracle hosting is ready.
3. Run genuine financial QA benchmark cases and measure answer quality, token consumption and latency by provider.
4. Add persistent background filing checks and opt-in alerts if a real schedule becomes useful.
5. Harden multi-user security, centralized quotas, configuration management, deployment and operational monitoring before any public launch.

**License:** No license has been granted. All rights reserved unless the repository owner chooses an explicit license.
