"""v0.7: SEC archive provenance, source-review gate, reproducible corpus scoring."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from scarascope.api.app import app
from scarascope.ai.retrieval import chunk_sections
from scarascope.data.sec.filings import extract_sections, FilingResearch
from scarascope.evaluation.corpus.snapshots import (
    make_snapshot, load_snapshot, save_snapshot, load_snapshots, validate_source_url,
    canonical_digest)
from scarascope.evaluation.corpus.annotations import Annotation, validate_annotations, load_annotations
from scarascope.evaluation.corpus.scoring import compare_corpus
from scarascope.evaluation.corpus.cli import ingest, inventory

AAPL="https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm"
MSFT="https://www.sec.gov/Archives/edgar/data/789019/000095017024087843/msft-20240630.htm"


def sample(cik, accession, url, keyword):
    text=(f"This is a deliberately fictional SEC HTML fixture. The {keyword} systems rely on several critical dependencies. "
          f"If delays in {keyword} equipment occur, operations can be interrupted and supplier costs can rise. "*4)
    html=f"<html><p>Item 1A. Risk Factors</p><p>{text}</p><p>Item 1B. Unresolved staff comments</p></html>"
    sections=extract_sections(html,url,accession,"2024-08-01",form="10-K")
    assert sections and keyword in sections[0].text
    return make_snapshot(FilingResearch(cik=cik,accession=accession,filing_url=url,
                                       sections=sections),"10-K")


def samples():
    return [sample("0000320193","0000320193-23-000106",AAPL,"supplier"),
            sample("0000789019","0000950170-24-087843",MSFT,"datacenter")]


def reviewed(cik, accession, keyword, evid=None, *, answerable=True, split="heldout"):
    return Annotation(id=f"case_{keyword}_{'yes' if answerable else 'no'}",split=split,cik=cik,
                      accession=accession,question=(f"Which risks regarding {keyword} were disclosed by this issuer?"
                                                     if answerable else "Does this filing discuss subspace quantum banana engines?"),
                      answerable=answerable,gold_evidence_ids=[evid] if answerable else [],
                      gold_answer=f"The {keyword} systems may face disruption." if answerable else None,
                      review_status="reviewed",reviewer="sample-reviewer")


def test_extract_from_html_and_integrity_round_trip(tmp_path):
    first,second=samples()
    assert first.text_sha256==canonical_digest(first.sections)
    save_snapshot(first,tmp_path/"a.json")
    assert save_snapshot(first,tmp_path/"a.json")==tmp_path/"a.json"
    with pytest.raises(ValueError,match="differs"):
        save_snapshot(first.model_copy(update={"text_sha256":"0"*64}),tmp_path/"a.json")
    save_snapshot(second,tmp_path/"b.json")
    got=load_snapshots(tmp_path)
    assert len(got)==2 and got[0].filing_url==AAPL
    assert got[0].sections[0].text.startswith("This is a deliberately fictional SEC HTML fixture")
    modified=json.loads((tmp_path/"a.json").read_text())
    modified["sections"][0]["text"]="Pretend the filing says something else."
    (tmp_path/"a.json").write_text(json.dumps(modified))
    with pytest.raises(ValueError,match="digest"):
        load_snapshot(tmp_path/"a.json")
    (tmp_path/"a.json").unlink()
    (tmp_path/"loop.json").symlink_to(tmp_path/"b.json")
    with pytest.raises(ValueError,match="symbolic link"):
        load_snapshot(tmp_path/"loop.json")


def test_source_allowlist_blocks_host_credentials_traversal_and_wrong_accession():
    validate_source_url(AAPL,"0000320193","0000320193-23-000106")
    for url in [AAPL.replace('www.sec.gov','sec.gov.evil.test'),
                AAPL.replace('320193','789019'),
                AAPL.replace('000032019323000106','000095017024087843'),
                AAPL+'?next=https://evil.test',
                'https://user:pass@www.sec.gov'+AAPL.split('www.sec.gov')[-1],
                AAPL.replace('aapl-20230930.htm','../bad.htm'),
                AAPL.replace('https:', 'http:')]:
        with pytest.raises(ValueError,match="canonical SEC"):
            validate_source_url(url,"0000320193","0000320193-23-000106")


def test_review_gate_and_issuer_holdout():
    first,second=samples()
    p=chunk_sections(second.sections)[0]
    dev=reviewed(first.cik,first.accession,"supplier",chunk_sections(first.sections)[0].evidence_id,split="dev")
    positive=reviewed(second.cik,second.accession,"datacenter",p.evidence_id)
    negative=reviewed(second.cik,second.accession,"bananas",answerable=False)
    cases=[dev,positive,negative]
    report=compare_corpus([first,second],cases)
    assert report["status"]=="evaluated" and report["reviewed_in_split"]==2
    assert report["methods"]["bm25"]["metrics"]["answerable"]==1
    assert report["methods"]["lexical"]["metrics"]["unanswerable"]==1
    assert all("cases" in v for v in report["methods"].values())
    assert report["snapshot_digests"][f"{second.cik}:{second.accession}"]==second.text_sha256
    # The same issuer in dev and heldout is leakage even if questions differ.
    with pytest.raises(ValueError,match="leakage"):
        validate_annotations([dev,positive.model_copy(update={"cik":first.cik,"accession":first.accession})], [first,second])
    with pytest.raises(ValueError,match="missing"):
        validate_annotations([dev,positive.model_copy(update={"gold_evidence_ids":["doesnotexist"]})],[first,second])


def test_never_publish_unreviewed_scores_and_missing_gold(tmp_path):
    first,second=samples()
    pending=Annotation(id="pending_datacenter",split="heldout",cik=second.cik,
                       accession=second.accession,question="How does datacenter availability affect operational delivery?",
                       answerable=True,review_status="unreviewed")
    result=compare_corpus([first,second],[pending])
    assert result["status"]=="not_evaluated" and result["methods"]=={}
    assert result["excluded_unreviewed"]==1
    with pytest.raises(ValueError,match="reviewer"):
        Annotation.model_validate({**pending.model_dump(), "review_status":"reviewed"})


def test_annotation_loading_duplicate_and_invalid_labels(tmp_path):
    first,second=samples()
    pending=Annotation(id="pending_datacenter",split="heldout",cik=second.cik,
                       accession=second.accession,question="What risks affect operation of datacenters?",
                       answerable=True)
    file=tmp_path/"questions.jsonl"
    file.write_text(pending.model_dump_json()+"\n")
    cases,digest=load_annotations(file)
    assert cases==[pending] and len(digest)==64
    file.write_text(pending.model_dump_json()+"\n"+pending.model_dump_json()+"\n")
    with pytest.raises(ValueError,match="duplicate"):
        load_annotations(file)
    with pytest.raises(ValueError,match="reviewer"):
        Annotation.model_validate({**pending.model_dump(),"review_status":"reviewed"})
    with pytest.raises(ValueError,match="evidence"):
        Annotation.model_validate({**pending.model_dump(),"review_status":"reviewed", "reviewer":"alice"})


@pytest.mark.asyncio
async def test_live_ingest_requires_real_contact_and_fails_closed(monkeypatch,tmp_path):
    with pytest.raises(ValueError,match="SEC_USER_AGENT"):
        await ingest(["320193"],"10-K",tmp_path,"ScaraScope sample@example.com")
    with pytest.raises(ValueError,match="distinct"):
        await ingest(["320193","320193"],"10-K",tmp_path,"ScaraScope actual@company.org")
    with pytest.raises(ValueError,match="Invalid CIK"):
        await ingest(["https://evil.test"],"10-K",tmp_path,"ScaraScope actual@company.org")
    class Stub:
        def __init__(self,contact): self.contact=contact
        async def research(self,cik,question,form="10-K"):
            snapshot=samples()[0]
            return FilingResearch(cik=snapshot.cik,accession=snapshot.accession,
                                  filing_url=snapshot.filing_url,sections=snapshot.sections)
    monkeypatch.setattr("scarascope.evaluation.corpus.cli.FilingClient",Stub)
    paths=await ingest(["320193"],"10-K",tmp_path,"ScaraScope actual@company.org")
    assert len(paths)==1 and inventory(tmp_path)["count"]==1


def test_engineering_lab_reports_real_corpus_availability_without_faking_scores():
    result=TestClient(app).get('/api/engineering/corpus-status')
    assert result.status_code==200
    assert 'snapshots' in result.json() and 'note' in result.json()


def test_generated_question_templates_never_count_as_reviewed():
    from scarascope.evaluation.corpus.cli import draft_review_questions
    first,second=samples()
    drafts=draft_review_questions([first,second],{second.cik})
    assert len(drafts)==2
    assert {c.split for c in drafts}=={'dev','heldout'}
    assert all(c.review_status=='unreviewed' and not c.gold_evidence_ids for c in drafts)
    assert compare_corpus([first,second],drafts)['status']=='not_evaluated'
    with pytest.raises(ValueError,match="proper subset"):
        draft_review_questions([first,second],{first.cik,second.cik})


def test_snapshot_rejects_wrong_section_accession_and_oversize(tmp_path):
    first,_=samples()
    changed=first.sections[0].model_copy(update={'accession':'0000000000-00-000001'})
    with pytest.raises(ValueError,match="metadata"):
        make_snapshot(FilingResearch(cik=first.cik,accession=first.accession,
                                    filing_url=first.filing_url,sections=[changed]),"10-K")
    malicious=first.sections[0].model_copy(update={'text':'not SEC text' * 30000})
    with pytest.raises(ValueError,match="metadata"):
        make_snapshot(FilingResearch(cik=first.cik,accession=first.accession,
                                    filing_url=first.filing_url,sections=[malicious]),"10-K")
    with pytest.raises(ValueError,match="unavailable"):
        make_snapshot(FilingResearch(cik=first.cik),"10-K")


def test_evaluation_without_negative_cases_does_not_publish_percentage():
    first,second=samples()
    evid=chunk_sections(second.sections)[0].evidence_id
    case=reviewed(second.cik,second.accession,"datacenter",evid)
    result=compare_corpus([first,second],[case])
    assert result['status']=='not_evaluated' and result['methods']=={}
