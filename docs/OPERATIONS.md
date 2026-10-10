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
