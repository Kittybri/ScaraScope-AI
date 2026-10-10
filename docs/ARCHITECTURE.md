# ScaraScope AI architecture guide

## Why this layout exists

ScaraScope uses **separate packages for separate responsibilities**. Scaramouche and Wanderer
were experiments with expanding single-file bot entry points. Here, application logic is
independent of Discord, HTTP, or any individual LLM vendor.

## Allowed dependency flow

```text
Web browser ──> api/routes.py ───┐
                                 ├──> services/research.py
Discord ────> REST /api/research─┘           |
                                        ┌───┼─────────┐
                                        v   v         v
                                   data/sec finance  ai/router -> ai/providers
                                        |   |         |
                                        └───┼─────────┘
                                            v
                                         core/models

storage/history.py is called by the API layer to persist metadata only.

New workflows have separate entry points: `api/advanced.py` (agent, compare, DCF,
benchmark), `api/exports.py` (PDF/Excel), and `api/watchlist.py`. They delegate
to `services/`, `finance/`, `reports/` and `storage/` rather than importing each other.
```

- **api/** only manages HTTP, authentication, and serialization. Keep business rules out of routes.
- **adapters/discord/** is a client of the HTTP API. Never import `discord` from `services/`, `finance/`, `ai/`, or `data/`.
- **services/** owns complete use cases and coordinates dependencies. It does not depend on FastAPI or Discord.
- **finance/** contains deterministic calculations and test fixtures, not LLM mathematics.
- **data/sec/** separates HTTP transport (`client.py`) from pure XBRL extraction (`extraction.py`).
- **ai/providers/** isolates Groq/Ollama details. `ai/router.py` decides selection and respects `local_only` privacy.
- **core/** contains contracts and settings, not HTTP handlers or data lookups.
- **storage/** manages persistence details; never store API tokens or private prompts in the metadata history.

## Where new features go

| Add this | Put it here | Test it with |
| --- | --- | --- |
| Financial ratio | `finance/calculations.py` (split into a new module when warranted) | `tests/test_finance.py` |
| Another SEC financial metric | `data/sec/extraction.py` and `core/models.py` | SEC fixture tests |
| A different financial-data API | `data/<provider>/client.py` | mocked HTTP integration tests |
| An LLM provider | `ai/providers/<vendor>.py`, wire it into `ai/router.py` | provider and privacy tests |
| A new research operation | `services/<use_case>.py` | service tests using fake providers |
| A new API endpoint | `api/routes.py`, split by resource as endpoints expand | `tests/test_api.py` |
| Discord commands | `adapters/discord/bot.py` | adapter tests, no finance logic inside |
| Report export | `reports/pdf.py` or `reports/excel.py` plus `api/exports.py` | output / source-validation tests |
| Agent step / verifier | `ai/agents/` and `services/agent.py` | agent + verification tests |
| Research evaluation | `evaluation/` and `tests/` | reproducible golden fixtures |
| SEC narrative tool | `data/sec/filings.py` | no-network HTML fixture tests |
| Watchlist / manual filing checks | `storage/watchlist.py`, `services/monitor.py` | injected SEC monitor tests |

## Development discipline

1. Keep entry points thin; never put tool logic into `app.py` or the Discord launcher.
2. Favor one clear responsibility per module. When a module grows difficult to navigate,
   split by feature rather than simply adding a second giant file.
3. Make integrations replaceable. All providers use the same `LLMProvider.generate` contract.
4. Validate calculations independently of any LLM. Keep SEC URLs and period metadata.
5. Enforce `local_only` at the router even when providers fail. Never auto-export private inputs.
6. Inject dependencies into services where possible; test with stubs before using real APIs.
7. Run `python -m pytest -q` and `python -m compileall -q scarascope` before merging.
8. Never commit secrets. `.env.example` documents keys but has no credentials.

## Stable launch entry points

- **Web API:** `uvicorn scarascope.api:app --reload`
- **Optional Discord:** `python -m scarascope.discord_bot`

The `scarascope/api/__init__.py` exports the ASGI application. The root
`scarascope/discord_bot.py` is intentionally a tiny compatibility shim.

## v0.3 SEC document retrieval and Q&A

```text
HTTP POST /api/documents/ask
    -> services/document_qa.py (bounded research use case + privacy gate)
       -> data/sec/client.py (ticker -> CIK; official SEC directory)
       -> data/sec/filings.py (10-K/10-Q retrieval + section extraction)
       -> ai/retrieval/lexical.py (bounded passages, offset, lexical ranking)
       -> ai/router.py (optional Groq/Ollama synthesis; local-only enforced)
    -> typed result with E1/E2 evidence labels, section locator, filing URL
```

Keep individual SEC parsers, retrieval strategies, generation prompts, service
orchestration and HTTP routes in distinct modules. The base financial data
pipeline should not import the document Q&A layer. Frontend code belongs in
`static/documents.js`, never in SEC or LLM modules.

**Trust boundary:** Filing text is untrusted data. Cited labels are mechanically
checked against retrieved passages, but this does not prove that an LLM's
interpretation is correct. No SEC paragraph deep link is asserted: offsets refer
to normalized extracted section text and the link opens the overall filing.
A `local_only` request never permits cloud fallback. Network and LLM calls are
optional for `DEMO`, which uses visibly fictional evidence.

**Known limitations:** Filings differ widely in markup and section naming;
10-Q Item 2 and 10-K Items 1A/7 are extracted only when reliably identifiable.
SEC HTML retrieval is limited to 5 MB and indexed sections are bounded;
this is *not* general PDF parsing, embeddings, a vector database, or exhaustive
multi-filing retrieval. The 10-Q reader uses the most recent 10-Q, which may not
contain a new risk-factor disclosure. Lexical retrieval can miss synonyms.
