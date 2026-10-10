# ADR-0001: Optional, locally provisioned semantic retrieval

**Status:** Accepted for experimental opt-in use, not as the default.

**Context.** v0.5 lexical and BM25 retrieval were evaluated on a small,
question-held-out reconstructed financial-reference dataset. The data were not
raw 10-K filing passages, so there was no justification to claim that embedding
search would automatically be better.

**Decision.** Retain lexical/BM25 as keyless defaults; add cosine-similarity
retrieval behind an injected encoder contract with a sentence-transformers
adapter that only opens a local, preinstalled directory. Add hybrid Reciprocal
Rank Fusion, reusable evaluation hooks, tests using deterministic fake vectors,
and explicit configuration errors when a model is absent.

**Consequences.** No unavoidable embedding dependency or cloud expenditure.
Run-time indexing is expensive and the similarity threshold is not calibrated;
there is no persistent semantic index. Results must be benchmarked with a real
local model and a genuinely independent, source-annotated SEC corpus. Fake
embedding test scores are never reported as live embedding quality.

**Rejected alternatives.** Silent downloads on the first request (poor
reproducibility/privacy), cloud embedding API (unnecessary data egress and cost),
and replacing BM25 on the basis of an unmeasured quality claim.
