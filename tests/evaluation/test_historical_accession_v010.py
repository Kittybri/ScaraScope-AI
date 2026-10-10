"""Historical SEC accession replay: network fully mocked, no live SEC in CI."""
from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from scarascope.data.sec.client import SECError
from scarascope.data.sec.filings import FilingClient, FilingResearch, FilingSection
from scarascope.data.sec.submissions import (
    MAX_ARCHIVE_INDEXES, archive_index_names, choose_record,
)
from scarascope.evaluation.corpus.cli import ingest
from scarascope.evaluation.corpus.snapshots import load_snapshot
from scarascope.services.document_qa import DocumentQuestion, answer_document_question
from scarascope.core.config import Settings

CIK = "0000789019"
ACCESSION = "0000950170-24-087843"
ANOTHER_ACCESSION = "0000950170-25-000123"
FILING = "msft-20240630.htm"
SEC_HTML = """<html><body><h2>Item 1A. Risk Factors</h2>
<p>Microsoft faces risks from cybersecurity attacks, cloud datacenter outages, data privacy
issues and security breaches. These could adversely affect company operations and increase
operating expenses across global locations. The security risk material could affect revenue.</p>
<p>Interruptions to infrastructure services may also result in service delays and reduced
customer trust. Data loss or operational failures can disrupt product development and delivery.</p>
<h2>Item 1B. Unresolved Staff Comments</h2><p>None.</p>
<h2>Item 7. Management Discussion and Analysis</h2>
<p>Management reviews operating performance, revenue trends, gross margin changes and
investment in new capacity. Costs may increase as datacenter capacity expands globally,
though future outcomes are uncertain and operations depend on energy availability.</p>
<p>Management also considers cash flows, investment commitments, capital expenditures and
financing. Results in future periods will vary based on demand and cloud growth.</p>
<h2>Item 7A. Market Risks</h2></body></html>"""


def row(accession=ACCESSION, form="10-K", document=FILING):
    return {"form": [form], "accessionNumber": [accession],
            "primaryDocument": [document], "filingDate": ["2024-07-30"]}


def index(recent=None, files=None):
    return {"filings": {"recent": recent if recent is not None else row(),
                        "files": files if files is not None else []}}


def test_metadata_must_match_requested_form_and_safe_document():
    record = choose_record(row(), "10-K", ACCESSION)
    assert record and record.url(CIK) == (
        "https://www.sec.gov/Archives/edgar/data/789019/000095017024087843/msft-20240630.htm")
    assert choose_record(row(), "10-K", ANOTHER_ACCESSION) is None
    with pytest.raises(SECError, match="different filing form"):
        choose_record(row(), "10-Q", ACCESSION)
    for doc in ("http://evil.invalid/anything.htm", "../evil.htm", "outside.pdf", "abc.htm?x=2"):
        with pytest.raises(SECError, match="invalid filing metadata"):
            choose_record(row(document=doc), "10-K", ACCESSION)
    for filed in ("2024-99-99", "next week"):
        broken = row()
        broken["filingDate"] = [filed]
        with pytest.raises(SECError, match="invalid filing date"):
            choose_record(broken, "10-K", ACCESSION)
    for field in row():
        broken = row()
        broken[field] = []
        with pytest.raises(SECError, match="lengths"):
            choose_record(broken, "10-K", ACCESSION)


def test_archived_index_names_are_bounded_and_never_client_supplied():
    name = f"CIK{CIK}-submissions-001.json"
    assert archive_index_names(index(files=[{"name": name}]), CIK) == [name]
    for bad in ("https://evil.invalid", "../../secrets.json", "CIK0000320193-submissions-001.json",
                "CIK0000789019-submissions-../../secret.json", "CIK0000789019-submissions-001.json?x=1"):
        with pytest.raises(SECError, match="unsafe or mismatched"):
            archive_index_names(index(files=[{"name": bad}]), CIK)
    with pytest.raises(SECError, match="too many|Too many"):
        archive_index_names(index(files=[{"name": name}] * (MAX_ARCHIVE_INDEXES + 1)), CIK)
    with pytest.raises(SECError, match="duplicate"):
        archive_index_names(index(files=[{"name": name}, {"name": name}]), CIK)


