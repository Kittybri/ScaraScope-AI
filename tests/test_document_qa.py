"""Reproducible SEC document RAG tests with injected fakes (zero external calls)."""
import pytest
from fastapi.testclient import TestClient
from scarascope.ai.retrieval import chunk_sections, search_passages
from scarascope.core.config import Settings
from scarascope.core.models import LLMResult
from scarascope.data.sec.filings import FilingSection, FilingResearch, extract_sections
from scarascope.services.document_qa import (
    DocumentQuestion, answer_document_question, valid_citations,
)
from scarascope.evaluation.retrieval import evaluate_retrieval
from scarascope.api import app

SEC_URL = "https://www.sec.gov/Archives/edgar/data/000001/test.htm"


def section(item: str, text: str) -> FilingSection:
    return FilingSection(item=item, title="Test filing", text=text, filing_url=SEC_URL,
                         accession="0000000001-26-000001", filed="2026-01-01", locator=f"10-K, {item}")


class FakeSec:
    async def resolve_ticker(self, ticker):
        assert ticker == "MSFT"
        return "Microsoft Test", "0000000001"


class FakeFilings:
    def __init__(self, sections):
        self.sections = sections
        self.calls = []

    async def research(self, cik, question, limit=4, form="10-K"):
        self.calls.append((cik, form, question))
        return FilingResearch(cik=cik, accession="0000000001-26-000001",
                              filing_url=SEC_URL, sections=self.sections)


class FakeRouter:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def explain(self, request, system, prompt, fallback_text):
        self.calls.append((request, system, prompt))
        return LLMResult(provider="groq", model="stub", text=self.response)


@pytest.mark.asyncio
async def test_synthetic_demo_offline_and_clearly_marked():
    result = await answer_document_question(DocumentQuestion(ticker="DEMO", question="What cybersecurity risks exist?"), Settings())
    assert result.data_kind == "synthetic_demo"
    assert result.provider == "deterministic"
    assert "fictional" in str(result.warnings).lower()
    assert result.evidence and "[E1]" in result.answer


def test_chunk_offsets_and_budget_and_ranked_search():
    doc = section("Item 1A", "Cybersecurity issues with data centers and customer privacy. " * 95)
    passages = chunk_sections([doc])
    assert len(passages) > 2
    assert all(len(p.excerpt) <= 1000 and doc.text[p.start_char:p.start_char + len(p.excerpt)] == p.excerpt for p in passages)
    assert all(p.evidence_id for p in passages)
    assert not search_passages(passages, "What about penguins migrating to Mars?")
    assert search_passages(passages, "cybersecurity privacy", limit=2)
    assert len(search_passages(passages, "cybersecurity privacy", limit=2)) <= 2


@pytest.mark.asyncio
async def test_good_model_citations_and_source_metadata():
    docs = FakeFilings([section("Item 1A", "Cybersecurity disruptions caused downtime to customer services and compromised account availability." * 3)])
    router = FakeRouter("The filing describes cybersecurity disruptions. [E1]")
    result = await answer_document_question(DocumentQuestion(ticker="MSFT", question="What cybersecurity risks are described?", provider="cloud"),
                                            Settings(), sec_client=FakeSec(), filing_client=docs, router=router)
    assert result.status == "synthesized" and result.provider == "groq"
    assert result.citation_format_validated and result.evidence[0].filing_url == SEC_URL
    assert "UNTRUSTED" in router.calls[0][1]
    assert docs.calls[0][1] == "10-K"


@pytest.mark.asyncio
async def test_hallucinated_citation_falls_back_to_exact_excerpts():
    docs = FakeFilings([section("Item 1A", "Cybersecurity disruptions may impact operational security and reputation. " * 6)])
    router = FakeRouter("Unlimited revenue is guaranteed. [E99]")
    result = await answer_document_question(DocumentQuestion(ticker="MSFT", question="What cybersecurity risks are described?"),
                                            Settings(), sec_client=FakeSec(), filing_client=docs, router=router)
    assert result.status == "extractive"
    assert "guaranteed" not in result.answer
    assert any("unknown evidence" in w for w in result.warnings)
    assert not valid_citations("A claim [E99]", result.evidence)
    assert not valid_citations("A claim without labels", result.evidence)
    assert not valid_citations("A claim [E1] [E100]", result.evidence)


