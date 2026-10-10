# Engineering operations and evidence (v0.6)

## Per-answer provenance (SEC document Q&A)

Responses from `/api/documents/ask` contain `provenance`, a short, unpersisted
manifest with a run ID, UTC time, retrieval strategy, privacy setting, SEC
accession, retrieved evidence IDs and excerpt SHA-256 hashes, model/provider
used, and approximate retrieval/generation/total timings. This lets a reviewer
recompute the excerpt hashes from evidence returned in the same response.

**Limitations:** A hash proves that the same bytes were observed, not that the
original SEC filing contained the passage, that the answer is true, or that the
pipeline is safe. Source chunk offsets refer to *extracted text*. Timing is
process-local, not distributed tracing; there is no token/cost measurement yet.
The manifest intentionally does not contain the question, the source text, any
API keys, a trace stored in a database, or a false claim that an LLM ran if it did
not. Not every ScaraScope endpoint is instrumented with these manifests yet.

## Small bounded latency experiment

Start the app locally (`uvicorn scarascope.api:app --reload`) and then run:

```bash
python -m scarascope.evaluation.load_probe --requests 30 --concurrency 3
```

The CLI accepts loopback HTTP with an explicit port only (localhost,
127.0.0.1, ::1). Up to 100 requests and 8 concurrent workers. Only read-only
`/api/demo` or `/api/health` may be tested. The output contains p50/p95/max
request latency, request count, throughput, and errors. **This is not a full
load test:** it does not exercise SEC, document parsing, embeddings, LLM tokens,
cloud costs, authentication at scale, or multi-worker behavior. Record hardware,
commit, Python version, and resource usage when presenting comparisons.

## CI evidence

- Python CI: pytest JUnit and offline benchmark JSON artifacts.
- CodeQL: Python static analysis, which does not prove absence of vulnerabilities.
- Dependency Audit and SBOM: an audit of installed CI dependencies plus a
  CycloneDX bill of materials. Review advisories before deployment.

The financial reference benchmark is a reconstructed-source test, not a
human-reviewed free-form financial QA dataset or an independent held-out issuer
corpus. Live Ollama/Groq comparisons cannot be asserted without model runs.

## v0.9: request tracing and claim audits

**New API request diagnostics:** `GET /api/engineering/traces` requires the
same API-key policy as other Engineering Lab endpoints. A request ID is returned
in `X-Request-ID` on normal API responses and reused by the SEC document Q&A
`provenance.run_id`. Only the last 100 route-template/status/duration events in
the current Python process are held in memory. `p50_ms` and `p95_ms` use
nearest-rank percentiles over **that bounded, mixed-route sample**. This is not
production observability, financial inference latency or durable history.

No query strings, raw paths, client IPs, request bodies, answer texts, SEC
excerpts or API credentials are stored in the HTTP trace queue. API responses
also include `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`.
On unhandled server exceptions, an internal 500 status is recorded, but an
`X-Request-ID` response header is not guaranteed if the HTTP server generates
the error response outside this middleware. Use a real edge proxy and a
structured logging/incident strategy before public deployment.

**Claim audits:** `POST /api/documents/ask` returns `claim_audit`. The status
`extractive` denotes safe source excerpts with no LLM validation claim;
`rejected` means a proposed model draft failed citation/numeric/unit/fiscal-year
checks and the **returned answer remains extractive**; and
`needs_semantic_review` means the draft passed those *syntactic* checks but
its qualitative meaning has **not been verified**. Audits cannot establish
that figures relate to the correct year/denominator just because both appear
somewhere in a cited passage. The UI labels this explicitly.

**API body bound:** requests with a declared `Content-Length` over 64 KiB are
rejected with 413. This is intentionally modest for JSON research requests,
but chunked bodies and streaming reverse proxies need independent maximum-body
limits. Do not treat this as DDoS protection or a substitute for nginx/Caddy.

To test locally:

```bash
python -m pytest -q tests/test_v09_tracing_claims.py
uvicorn scarascope.api:app --reload
# Open /engineering, run benchmark, inspect Sanitized request diagnostics
```
