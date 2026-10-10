# Security, privacy and operational limits

## Trust boundaries

- Treat all public filings, uploaded text (if later supported), model outputs, and user prompts as untrusted data. This prototype never executes model-created code or arbitrary web requests. The research plan is a fixed allowlist of supported operations.
- Requests for SEC documents construct host/path from an official, validated SEC CIK/accession/document identifier. There is no arbitrary URL-fetch endpoint.
- SEC requests are paced conservatively in each Python process and cached briefly. Multiple replicas/workers need a coordinated rate limiter to protect SEC fair-access limits.
- `privacy=local_only` prevents Groq inference and returns a deterministic explanation if the local provider is down. A private request must not silently be sent to a cloud model.
- The Groq cloud option transmits the prompt and included public SEC numbers to a third party. Do not send confidential client records without appropriate permissions and contractual controls.
- Server logs and operational counters omit full prompts, reports, tokens, and provider credentials. Metadata-only research history and watchlist entries live in local SQLite.
- Web output is rendered with `textContent`; exports escape PDF markup and prevent spreadsheet formula injection in free-text excerpts.

## Required before public deployment

1. Set `SCARASCOPE_API_KEY` and `SCARASCOPE_REQUIRE_AUTH=true`. Otherwise the prototype runs without required authentication, intended only for local use.
2. Put the service behind HTTPS with request size limits, a hardened reverse proxy and appropriate network firewall rules. Compose binds only to loopback by default.
3. Replace per-process rate limits with shared gateway limits and ensure quotas cover SEC, Groq, Ollama and report generation.
4. Add a real user identity/authorization model and row-level separation before multi-user use; the current API key is **one shared token** and SQLite watchlist/history is **not isolated by user**.
5. Encrypt backups, define data-retention policies, assess provider terms and privacy posture, and add operational incident monitoring.
6. Use Tailscale or equivalent *authenticated* private connectivity for remote Ollama, never publicly expose port 11434.
7. Run real-user security reviews and regulatory/legal reviews before commercial deployment. Educational disclaimers do not constitute regulatory approval.

## Reliability

- The non-LLM financial math remains available when both Ollama and Groq are down.
- A failure of optional SEC filing-text retrieval does not discard structured financial results.
- Provider diagnostics check reachability, not semantic quality or prompt completion.
- Prompts cannot trigger arbitrary external actions; proposed trading and account access integrations require separate reviews.
