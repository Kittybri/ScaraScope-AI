# Portfolio quality roadmap

This is a transparent engineering backlog; checked items identify code that
exists, not universal production readiness. The evidence for completed items is
the test suite, GitHub Actions runs, and documented limitations.

## Started/completed in v0.6

- [x] Opt-in **local** semantic embeddings and BM25+semantic rank fusion.
- [x] Reuse the existing question-held-out A/B harness for optional embedding methods.
- [x] Per-answer source-hash and timing manifest for document Q&A.
- [x] Suspicious filing-instruction screening and targeted adversarial tests.
- [x] Dependency audit + CycloneDX SBOM workflow.
- [x] Bounded loopback-only API latency probe.
- [x] Threat model, architecture decision record, and operational runbook.

## Implemented in v0.7 (operator-run, **not** production-validated)

- [x] Real SEC 10-K / 10-Q section snapshot ingestion with SEC fair-access pacing, verified SEC URL/CIK/accession association, section-text hashes, and size caps.
- [x] Reviewer-gated JSONL annotations with explicit issuer-held-out partitions; no unreviewed question may produce a real-corpus accuracy score.
- [x] Real-corpus lexical/BM25 and opt-in semantic/hybrid retrieval evaluation, exact passage ID auditing, dataset hashes, failure reports, and Engineering Lab corpus-readiness panel.
- [x] Bounded opt-in **live** Ollama/Groq smoke-test tool, without fabricated cost/accuracy metrics; not yet run on owner hardware.
- [x] Corpus CLI smoke tests, security regression cases and architectural decision record.

## Started/completed in v0.8

- [x] Optional independent-second-review gating (reviewer identity is self-attested).
- [x] Reviewer completeness audit with explicit missing rationale and second-review gaps.
- [x] Reject incomparable corpus benchmark baselines and fail on verified retrieval regressions.
- [x] Show real-corpus retrieval metrics separately in the Engineering Lab, with no synthetic fill-in.
- [x] Additional explicitly-unit-bearing numerical claim checks for `$` and `%` in cited evidence.
- [x] Expanded offline validation and adversarial benchmark regression tests.

## Evidence still needed before making hiring claims

- [ ] Real SEC full-filing corpus with multiple independent human-reviewed
      answer/evidence labels and issuer-held-out evaluation.
- [ ] Human review of gold references, source-date/period matching and annotation disagreements.
- [ ] Install a licensed local embedding model, run actual semantic/hybrid
      comparisons, and tune only on development data.
- [ ] Evaluate free-form Groq/Ollama answer correctness, supported claims,
      abstention, latency, tokens and actual provider cost.
- [ ] Broader prompt-injection and data-exfiltration tests plus network egress
      controls and complete request/workflow tracing.
- [ ] Test SEC retrieval under actual live 10-K and 10-Q formats/edge cases.
- [ ] Secure Oracle deployment, role isolation, HTTPS and operational monitoring.
- [ ] Capture *actual* UI screenshots, create a reproducible demo video,
      tag a stable release and publish release evidence.

**Avoid:** unsourced perfect accuracy claims, fake uptime numbers, silently
falling back to cloud from `local_only`, and making more chat commands at the
expense of correctness and auditability.

## Implemented in v0.9 (local/prototype scope only)

- [x] HTTP request IDs and bounded process-local route/status/latency traces;
      the document-Q&A provenance run ID matches the HTTP response header.
- [x] Engineering Lab trace panel shows real local request p50/p95 and errors,
      explicitly without live provider or cloud-performance claims.
- [x] Structured generated-answer audit distinguishes rejected citation/unit/
      period mistakes, exact extractive fallback, and syntactically acceptable
      claims that **still require semantic human verification**.
- [x] Additional indirect prompt-injection patterns, Unicode normalization,
      API declared-size limit, no-store API headers and adversarial regression tests.
- [x] Documented detection scope, tracing retention and missing public-deployment protections.

**Remaining security gaps:** this in-app Content-Length gate is not a streaming
body-size limiter. Public hosting needs a hardened reverse proxy with streaming
limits, network egress allowlisting, private authentication, cross-worker quotas,
and a reviewed incident/retention policy. These were not simulated as complete.

## Implemented in v0.10: deterministic historical source selection

- [x] Optional exact 10-K/10-Q accession selection in the document Q&A panel
      and operator-run SEC corpus ingestion.
- [x] Cross-check accession, CIK, form, SEC-listed primary document, and
      historical archive index metadata **before** requesting a filing.
- [x] Reject an absent accession rather than silently substituting the latest
      document; bound historic-index requests and stream-limit filing size.
- [x] Mocked SEC historic-index, malicious filename, mismatched form,
      oversized HTML and pinned-snapshot regression cases.
- [x] Published SEC historical source identifiers and reproduction commands.

**Still not completed:** live SEC downloads, reproducible source-backed
independently reviewed financial QA labels, live model comparisons, secure
Oracle deployment, and authentic application screenshots.

## Implemented in v0.11: repeatable real-filing evidence intake (review not yet completed)

- [x] Versioned, metadata-validated four-issuer SEC accession intake plan and
      16 provisional questions with issuer-disjoint development/held-out groups.
- [x] All-or-fail accession identity preflight before storing immutable,
      source-hashed SEC section snapshots.
- [x] Bounded blind HTML source review packet with escaped text, exact local
      evidence IDs and original SEC filing links; no gold labels or reviewer notes.
- [x] Manually triggered GitHub Actions evidence collection workflow requiring
      an operator-owned SEC contact secret, with short-retention artifact upload.
- [x] Offline plan validation in ordinary CI and adversarial source/review tests.

**Still pending:** successful live execution of that manual intake workflow,
actual filing/section quality inspection, *independent human* gold review,
held-out retrieval measurements, real LLM quality/latency comparisons and secure
Oracle deployment. No offline test automatically certifies those conditions.