@pytest.mark.asyncio
async def test_unsupported_question_does_not_call_model():
    docs = FakeFilings([section("Item 7", "Revenue growth came from subscription customers and demand. " * 8)])
    router = FakeRouter("Invented details [E1]")
    result = await answer_document_question(DocumentQuestion(ticker="MSFT", question="Describe research on Antarctic penguin fossils."),
                                            Settings(), sec_client=FakeSec(), filing_client=docs, router=router)
    assert result.status == "insufficient_evidence"
    assert not router.calls
    assert not result.evidence


@pytest.mark.asyncio
async def test_private_routing_and_10q_passage():
    docs = FakeFilings([section("Item 2", "Liquidity conditions changed following higher subscription demand and revenue. " * 5)])
    router = FakeRouter("Liquidity changed. [E1]")
    with pytest.raises(ValueError):
        await answer_document_question(DocumentQuestion(ticker="DEMO", question="Describe revenue changes", privacy="local_only", provider="cloud"), Settings())
    result = await answer_document_question(DocumentQuestion(ticker="MSFT", question="How has liquidity changed?", form="10-Q", privacy="local_only", provider="local"),
                                            Settings(), sec_client=FakeSec(), filing_client=docs, router=router)
    assert docs.calls[0][1] == "10-Q"
    assert router.calls[0][0].privacy == "local_only"
    assert router.calls[0][0].provider == "local"
    assert result.status == "synthesized"


def test_10q_section_parser():
    html = "<p>Item 2. Management Discussion</p><p>" + "Business liquidity and borrowing costs affected our business performance. " * 7 + "</p><p>Item 3. Market Risk</p>"
    sections = extract_sections(html, SEC_URL, "0000000001-26-000001", "2026-01-01", form="10-Q")
    assert len(sections) == 1 and sections[0].item == "Item 2"
    assert "10-Q" in sections[0].locator


def test_document_endpoint_validation_and_demo():
    client = TestClient(app)
    assert client.post("/api/documents/ask", json={"ticker": "DEMO", "question": "What cybersecurity risks exist?"}).status_code == 200
    assert client.post("/api/documents/ask", json={"ticker": "DEMO", "question": "What cybersecurity risks exist?", "form": "8-K"}).status_code == 422
    assert client.post("/api/documents/ask", json={"ticker": "DEMO", "question": "What cybersecurity risks exist?", "privacy": "local_only", "provider": "cloud"}).status_code == 400
    assert client.post("/api/documents/ask", json={"ticker": "DEMO", "question": "What cybersecurity risks exist?", "top_k": 100}).status_code == 422


def test_retrieval_regression_fixture():
    report = evaluate_retrieval()
    assert report["passed"] == report["total"], report
    assert report["total"] >= 5

@pytest.mark.asyncio
async def test_filing_not_found_returns_explicit_unavailable_without_model():
    class EmptyFilings:
        async def research(self, cik, question, limit=4, form="10-K"):
            return FilingResearch(cik=cik, warnings=["No matching 10-Q found."])
    router = FakeRouter("made up information [E1]")
    result = await answer_document_question(
        DocumentQuestion(ticker="MSFT", form="10-Q", question="What was the litigation risk?"), Settings(),
        sec_client=FakeSec(), filing_client=EmptyFilings(), router=router)
    assert result.status == "filing_unavailable"
    assert "not be retrieved" in result.answer
    assert not router.calls
    assert not result.evidence


def test_retrieval_benchmark_endpoint():
    r = TestClient(app).get("/api/evaluation/retrieval")
    assert r.status_code == 200
    assert r.json()["passed"] == r.json()["total"]
    assert "NOT live SEC" in r.json()["scope"]


def test_document_frontend_is_static_and_script_is_wired():
    from pathlib import Path
    html = (Path(__file__).resolve().parents[1] / "scarascope/static/index.html").read_text()
    script = (Path(__file__).resolve().parents[1] / "scarascope/static/documents.js").read_text()
    assert '/static/documents.js' in html and 'id="document-form"' in html
    assert "textContent" in script and "innerHTML" not in script