def mock_sec(monkeypatch, response_handler):
    import scarascope.data.sec.filings as filings
    original = httpx.AsyncClient
    transport = httpx.MockTransport(response_handler)
    monkeypatch.setattr(filings.httpx, "AsyncClient", lambda **kwargs: original(transport=transport, **kwargs))

    async def no_wait():
        return None

    monkeypatch.setattr(filings.SEC_GATE, "wait", no_wait)


@pytest.mark.asyncio
async def test_pinned_recent_accession_downloads_only_matching_sec_document(monkeypatch):
    seen = []

    def handler(req):
        seen.append(str(req.url))
        assert req.url.host in {"data.sec.gov", "www.sec.gov"}
        if req.url.host == "data.sec.gov":
            return httpx.Response(200, json=index())
        assert str(req.url).endswith("/000095017024087843/msft-20240630.htm")
        return httpx.Response(200, text=SEC_HTML)

    mock_sec(monkeypatch, handler)
    result = await FilingClient("ScaraScope audit team@example.edu").research(
        CIK, "cybersecurity disruptions", accession=ACCESSION)
    assert result.accession == ACCESSION and result.filing_url.endswith(FILING)
    assert result.sections and result.evidence
    assert len(seen) == 2


@pytest.mark.asyncio
async def test_pinned_archived_accession_follows_sec_metadata_not_guesswork(monkeypatch):
    seen = []
    archive_name = f"CIK{CIK}-submissions-001.json"

    def handler(req):
        seen.append(str(req.url))
        if req.url.path == f"/submissions/CIK{CIK}.json":
            return httpx.Response(200, json=index(recent=row(ANOTHER_ACCESSION),
                                                   files=[{"name": archive_name}]))
        if req.url.path.endswith(archive_name):
            return httpx.Response(200, json=row())
        if req.url.host == "www.sec.gov":
            return httpx.Response(200, text=SEC_HTML)
        return httpx.Response(500)

    mock_sec(monkeypatch, handler)
    result = await FilingClient("ScaraScope audit team@example.edu").research(
        CIK, "cybersecurity", accession=ACCESSION)
    assert result.accession == ACCESSION and len(seen) == 3
    assert seen[1] == f"https://data.sec.gov/submissions/{archive_name}"


@pytest.mark.asyncio
async def test_wrong_pinned_accession_does_not_fallback_to_latest_or_fetch_filing(monkeypatch):
    seen = []

    def handler(req):
        seen.append(str(req.url))
        return httpx.Response(200, json=index())

    mock_sec(monkeypatch, handler)
    result = await FilingClient("ScaraScope audit team@example.edu").research(
        CIK, "cybersecurity", accession=ANOTHER_ACCESSION)
    assert result.accession is None and not result.sections
    assert any("No substitute" in message for message in result.warnings)
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_archive_form_mismatch_does_not_download_wrong_document(monkeypatch):
    seen = []

    def handler(req):
        seen.append(str(req.url))
        return httpx.Response(200, json=index(recent=row(form="10-Q")))

    mock_sec(monkeypatch, handler)
    with pytest.raises(SECError, match="different filing form"):
        await FilingClient("ScaraScope audit team@example.edu").research(
            CIK, "cybersecurity", accession=ACCESSION, form="10-K")
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_oversized_html_never_creates_fake_snapshot(monkeypatch):
    def handler(req):
        if req.url.host == "data.sec.gov":
            return httpx.Response(200, json=index())
        return httpx.Response(200, content=b"X" * 5_000_001)

    mock_sec(monkeypatch, handler)
    with pytest.raises(SECError, match="size limit"):
        await FilingClient("ScaraScope audit team@example.edu").research(
            CIK, "cybersecurity", accession=ACCESSION)


