# Optional local semantic and hybrid retrieval (v0.6)

**Status: implemented as an opt-in experiment.** It is not an established
accuracy improvement, a hosted embeddings service, or a substitute for primary
filing evidence. The default retrieval strategies remain **lexical** and **BM25**.

## Install only when needed

```bash
pip install -e '.[semantic,test]'
```

An operator must separately install an appropriate sentence-transformers model
**into a local directory** after reviewing its license, storage requirements and
trustworthiness. For example, on a machine with network access and an approved
model source, download and save the model explicitly. No model file is bundled
with this repository, and the app itself does not download any model. Models may
be large and may take time to load on CPU-only systems.

Set an absolute directory path in local `.env`:

```dotenv
SCARASCOPE_EMBEDDING_MODEL_PATH=/your/local/model/directory
```

Then restart FastAPI. In the *Ask a filing* panel, choose **Semantic (local model
required)** or **Hybrid (local model required)**. A missing directory or the
absence of the optional library causes a clear error. ScaraScope does **not**
silently send embedding inputs to a cloud provider or downgrade to BM25 while
pretending it performed semantic search.

## Evaluation

```bash
# Keyless and unchanged baseline: lexical vs BM25 only
python -m scarascope.evaluation.runner --fail-on-regression

# Optional: use the preinstalled local model to compare four strategies
python -m scarascope.evaluation.runner \
  --embedding-model-path /your/local/model/directory \
  --output data/benchmarks/with-local-embeddings.json
```

The Engineering Lab has an optional **local embeddings** checkbox. If checked,
it runs the same reconstructed-financial-question comparison with semantic and
hybrid strategies. The report includes the dataset fingerprint, numerator /
denominator, and missed questions. Results cannot be treated as LLM financial
answer accuracy. In particular, the tiny question-held-out reference corpus
shares issuers and figures between development and evaluation questions. There
is no independently audited full-filing benchmark yet.

## Algorithms and limits

- Semantic: cosine similarity over sentence embedding vectors, with a provisional
  similarity threshold. Zero-length, non-finite or inconsistent vectors fail
  validation. The score is a ranking signal, **not** a support probability.
- Hybrid: Reciprocal Rank Fusion of BM25 and semantic rankings. Ranks are
  fused; BM25 and cosine scores are not naively added.
- The model processes a bounded number of extracted filing chunks in memory
  for each query. Index persistence, cached embeddings, CPU/GPU resource limits
  and large-corpus scalability are future work.
- Embedding model selection, threshold and retrieval strategy require measured
  validation on a truly independent corpus before selecting a default.
- **Privacy distinction:** all embeddings are computed by the configured local
  model; optional generation follows the separate Ollama/Groq privacy policy.
