# Bounded live inference latency probe (v0.7)

The live provider probe is built but **has not been executed against the owner's Ollama or Groq accounts**. It requires deliberate opt-in and is not part of automated CI.

```bash
# First run Ollama on your laptop and configure OLLAMA_ENABLED=true and OLLAMA_MODEL in local .env.
python -m scarascope.evaluation.provider_probe --provider local --confirm-live --iterations 3 \
  --output data/benchmarks/local-smoke.json

# Requires GROQ_API_KEY, plus explicit cloud permission; sends one fixed, public arithmetic question.
python -m scarascope.evaluation.provider_probe --provider cloud --confirm-live --allow-cloud --iterations 3 \
  --output data/benchmarks/cloud-smoke.json
```

The probe records request outcomes and **wall-clock p50/p95 for successful requests**. It limits repetitions to five per call, records no response text, secrets or prompts, and never transfers sensitive documents. `--allow-cloud` is required separately so a local-only operator cannot accidentally incur cloud requests. Actual cost, token usage, QA correctness, quality, and uptime are **null**, not fabricated. A subsequent research benchmark will need issuer-held-out, independently reviewed questions, more repetitions and actual usage metadata before comparing provider economics. Failures are reported and cause a nonzero CLI exit.
