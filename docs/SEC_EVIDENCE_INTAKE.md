# v0.11: pinned SEC evidence intake and blind review

**Status:** implemented and offline-tested, but **no live SEC filings were downloaded in the development environment**. The intake plan contains real SEC filing identifiers and provisional questions. It does **not** contain verified answer labels, an independent human review, or a measured real-filing accuracy score.

## Why this step exists

Earlier releases already supported exact-accession ingestion and reviewed-only retrieval evaluation, but an operator still had to collect issuers one by one, build source-specific question drafts, and locate evidence IDs manually. This release assembles that repeatable workflow without weakening the review gate.

The source plan is [`evidence/sec_intake_plan_v1.json`](evidence/sec_intake_plan_v1.json). It specifies four official historical SEC 10-K filings:

| Development set | Accession | Official archive |
| --- | --- | --- |
| Apple FY2023 | `0000320193-23-000106` | [SEC filing](https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm) |
| Microsoft FY2024 | `0000950170-24-087843` | [SEC filing](https://www.sec.gov/Archives/edgar/data/789019/000095017024087843/msft-20240630.htm) |

| Reserved issuer-held-out set | Accession | Official archive |
| --- | --- | --- |
| Alphabet FY2023 | `0001652044-24-000022` | [SEC filing](https://www.sec.gov/Archives/edgar/data/1652044/000165204424000022/goog-20231231.htm) |
| Amazon FY2023 | `0001018724-24-000008` | [SEC filing](https://www.sec.gov/Archives/edgar/data/1018724/000101872424000008/amzn-20231231.htm) |

There are **16 initial question drafts**, including four presumed unanswerable prompts. These are *only starting hypotheses*. A reviewer must validate each question and whether its answer really does or does not appear in the extracted filing sections. There are no stored gold answers. Do not tune retrieval against held-out questions.

## Option A: run on GitHub Actions without local Python setup

1. In your repository's **Settings → Secrets and variables → Actions**, create a repository secret named `SEC_USER_AGENT`. Its value should identify your real application and contain an email address at which the SEC can contact you. Do not add it to your source files or paste it into public Issues.
2. Under **Actions**, find **SEC Evidence Intake (Manual)** and select **Run workflow**. This workflow never runs on push or on a schedule; it only runs when deliberately triggered.
3. If SEC access, metadata or extraction fails, the workflow fails. Do not interpret a failed intake as an AI accuracy result or relax SEC protections to force a green check.
4. When successful, download the `scarascope-sec-unreviewed-intake` artifact (retained for seven days). It contains pinned local snapshots, unreviewed question JSONL and `blind-review.html`. The archive is *not* a scored benchmark; be mindful of redistribution and archival requirements before sharing filing text.
5. Have the first reviewer inspect each exact original filing and extracted passage. A **different** person should independently review each label without seeing the first person's gold answer or note. The blind HTML packet is read-only and intentionally hides those labels.

The repository's normal Python CI validates the plan **offline**, without a contact secret and without downloading SEC files. No automatic/cron SEC scraping is introduced.

## Option B: run on your own laptop

After installing `pip install -e '.[test]'` and setting a genuine `SEC_USER_AGENT` in your untracked `.env`:

```bash
# No network required; validates accession/CIK/URL, issuer split and question structure.
python -m scarascope.evaluation.corpus.cli plan-check \
  --plan docs/evidence/sec_intake_plan_v1.json

# Live, SEC-polite, accession-pinned, bounded requests. This requires network access.
python -m scarascope.evaluation.corpus.cli ingest-plan \
  --plan docs/evidence/sec_intake_plan_v1.json --corpus data/sec-corpus

# Drafts are created with review_status=unreviewed; never overwrites an edited file.
python -m scarascope.evaluation.corpus.cli draft-plan \
  --plan docs/evidence/sec_intake_plan_v1.json --corpus data/sec-corpus \
  --output data/sec-corpus/questions.jsonl

# Read-only, blind HTML with passage IDs, normalized offsets and original SEC links.
python -m scarascope.evaluation.corpus.cli review-packet \
  --plan docs/evidence/sec_intake_plan_v1.json --corpus data/sec-corpus \
  --annotations data/sec-corpus/questions.jsonl \
  --output data/sec-corpus/blind-review.html
```

Open `blind-review.html` locally, not on a public website. It has no scripts or remote assets and HTML-escapes untrusted source text. Only a subset of excerpts is shown to keep the page bounded; `inventory --all-passages` lists more evidence IDs. Passage offsets refer to **extracted** filing text, not a guaranteed deep-link anchor to the original filing.

## Human review and strict evaluation

Edit `data/sec-corpus/questions.jsonl` only after inspecting the actual SEC filing and its extracted evidence:

- For answerable questions: record a defensible `gold_answer`, the exact `gold_evidence_ids`, the true fiscal period/units, `review_status=reviewed`, reviewer alias and an original written rationale.
- For unanswerable questions: first verify the answer truly cannot be supported by the extracted corpus, set `answerable=false`, and leave gold answers and evidence IDs empty.
- For independently checked questions: record **a different** second reviewer and written second-review rationale. Reviewer aliases are self-attested; the program cannot verify human identity or independence.
- Do not silently change the frozen issuer split, source hashes, or retrieval configuration between baseline and regression runs.

```bash
python -m scarascope.evaluation.corpus.cli audit \
  --corpus data/sec-corpus --annotations data/sec-corpus/questions.jsonl
python -m scarascope.evaluation.corpus.cli evaluate \
  --corpus data/sec-corpus --annotations data/sec-corpus/questions.jsonl \
  --split heldout --require-second-review \
  --output data/benchmarks/pinned-sec-reviewed-v1.json
```

**Expected before review:** `not_evaluated`, no accuracy numbers and a nonzero evaluation exit status. That is the correct outcome, not an evaluation failure. The resulting scores, when review is real, measure **retrieval**, not free-form LLM answer accuracy.

## Technical guarantees and limitations

- Input plan accepts only SEC canonical archive URL assertions matching CIK and accession; the actual filing URLs are **not fetched from plan strings**. The SEC client constructs its own URL after checking official submission metadata.
- Plan permits 2–12 filings, refuses duplicate accession/form combinations and requires separate issuers for development and held-out sets.
- Downloads run sequentially under existing SEC pacing and size caps. If the SEC blocks access, an unexpected form is returned, or sections cannot be extracted, the intake stops without producing a claimed score.
- Downloaded texts remain under `.gitignore`'s `data/`. A byte-mismatched pinned snapshot cannot be overwritten without deliberate investigation.
- Intentionally large/iXBRL-heavy filings may exceed the current client size limit or resist the heuristic section extractor; this should be recorded as an intake failure, not edited away. It is possible that not all four planned documents can be ingested without additional *tested* parser work.
- HTML review packets may contain source filing material; apply sensible access controls, copyright/redistribution judgment and data-retention policies to archived artifacts.
- No live provider, Oracle deployment, independently reviewed answers, or held-out financial QA score is included in v0.11.

Also see [REVIEW_PROTOCOL.md](REVIEW_PROTOCOL.md), [ACCESSION_PINNING.md](ACCESSION_PINNING.md) and [REAL_SEC_CORPUS.md](REAL_SEC_CORPUS.md).
