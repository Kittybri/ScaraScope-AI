# ScaraScope AI

**A source-grounded financial research assistant and hybrid LLM engineering portfolio project.** Built independently (not connected with my personal projects Scaramouche and Wanderer), with a headless Python/FastAPI backend, browser dashboard, optional Discord client, and pluggable Ollama/Groq inference.

> **Status:** v0.1 prototype, not a trading platform or investment adviser. Oracle hosting and Groq credentials are **not configured** in the repository. The no-key demo uses **fictional** financial information. Live financial results use the SEC's XBRL Company Facts data, not a full-text filing RAG system.

## What works today

| Capability | Status |
| --- | --- |
| Responsive browser dashboard | Implemented |
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

**Not yet implemented:** full-text document ingestion and risk-factor extraction, embeddings/RAG, XBRL calculation linkbase reconciliation, precision-grade financial validation across every accounting taxonomy, streaming responses, user accounts, multi-tenant isolation, quota accounting, SEC-wide rate limiting/caching, and production cloud deployment. Financial summaries should be reviewed against their sources.

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

## Optional Discord interface

This thin client calls the same FastAPI backend; the financial engine does not depend on Discord.

```bash
pip install -e '.[discord]'
# Set DISCORD_BOT_TOKEN in .env; enable Message Content Intent in Discord developer portal.
python -m scarascope.discord_bot
```

Commands: `!scope DEMO`, `!scope MSFT`, and `!scopehelp`. Run FastAPI separately first. For a separate deployment, set `SCARASCOPE_API_URL` to its authenticated, private URL.

## Architecture and project structure

The app is deliberately organized **by responsibility**, not as a large `bot.py` file.
The financial engine is independent of the interface. Adding a Discord command, web page,
or future mobile client does not require changing financial calculations or model providers.

```text
scarascope/
  api/                      HTTP boundary: ASGI app, routes, auth dependencies
    __init__.py             Public `scarascope.api:app` entry point
    app.py                  FastAPI application / static frontend mount
    routes.py               Health, demo, research and history endpoints
    dependencies.py         Settings injection and API key protection
  core/                     Cross-cutting types and configuration
    config.py               Environment settings and credentials
    models.py               Typed request, response, and financial contracts
  finance/                  Pure financial domain logic
    calculations.py         Deterministic calculations, summaries
    demo.py                 Explicitly fictional offline sample dataset
  data/sec/                 Public financial source integration
    client.py               SEC HTTP client and error handling
    extraction.py           Pure SEC XBRL data parsing and source references
    constants.py            SEC endpoint locations
  ai/                       LLM-specific components
    prompts.py              Financial research prompt assembly
    router.py               Provider selection, failover, privacy checks
    providers/
      base.py               Async provider interface / shared errors
      ollama.py             Local inference implementation
      groq.py               Cloud inference implementation
  services/
    research.py             Shared headless research workflow
  storage/
    history.py              SQLite research metadata, no prompt contents
  adapters/discord/
    bot.py                  Optional Discord client, calls REST API
  discord_bot.py            Tiny compatibility launcher (not bot logic)
  static/                   Browser UI assets
    index.html
    app.js
    styles.css
tests/                        Tests for each system boundary
.github/workflows/           Automated CI checks
Dockerfile, compose.yaml      Local Docker / future Oracle deploy
 docs/ARCHITECTURE.md         Design rules and extension examples
```

**Dependency direction:** API and Discord adapt external requests; `services/` coordinates
`finance/`, `data/`, `ai/`, and `storage/`. Pure calculation and SEC extraction modules
have no Discord or FastAPI dependency. Providers must not import routes or storage.
See [Architecture Guide](docs/ARCHITECTURE.md) for how to grow the project safely.

**Existing commands are unchanged:** `uvicorn scarascope.api:app --reload` and
`python -m scarascope.discord_bot` still work after the reorganization.

## Testing

```bash
pip install -e '.[test]'
python -m pytest -q
python -m compileall -q scarascope
```

Tests simulate provider failures and offline Ollama, verify privacy boundaries, check SEC period matching, and exercise keyless demo endpoints. They do **not** require paid APIs, live SEC access, or a running Ollama server.

## Deployment and security notes

- Docker: `docker compose up --build`. The Compose port binds to `127.0.0.1` only. Put an authenticated HTTPS reverse proxy in front when deploying publicly.
- **Do not assume an open Oracle VM is safe**. Configure HTTPS, firewall/security groups, credentials, and request-level rate limiting before exposing it. CORS is intentionally not broadly enabled.
- SQLite stores only ticker, data type, inference provider, and timestamp. It does not implement per-user isolation; do not expose the history endpoint in a multi-user setup without adding identities and access controls.
- The application is **informational**; it does not automate trades or provide tailored investment advice. Legal/compliance review would be required before operating a paid adviser-like product.
- The first SEC version uses live, public filing *facts*. It does **not** claim to review risk-factor paragraphs, valuation assumptions, stock prices, or private filings.

## Next milestones

1. Verify real SEC extraction across 10-K examples and improve financial-taxonomy handling.
2. Add document ingestion, section-level source citations, and stronger evaluation fixtures.
3. Benchmark Ollama on actual laptop hardware and establish secured Oracle ↔ laptop connectivity.
4. Add provider health/circuit breaker, quota-aware throttling, measured latency/cost telemetry, and safe auth for multiple users.
5. Add automated PDF report export, saved comparisons, and monitored cloud deployment.

**License:** No license has been granted. All rights reserved unless the repository owner chooses an explicit license.
