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