@pytest.mark.asyncio
async def test_ingest_pinned_snapshot_matches_exact_source_and_digest(tmp_path, monkeypatch):

    class FakeClient:
        def __init__(self, ua):
            pass

        async def research(self, cik, question, form, **kwargs):
            assert kwargs.get("accession") == ACCESSION
            url = "https://www.sec.gov/Archives/edgar/data/789019/000095017024087843/msft-20240630.htm"
            section = FilingSection(item="Item 1A", title="Risk Factors", text="Real test text for a synthetic offline snapshot. " * 12,
                                    filing_url=url, accession=ACCESSION, filed="2024-07-30", locator="10-K, Item 1A")
            return FilingResearch(cik=CIK, accession=ACCESSION, filing_url=url, sections=[section])

    import scarascope.evaluation.corpus.cli as cli
    monkeypatch.setattr(cli, "FilingClient", FakeClient)
    result = await ingest([CIK], "10-K", tmp_path, "ScaraScope test team@example.edu", accession=ACCESSION)
    assert len(result) == 1
    pinned = load_snapshot(result[0])
    assert pinned.accession == ACCESSION and pinned.sections[0].text.startswith("Real test text")
    with pytest.raises(ValueError, match="exactly one"):
        await ingest([CIK, "320193"], "10-K", tmp_path, "ScaraScope test team@example.edu", accession=ACCESSION)


def test_document_question_rejects_invalid_pinned_accession_and_demo():
    with pytest.raises(ValidationError):
        DocumentQuestion(ticker="MSFT", question="What risks are disclosed?", accession="2024")


@pytest.mark.asyncio
async def test_document_api_does_not_pass_pinned_accession_for_fictional_demo():
    request = DocumentQuestion(ticker="DEMO", question="What cybersecurity risks are described?",
                               accession=ACCESSION)
    with pytest.raises(ValueError, match="FICTIONAL-DEMO"):
        await answer_document_question(request, Settings())


@pytest.mark.asyncio
async def test_document_question_pinned_accession_reaches_filing_client():
    class FakeSEC:
        async def resolve_ticker(self, ticker):
            return "Microsoft Corporation", CIK

    class FakeFiling:
        async def research(self, cik, question, limit, form, accession=None):
            assert cik == CIK and accession == ACCESSION
            return FilingResearch(cik=CIK, warnings=["Not in offline mocked SEC index."])

    result = await answer_document_question(DocumentQuestion(
        ticker="MSFT", question="What cybersecurity risks are disclosed?", accession=ACCESSION),
        Settings(), sec_client=FakeSEC(), filing_client=FakeFiling())
    assert result.status == "filing_unavailable" and result.accession is None
    assert any("Not in offline mocked SEC index" in warning for warning in result.warnings)


def test_historical_docs_have_real_primary_archive_urls():
    docs = (Path(__file__).resolve().parents[2] / "docs/ACCESSION_PINNING.md").read_text()
    assert "0000950170-24-087843" in docs and "0000320193-23-000106" in docs

@pytest.mark.asyncio
async def test_sec_redirect_is_rejected_without_external_followup(monkeypatch):
    hosts = []

    def handler(req):
        hosts.append(req.url.host)
        if req.url.host == "data.sec.gov":
            return httpx.Response(200, json=index())
        return httpx.Response(302, headers={"Location": "https://tracking.invalid/not-a-filing"})

    mock_sec(monkeypatch, handler)
    result = await FilingClient("ScaraScope audit team@example.edu").research(
        CIK, "cybersecurity", accession=ACCESSION)
    assert result.accession is None
    assert hosts == ["data.sec.gov", "www.sec.gov"]
    assert any("no alternate filing" in warning for warning in result.warnings)


@pytest.mark.asyncio
async def test_archive_index_http_failure_does_not_download_any_other_filing(monkeypatch):
    hosts = []
    name = f"CIK{CIK}-submissions-001.json"

    def handler(req):
        hosts.append(req.url.host)
        if req.url.path.endswith(name):
            return httpx.Response(503, text="unavailable")
        return httpx.Response(200, json=index(recent=row(ANOTHER_ACCESSION), files=[{"name": name}]))

    mock_sec(monkeypatch, handler)
    result = await FilingClient("ScaraScope audit team@example.edu").research(
        CIK, "cybersecurity", accession=ACCESSION)
    assert result.accession is None and result.sections == []
    assert hosts == ["data.sec.gov", "data.sec.gov"]
