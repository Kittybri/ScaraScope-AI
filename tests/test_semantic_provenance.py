"""Local-only semantic retrieval and auditable response provenance regressions."""
from __future__ import annotations

from hashlib import sha256
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient

from scarascope.ai.retrieval import chunk_sections, search_semantic, search_hybrid
from scarascope.ai.retrieval.semantic import LocalSentenceEncoder
from scarascope.core.config import Settings
from scarascope.data.sec.filings import FilingSection, FilingResearch
from scarascope.evaluation.heldout.evaluator import compare_retrievers
from scarascope.services.document_qa import DocumentQuestion, answer_document_question
from scarascope.api import app

SEC_URL = "https://www.sec.gov/Archives/edgar/data/123/test.htm"


def sections():
    return [FilingSection(item="Item 1A", title="Risk factors",
                          text="Cybersecurity incidents could disrupt operations and compromise sensitive systems.",
                          filing_url=SEC_URL, accession="0000000123-26-000001", filed="2026-01-01",
                          locator="10-K, Item 1A"),
            FilingSection(item="Item 7", title="Management discussion",
                          text="Sales accelerated after a stronger performance in subscription revenue.",
                          filing_url=SEC_URL, accession="0000000123-26-000001", filed="2026-01-01",
                          locator="10-K, Item 7")]


class FakeEncoder:
    """Deterministic tiny vectors: a test double, NOT an embedding benchmark."""
    def encode(self, texts):
        out=[]
        for text in texts:
            if "cybersecurity" in text.lower() or "threat" in text.lower() or "risk" in text.lower():
                out.append([1.0, 0.0, 0.0])
            elif "revenue" in text.lower() or "sales" in text.lower():
                out.append([0.0, 1.0, 0.0])
            else:
                out.append([0.0, 0.0, 1.0])
        return out


class BadEncoder:
    def __init__(self, vectors):
        self.vectors = vectors
    def encode(self, texts):
        return self.vectors


def test_semantic_ranking_handles_synthetic_synonym_and_hybrid_fusion():
    passages = chunk_sections(sections())
    question = "What threats could affect the business?"
    assert search_semantic(passages, question, FakeEncoder())[0].item == "Item 1A"
    assert search_hybrid(passages, question, FakeEncoder())[0].item == "Item 1A"
    assert not search_semantic(passages, "", FakeEncoder())
    assert search_semantic([], question, FakeEncoder()) == []
    assert search_hybrid(passages, question, FakeEncoder(), limit=1)
    with pytest.raises(ValueError, match="rrf_k"):
        search_hybrid(passages, question, FakeEncoder(), rrf_k=0)


def test_embedding_validation_refuses_bad_or_nonfinite_vectors(tmp_path):
    passages = chunk_sections(sections())
    with pytest.raises(ValueError, match="number of vectors"):
        search_semantic(passages, "Risk question", BadEncoder([[1.0]]))
    with pytest.raises(ValueError, match="mismatch"):
        search_semantic(passages, "Risk question", BadEncoder([[1., 0.], [1., 0.], [0., 1., 2.]]))
    with pytest.raises(ValueError, match="invalid"):
        search_semantic(passages, "Risk question", BadEncoder([[float('nan')], [1.], [0.]]))
    with pytest.raises(ValueError, match="model directory"):
        LocalSentenceEncoder(str(tmp_path / "not-installed"))
    with pytest.raises(ValueError, match="threshold"):
        search_semantic(passages, "Risk question", FakeEncoder(), minimum_similarity=-1)


class FakeSEC:
    async def resolve_ticker(self, ticker):
        return "Reference Corp", "0000000123"


class FakeFilings:
    async def research(self, cik, question, limit, form):
        return FilingResearch(cik=cik, accession="0000000123-26-000001",
                              filing_url=SEC_URL, sections=sections())


class MaliciousRouter:
    async def explain(self, *args):
        raise AssertionError("No provider should be called when provider=none.")


@pytest.mark.asyncio
async def test_provenance_is_tamper_evident_and_excludes_prompts_and_keys():
    request = DocumentQuestion(ticker="MSFT", question="What cybersecurity risks are described?",
                               retrieval_strategy="hybrid", provider="none", privacy="local_only")
    result = await answer_document_question(request, Settings(groq_api_key="secret-key-321"),
                       sec_client=FakeSEC(), filing_client=FakeFilings(), encoder=FakeEncoder(),router=MaliciousRouter())
    assert result.evidence and result.provenance
    manifest = result.provenance
    assert manifest.run_id.startswith("rs_") and len(manifest.run_id) == 35
    assert manifest.privacy_policy == "local_only" and manifest.provider == "deterministic"
    assert manifest.model == "none" and manifest.retrieval_strategy == "hybrid"
    assert manifest.total_ms >= manifest.retrieval_ms >= 0
    assert len(manifest.references) == len(result.evidence)
    for entry, source in zip(manifest.references, result.evidence):
        assert entry.excerpt_sha256 == sha256(source.excerpt.encode()).hexdigest()
        assert entry.evidence_id == source.evidence_id
    raw = manifest.model_dump_json()
    assert "secret-key-321" not in raw and request.question not in raw
    assert "Cybersecurity incidents" not in raw


@pytest.mark.asyncio
async def test_no_evidence_still_has_a_safe_trace():
    result = await answer_document_question(DocumentQuestion(ticker="MSFT",question="Where are interplanetary wormholes?",provider="none"),
                                             Settings(),sec_client=FakeSEC(),filing_client=FakeFilings())
    assert result.status == "insufficient_evidence"
    assert result.provenance is not None and result.provenance.references == []


def test_semantic_option_requires_local_model_and_never_silently_downloads():
    client = TestClient(app)
    base={"ticker":"DEMO","question":"What cybersecurity risks are discussed?", "provider":"none"}
    for strategy in ("semantic", "hybrid"):
        response=client.post('/api/documents/ask',json={**base,"retrieval_strategy":strategy})
        assert response.status_code==400
        assert "SCARASCOPE_EMBEDDING_MODEL_PATH" in response.json()["detail"]
    response=client.get('/api/engineering/retrieval-comparison?include_semantic=true')
    assert response.status_code==400
    assert response.json()['detail'].startswith('Configure SCARASCOPE_EMBEDDING_MODEL_PATH')


def test_same_evaluation_harness_accepts_injected_embedders():
    result=compare_retrievers(encoder=FakeEncoder())
    assert result['semantic_evaluated'] is True
    assert set(result['methods'])=={'lexical','bm25','semantic','hybrid'}
    assert result['methods']['semantic']['metrics']['answerable']==12
    assert len(result['dataset_sha256'])==64
    baseline=compare_retrievers()
    assert baseline['semantic_evaluated'] is False
    assert 'hybrid' not in baseline['methods']
