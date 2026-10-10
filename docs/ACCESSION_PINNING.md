# Exact historical SEC filing selection (v0.10)

**Purpose:** repeatable company research against a **specific accession**, rather
than silently switching to a newer 10-K/10-Q when SEC receives another filing.
This is not a validated financial-answer benchmark, and no real-filing downloads
were performed by GitHub CI.

## Historical SEC sources to reproduce

The accession numbers below identify real filing URLs published by the SEC.
They are *source identifiers only*. They do not represent reviewed answer labels
or prove that the prototype's section extractor succeeds on these full HTML files.

| Issuer | CIK | Form | Exact accession | Original SEC primary document |
| --- | --- | --- | --- | --- |
| Microsoft FY2024 | 0000789019 | 10-K | `0000950170-24-087843` | [FY2024 filing](https://www.sec.gov/Archives/edgar/data/789019/000095017024087843/msft-20240630.htm) |
| Apple FY2023 | 0000320193 | 10-K | `0000320193-23-000106` | [FY2023 filing](https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm) |
| Apple FY2024 first quarter | 0000320193 | 10-Q | `0000320193-24-000006` | [quarterly filing](https://www.sec.gov/Archives/edgar/data/320193/000032019324000006/aapl-20231230.htm) |

## Fetch the *exact* filing (operator initiated)

Set a genuine SEC contact string in your **local**, uncommitted `.env`:

```dotenv
SEC_USER_AGENT=ScaraScope-Research your-real-address@your-domain
```

After `pip install -e '.[test]'`, run:

```bash
python -m scarascope.evaluation.corpus.cli ingest \
  --cik 789019 --form 10-K --accession 0000950170-24-087843

python -m scarascope.evaluation.corpus.cli ingest \
  --cik 320193 --form 10-K --accession 0000320193-23-000106

python -m scarascope.evaluation.corpus.cli ingest \
  --cik 320193 --form 10-Q --accession 0000320193-24-000006

python -m scarascope.evaluation.corpus.cli inventory --all-passages
```

Snapshots are stored under `data/sec-corpus/`, which the project ignores in Git.
Snapshots save the extracted section text, form, accession, filed date and
SHA-256 digest. Do not blindly publish all downloaded source text. Re-downloads
of the **same** accession that yield different normalized text are rejected
rather than replacing evidence ID definitions.

**Why metadata-first?** The app first gets the CIK's official SEC submission
index and checks that the requested accession and form are actually associated
with that issuer, including SEC-identified historical index pages when required.
Only then does it construct a canonical URL on `www.sec.gov` using the SEC's
validated primary-document filename. It will **not** fetch caller-supplied URLs,
follow redirects, guess a filename, or substitute the newest filing when a
requested accession is absent. Historical archive indexes are validated and
bounded; unusually large indexes and filings fail closed.

## Try exact-filing document questions

In the browser's **Ask a filing** panel, choose the form and optionally paste
its SEC accession. Keep this field empty to use the latest filing of that form.
Alternatively, call the API:

```bash
curl -X POST http://127.0.0.1:8000/api/documents/ask \
  -H 'Content-Type: application/json' \
  -d '{"ticker":"MSFT","form":"10-K","accession":"0000950170-24-087843", "question":"What cybersecurity risks were disclosed?", "provider":"none"}'
```

A real contact user-agent, SEC network access and successful section extraction
are required. `DEMO` rejects real accession numbers to avoid suggesting that
fictional text was taken from a real filing. The requested accession also does
not change the basic numerical analysis workflow, which still queries annual
XBRL facts separately.

## Test and evaluation scope

- CI tests use offline mocked SEC manifests, historical index pages, HTTP
  responses and HTML. They verify strict accession selection, form matching,
  URL safety, size limits, and snapshot integrity.
- This implementation has **not** demonstrated actual download of the above
  historical HTML documents on the owner's machine or a complete cross-issuer
  human-reviewed gold dataset.
- Extracted **sections**, not necessarily full 10-K text or exact SEC paragraph
  anchors, are saved. No raw-HTML authenticity hash or detailed table
  reconciliation is provided.
- Human review and issuer-held-out evaluation remain governed by
  [REVIEW_PROTOCOL.md](REVIEW_PROTOCOL.md) and
  [REAL_SEC_CORPUS.md](REAL_SEC_CORPUS.md).
