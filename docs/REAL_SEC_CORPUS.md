# ScaraScope v0.7: real SEC filing corpus and issuer-held-out review

**Status:** an implemented **operator-run ingestion and evaluation pipeline**, not a completed human-reviewed benchmark. In the CI environment no live SEC documents are fetched, and no independently reviewed real-filing QA scores are claimed. Prior v0.5/v0.6 offline QA metrics come from *reconstructed reference-table extracts*, not original filing passages.

## 1. Ingest actual SEC filing sections

ScaraScope's existing SEC client fetches an official SEC submission manifest and the **latest** matching 10-K or 10-Q primary HTML, checks the accession/document path, follows SEC fair-access pacing and extracts supported Item 1A and management-discussion sections where possible. ScaraScope saves a validated immutable-text snapshot with an accession-linked URL and SHA-256 digest of the extracted sections.

Requirements: real contact email, network access to SEC, Python 3.11+, and low-volume use under [SEC fair-access guidance](https://www.sec.gov/about/developer-resources). Create **an untracked local** `.env` with `SEC_USER_AGENT=ScaraScope Research your-real-contact@your-domain` and run:

```bash
python -m scarascope.evaluation.corpus.cli ingest --cik 320193 --form 10-K
python -m scarascope.evaluation.corpus.cli ingest --cik 789019 --form 10-K
python -m scarascope.evaluation.corpus.cli ingest --cik 1652044 --form 10-K
python -m scarascope.evaluation.corpus.cli ingest --cik 1018724 --form 10-K
python -m scarascope.evaluation.corpus.cli inventory
# When selecting exact gold passage IDs for review:
python -m scarascope.evaluation.corpus.cli inventory --all-passages
```

These example CIKs are **Apple, Microsoft, Alphabet, and Amazon**. The first run retrieves their latest filing at the time of execution. **Do not assume the filing or accession is the FY2023/FY2024 one cited in earlier benchmark examples.** For more historical or quarter-specific filings, a pinned-accession fetcher would still be required. SEC occasionally rate-limits or changes HTML; treat extraction warnings and missing sections as failures to collect evidence, not proof of accuracy. Only sections that ScaraScope successfully extracts are stored.

Snapshot files are written under `data/sec-corpus/` (excluded from commits by project ignore rules). SEC URL must match the canonical host, CIK and accession. A corrupted, edited, oversized, duplicate, wrong-host or misattributed section snapshot is rejected before evaluation. The digest authenticates **local consistency**, not the SEC's authorship independently.

## 2. Create issuer-disjoint *unreviewed* question drafts

Choose one or more CIKs exclusively for evaluation, e.g. **Alphabet and Amazon**. Apple and Microsoft then form development issuers. The CLI uses these *explicit* assignments, not a random question split sharing the same filings.

```bash
python -m scarascope.evaluation.corpus.cli draft \
  --heldout-cik 1652044 --heldout-cik 1018724 \
  --output data/sec-corpus/questions.jsonl
```

The draft generator creates only generic question scaffolding. It does **not** fabricate gold answers, select passages automatically or mark questions as reviewed. It refuses to overwrite an existing question file. Edit the questions to make them specific, answerable from the corresponding filing, and useful for the intended benchmark. Add unanswerable questions to test abstention. Reserve held-out issuer questions for final evaluation; never use their labels to tune retrieval or prompts.

A question record looks like:

```json
{
  "id": "alphabet_cyberrisk_001",
  "split": "heldout",
  "cik": "0001652044",
  "accession": "<replace-with-exact-accession-from-inventory>",
  "question": "Which operational risks does this filing identify concerning data-center equipment?",
  "answerable": true,
  "gold_evidence_ids": ["<real-passage-id-from-inventory>"],
  "gold_answer": "<human-checked-answer-grounded-in-that-passage>",
  "review_status": "reviewed",
  "reviewer": "reviewer-alias",
  "reviewer_notes": "<why-this-evidence-supports-the-answer>"
}
```

The literal angle-bracket fields above are **placeholders**. Evidence IDs are SHA-256-derived from the exact extracted section bytes and offsets; they change if extraction or chunking changes. Run `inventory` to find each passage's evidence ID and preview, then inspect the **full original SEC filing** and its dates/units. A reviewer should verify every answer against the source, then mark it `reviewed`. An independent second reviewer should check disagreements before any portfolio accuracy claim. Merely putting a name in `reviewer` does not prove independent review.

## 3. Run evaluation or acknowledge missing data

```bash
python -m scarascope.evaluation.corpus.cli evaluate \
  --annotations data/sec-corpus/questions.jsonl \
  --split heldout \
  --output data/benchmarks/real-sec-heldout.json

# Optional only if a licensed embedding model was explicitly installed locally:
python -m scarascope.evaluation.corpus.cli evaluate \
  --annotations data/sec-corpus/questions.jsonl \
  --embedding-model-path /absolute/path/to/model
```

The evaluator compares lexical and BM25 retrieval over the same snapshot passages, with optional local semantic and hybrid methods. It tracks Recall@1/3/5, MRR, unanswerable abstention, failed question IDs, dataset SHA and source text digests. Retrieval is restricted to the question's issuer **and exact filing accession**. The evaluator detects question-level issuer overlap between dev and heldout, missing evidence IDs, and unverified labels; it **excludes all unreviewed cases** from metric denominators.

**Fail-closed behavior:** If there are no reviewed questions or if the reviewed set lacks either answerable or unanswerable questions, it reports `not_evaluated` with no scores and exits nonzero. That is correct behavior. It is not a failed production evaluation; it is an incomplete dataset. No benchmark score is generated from the placeholder drafts.

**Known limits:** This assesses *retrieval of a specific reviewed passage*, not free-form LLM answer quality or semantic entailment. Some true answers have multiple passages; a reviewer must select valid evidence IDs. SEC HTML may be noisy and section extraction is best-effort. Capturing the latest filing makes comparisons time-dependent until snapshots are pinned. Reviewers should also record reasoned disagreements and audit the labels independently. There is **no automatic metric claiming that AI prose is factually correct**.

## 4. Evidence and employer presentation

The Engineering Lab shows the number and hashes of locally stored real-filing snapshots and counts of reviewed/unreviewed labels. It intentionally does not present synthetic figures as live filing scores. To publish a reproducible real-filing benchmark in the future, obtain permission to distribute source text or publish accession links and hashes with an ingestion recipe, lock the issuer-held-out split, document review methods, and attach the exact benchmark output to a tagged commit.

Official historical filing examples for manual cross-checking:
- [Apple FY2023 10-K](https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm)
- [Microsoft FY2024 10-K](https://www.sec.gov/Archives/edgar/data/789019/000095017024087843/msft-20240630.htm)

These are **historical references**, not filings the v0.7 CI downloaded or used to claim live accuracy.


## v0.8 review-quality controls and baseline regression

See [Independent Review and Regression Protocol](REVIEW_PROTOCOL.md). Operators can now run `python -m scarascope.evaluation.corpus.cli audit --annotations data/sec-corpus/questions.jsonl` for reviewer metadata and gap IDs. Add a **separate** `second_reviewer` and `second_review_notes` only after an actual independent review; software cannot verify that a real person performed it. `evaluate --require-second-review` excludes every case lacking that second review. `--baseline ... --fail-on-regression` rejects incompatible datasets or corpus hashes and exits nonzero if comparable retrieval metrics decline.

The Engineering Lab can show real-corpus retrieval scores only when verified local snapshots and reviewed questions are present; otherwise it shows **not evaluated**. These safeguards do not create human-reviewed questions or measure LLM answer accuracy by themselves.

## v0.10: repeatable historical-accession retrieval

The previous CLI pulled the **latest** matching form, so collecting the same
corpus weeks later could silently select different documents. The `ingest`
command now accepts `--accession` when **exactly one** `--cik` is specified. It
checks the official SEC submissions metadata before fetching the matching filing
and never replaces a missing historical accession with the newest one. For
specific historical Microsoft and Apple 10-K/10-Q examples, operator commands,
security boundaries and limitations, see [ACCESSION_PINNING.md](ACCESSION_PINNING.md).

Live retrieval and independent answer review remain pending; these changes do
not imply successful live extraction or audited question-answer accuracy.


## v0.11: pinned four-issuer intake plan and blind review packet

See [SEC_EVIDENCE_INTAKE.md](SEC_EVIDENCE_INTAKE.md) for the versioned Apple/Microsoft/Alphabet/Amazon source plan, offline validation, manual GitHub Actions collection, and blind HTML passage review. The 16 provisional questions are **unreviewed**; the actual SEC source snapshot and independent human labels still need to be collected.
