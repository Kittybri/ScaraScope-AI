"""v0.8: independent-review gates, comparable regression reports and API honesty."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from scarascope.api.app import app
from scarascope.ai.retrieval import chunk_sections
from scarascope.data.sec.filings import FilingResearch, FilingSection
from scarascope.evaluation.corpus.annotations import Annotation, validate_annotations
from scarascope.evaluation.corpus.snapshots import make_snapshot
from scarascope.evaluation.corpus.scoring import compare_corpus
from scarascope.evaluation.corpus.baselines import compare_to_baseline, load_baseline
from scarascope.verification.numeric_context import tokens, check_cited_units
from scarascope.services.document_qa import valid_citations


def corpus():
    result=[]
    for cik,accession,word in [
        ("0000320193","0000320193-23-000106","suppliers"),
        ("0000789019","0000950170-24-087843","servers")]:
        url=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/report.htm"
        section=FilingSection(item="Item 1A",title="Risk Factors",text=(
            f"Delays from {word} can interrupt service delivery and increase costs. "*6),
            filing_url=url,accession=accession,filed="2024-08-01",locator="10-K, Item 1A")
        result.append(make_snapshot(FilingResearch(cik=cik,accession=accession,filing_url=url,sections=[section]),"10-K"))
    return result


def case(snapshot,split,answerable,second=False):
    label="verified_" if answerable else "unknown_"
    evidence=chunk_sections(snapshot.sections)[0].evidence_id
    return Annotation(id=f"{label}{split}_{snapshot.cik}",split=split,cik=snapshot.cik,accession=snapshot.accession,
       question=("How could supplier delays interrupt operations?" if answerable else
                 "What are the risks of quantum teleportation devices?"),
       answerable=answerable,gold_evidence_ids=[evidence] if answerable else [],
       gold_answer="Delivery may be interrupted." if answerable else None,
       reviewer="reviewer-1",review_status="reviewed",reviewer_notes="Reviewed against source fixture.",
       second_reviewer="reviewer-2" if second else None,
       second_review_notes="Independent textual cross-check." if second else None)


def test_second_review_requires_distinct_alias_and_notes():
    s=corpus()[1]
    basic=case(s,"heldout",True)
    assert basic.second_reviewer is None
    with pytest.raises(ValueError,match="Second review"):
        Annotation.model_validate({**basic.model_dump(),"second_reviewer":"another"})
    with pytest.raises(ValueError,match="differ"):
        Annotation.model_validate({**basic.model_dump(),"second_reviewer":"REVIEWER-1","second_review_notes":"Cross-checked"})
    with pytest.raises(ValueError,match="Second review"):
        Annotation.model_validate({**basic.model_dump(),"review_status":"unreviewed","second_reviewer":"reviewer-2","second_review_notes":"Cross-checked"})


def test_second_review_gate_never_counts_singly_reviewed_data():
    dev,held=corpus()
    cases=[case(dev,"dev",True),case(held,"heldout",True),case(held,"heldout",False)]
    report=compare_corpus([dev,held],cases,require_second_review=True)
    assert report["status"]=="not_evaluated"
    assert report["methods"]=={}
    assert report["excluded_lacking_second_review"]==2
    assert report["review_policy"]=="two_reviewers"
    reviewed=[cases[0],case(held,"heldout",True,True),case(held,"heldout",False,True)]
    validated=validate_annotations(reviewed,[dev,held])
    assert validated["second_reviewed"]==2
    evaluated=compare_corpus([dev,held],reviewed,require_second_review=True)
    assert evaluated["status"]=="evaluated"
    assert evaluated["reviewed_in_split"]==2
    assert evaluated["methods"]["bm25"]["metrics"]["unanswerable"]==1


def test_pinned_baseline_exact_match_and_regression_detection():
    dev,held=corpus()
    cases=[case(dev,"dev",True),case(held,"heldout",True),case(held,"heldout",False)]
    baseline=compare_corpus([dev,held],cases)
    assert compare_to_baseline(baseline,deepcopy(baseline))["status"]=="pass"
    lower=deepcopy(baseline)
    lower["methods"]["lexical"]["metrics"]["recall_at_3"]=0.0
    result=compare_to_baseline(lower,baseline)
    assert result["status"]=="regression"
    assert result["regressions"][0]["method"]=="lexical"
    assert compare_to_baseline(lower,baseline,tolerance=1)["status"]=="pass"
    with pytest.raises(ValueError,match="tolerance"):
        compare_to_baseline(lower,baseline,tolerance=2)


def test_changed_dataset_or_filing_or_review_policy_is_not_comparable():
    dev,held=corpus()
    cases=[case(dev,"dev",True),case(held,"heldout",True),case(held,"heldout",False)]
    report=compare_corpus([dev,held],cases)
    for key,revision in [("dataset_sha256","another"),("snapshot_digests",{}),
                          ("review_policy","two_reviewers"),("split","dev"),
                          ("reviewed_in_split",0)]:
        modified=deepcopy(report)
        modified[key]=revision
        with pytest.raises(ValueError,match="Incomparable"):
            compare_to_baseline(report,modified)
    trimmed=deepcopy(report)
    del trimmed["methods"]["bm25"]
    with pytest.raises(ValueError,match="methods changed"):
        compare_to_baseline(report,trimmed)
    with pytest.raises(ValueError,match="evaluated"):
        compare_to_baseline({"status":"not_evaluated"},report)


def test_baseline_read_is_bounded_and_symlink_rejected(tmp_path):
    missing=tmp_path/"no.json"
    with pytest.raises(ValueError,match="missing"):
        load_baseline(missing)
    target=tmp_path/"real.json"
    target.write_text('{"status":"evaluated"}')
    alias=tmp_path/"alias.json"
    alias.symlink_to(target)
    with pytest.raises(ValueError,match="symbolic link"):
        load_baseline(alias)
    assert load_baseline(target)=={"status":"evaluated"}


def test_numeric_unit_audit_distinguishes_currency_and_percent():
    source=[SimpleNamespace(label="E1",excerpt="The gross margin was 25% and total costs were $20 million.")]
    assert ("25","percent") in tokens(source[0].excerpt)
    assert check_cited_units("Gross margin was 25% [E1].",source)==[]
    assert check_cited_units("Total costs were $20 [E1].",source)==[]
    assert valid_citations("The gross margin was 25% [E1].",source)
    assert check_cited_units("Costs were 25 dollars, i.e. $25 [E1].",source)
    plain=[SimpleNamespace(label="E1",excerpt="The metric was 30% and the price was $20.")]
    assert check_cited_units("The metric was $30 [E1].",plain)
    assert check_cited_units("The price was 20% [E1].",plain)


def test_engineering_lab_real_corpus_endpoint_has_no_fabricated_results():
    client=TestClient(app)
    for strict in (False,True):
        r=client.get('/api/engineering/corpus-evaluation',params={"require_second_review":str(strict).lower()})
        assert r.status_code==200
        result=r.json()
        assert result["status"]=="not_evaluated"
        assert result["methods"]=={}
        assert result["review_policy"]==("two_reviewers" if strict else "one_reviewer")


def test_engineering_lab_assets_explain_review_gating():
    root=Path(__file__).resolve().parents[2]
    html=(root/'scarascope/static/engineering/index.html').read_text()
    js=(root/'scarascope/static/engineering/lab.js').read_text()
    assert 'id="require-second-review"' in html
    assert '/api/engineering/corpus-evaluation' in js
    assert 'textContent' in js and 'innerHTML' not in js


def test_review_audit_ignores_pretty_scores_and_lists_provenance_gaps():
    from scarascope.evaluation.corpus.review_audit import review_audit
    dev,held=corpus()
    cases=[case(dev,"dev",True),case(held,"heldout",True,True),
           case(held,"heldout",False)]
    report=review_audit(cases,[dev,held])
    assert report['status']=='metadata_review_only'
    assert report['reviewed']==3 and report['second_reviewed']==1
    assert len(report['gaps'])==2
    assert all('accuracy' not in key.lower() for key in report)
    assert report['development_issuers']==1 and report['heldout_issuers']==1


def test_review_audit_flags_missing_reviewer_rationale():
    from scarascope.evaluation.corpus.review_audit import review_audit
    dev,held=corpus()
    case_without_notes=case(held,'heldout',True).model_copy(update={'reviewer_notes':None})
    result=review_audit([case(dev,'dev',True),case_without_notes],[dev,held])
    assert 'first_review_missing_rationale' in result['gaps'][1]['checks']


def test_strict_review_reports_exclusions_without_bad_scores():
    dev,held=corpus()
    draft=Annotation(id='draft_cyberrisk',split='heldout',cik=held.cik,
                     accession=held.accession,question='What cybersecurity risks are discussed?',
                     answerable=True,review_status='unreviewed')
    result=compare_corpus([dev,held],[case(dev,'dev',True),case(held,'heldout',True,True),draft],
                          require_second_review=True)
    assert result['status']=='not_evaluated'
    assert result['excluded_unreviewed']==1
    assert result['reviewed_in_split']==1
    assert result['methods']=={}


def test_real_corpus_api_evaluates_only_snapshot_bound_reviewed_cases(tmp_path,monkeypatch):
    import scarascope.api.engineering as engineering
    from scarascope.evaluation.corpus.snapshots import save_snapshot
    dev,held=corpus()
    save_snapshot(dev,tmp_path/'a.json')
    save_snapshot(held,tmp_path/'b.json')
    cases=[case(dev,'dev',True),case(held,'heldout',True,True),case(held,'heldout',False,True)]
    (tmp_path/'questions.jsonl').write_text(''.join(x.model_dump_json()+'\n' for x in cases))
    monkeypatch.setattr(engineering,'DEFAULT_CORPUS',tmp_path)
    client=TestClient(app)
    response=client.get('/api/engineering/corpus-evaluation?require_second_review=true')
    assert response.status_code==200,response.text
    report=response.json()
    assert report['status']=='evaluated'
    assert report['review_policy']=='two_reviewers'
    assert report['reviewed_in_split']==2
    assert report['methods']['bm25']['metrics']['answerable']==1
    assert len(report['annotation_file_sha256'])==64
    assert 'text' not in report


def test_corpus_audit_command_writes_metadata_without_gold_answers(tmp_path,monkeypatch,capsys):
    import sys
    from scarascope.evaluation.corpus.cli import main
    from scarascope.evaluation.corpus.snapshots import save_snapshot
    dev,held=corpus()
    save_snapshot(dev,tmp_path/'a.json')
    save_snapshot(held,tmp_path/'b.json')
    cases=[case(dev,'dev',True),case(held,'heldout',True)]
    (tmp_path/'questions.jsonl').write_text(''.join(c.model_dump_json()+'\n' for c in cases))
    out=tmp_path/'report.json'
    monkeypatch.setattr(sys,'argv',['cli','audit','--corpus',str(tmp_path),
                        '--annotations',str(tmp_path/'questions.jsonl'),'--output',str(out)])
    main()
    saved=out.read_text()
    assert 'metadata_review_only' in saved
    assert 'Delivery may be interrupted' not in saved
    assert 'second_review_pending' in capsys.readouterr().out
