# ScaraScope AI: threat model and controls (v0.6)

**Scope:** single-operator research prototype; not a production security
attestation. Public SEC documents, text returned from external services and
AI-generated replies must always be treated as untrusted input.

| Asset / trust boundary | Threat | Current mitigation | Still missing |
| --- | --- | --- | --- |
| User request → FastAPI | API abuse, invalid parameters | Pydantic bounds, optional API key, in-process rate limit | Authenticated accounts, per-user quotas, gateway controls |
| SEC filing → retrieval/LLM | Prompt injection within retrieved material | Source treated as data; suspicious instruction patterns skip LLM synthesis; tool URLs are not supplied by LLM | Independent red-team testing, deeper contextual injection resistance |
| SEC source → answers | Fabricated financial facts | Deterministic math, citation-label and explicit-number checks, evidence fingerprints | General semantic entailment, derived-value reconciliation |
| Privacy setting → provider router | Private prompt leaking to cloud | `local_only` permits only local LLM even under fallback | Network-layer egress policy and live integration verification |
| Embedding retrieval → local model | Silent cloud inference / remote model execution | Explicit local directory, `local_files_only=True`, no remote custom code trusted | Model supply-chain verification and runtime sandbox |
| User text → browser/PDF/Excel | Script or formula injection | UI uses `textContent`, export protections in existing modules | Browser CSP and comprehensive file fuzzing |
| HTTP client → SEC endpoints | Server-side request forgery | Allowlisted constructed SEC URLs and bounded identifiers | Wider parser and redirect/hostname fuzzing |
| Repository → deployed binary | Vulnerable dependencies | CodeQL, new Python dependency audit, SBOM artifact | Lockfiles with hashes, signed builds/attestations |
| Research output → history | Sensitive prompt retention | Existing metadata-only history, per-response traces contain no questions or full snippets | Centralized access controls, retention and deletion policies |

## Specific v0.6 mitigations and tests

- **Retrieval injection screening** rejects common instruction-shaped content
  from optional model synthesis. It is a heuristic, not a general prompt-injection
  solution. The flagged excerpt remains visible as source evidence.
- **Semantic retrieval is opt-in and local-only.** A missing local model causes
  an explicit configuration error, not an automatic download or cloud call.
- **Response provenance** records UUID-style run IDs, source passage SHA-256
  fingerprints, SEC accession, retrieval method, selected inference model and
  timings, without persisting prompts, API keys or full excerpts.
- **Automated tests** cover malformed embeddings, adversarial passages, invalid
  routes, local-only policy, load-probe target restrictions, and metadata omission.
- **Supply-chain workflow** audits the installed CI environment and creates a
  CycloneDX SBOM; its output is inspectable and security advisories can change.

## Known unresolved risks

Prompt-injection detection can be bypassed, citation validity is not semantic
truth, untrusted PDF/Excel exports need further fuzzing, and API-key protection
is not user-scoped authorization. The local embedding model remains a third-party
supply-chain input. `local_only` is an application policy, **not** a validated
outbound firewall. Do not expose the prototype publicly until HTTPS, hardening,
identity/isolation and resource controls have been reviewed.

Security checklist: run `python -m pytest -q`, inspect **CodeQL** and
**Dependency Audit and SBOM** workflow outcomes, and review source dependencies
before any release.

## v0.9 scope updates

- Prompt-injection screening normalizes Unicode NFKC and strips format marks
  before applying additional role-delimiter/disregard-instructions patterns.
  Obfuscated or indirect instructions can still bypass this heuristic.
- The document-Q&A generated-answer audit rejects clearly missing evidence
  labels, incorrect cited numerical values or units, unsupported explicit
  fiscal-year references, and substantive sentences with no citations. It
  **does not** prove qualitative entailment, causality or finance correctness.
- Normal API responses include a random request ID, no-store/nosniff headers;
  metadata-only traces are bounded, process-local, unaudited and not durable.
- Oversized *declared* request bodies are rejected early. Chunked transfer,
  unknown Content-Length, resource-intensive model calls, distributed quotas,
  and network egress restrictions require independent gateway/platform controls.
- Review `docs/OPERATIONS.md` for exactly which diagnostics may be shown and
  what information is intentionally omitted.
