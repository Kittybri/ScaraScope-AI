"""Offline SEC intake-plan, blind-review and CI integrity regressions."""
import asyncio
from pathlib import Path
import json
import sys

import pytest
from pydantic import ValidationError

from scarascope.data.sec.filings import FilingResearch, FilingSection
from scarascope.evaluation.corpus.annotations import Annotation, load_annotations
from scarascope.evaluation.corpus.cli import main
from scarascope.evaluation.corpus.intake import (
    IntakePlan, collect_intake, load_intake_plan, question_drafts, write_drafts,
)
from scarascope.evaluation.corpus.review_packet import render_review_packet, save_review_packet
from scarascope.evaluation.corpus.snapshots import make_snapshot, load_snapshots

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / 'docs/evidence/sec_intake_plan_v1.json'


def mini_plan():
    raw = json.loads(PLAN.read_text())
    raw['filings'] = raw['filings'][:2]
    raw['filings'][1]['split'] = 'heldout'
    return IntakePlan.model_validate(raw)


def snapshot_for(item, text=None):
    section = FilingSection(item='Item 1A',title='Risk Factors',
       text=text or ('Adverse supplier interruptions, cyber incidents, and infrastructure '
                     'failures can materially impact operations and financial performance. ' * 5),
       filing_url=item.expected_filing_url, accession=item.accession,
       filed='2023-11-02',locator='10-K, Item 1A')
    return make_snapshot(FilingResearch(cik=item.cik,accession=item.accession,
              filing_url=item.expected_filing_url,sections=[section]),item.form)


class FakeClient:
    def __init__(self, plan, bad=None):
        self.spec = {i.cik: i for i in plan.filings}
        self.calls = []
        self.bad = bad

    async def research(self,cik,question,form,accession):
        self.calls.append((cik,form,accession))
        item = self.spec[cik]
        snap = snapshot_for(item)
        if cik == self.bad:
            return FilingResearch(cik=cik,accession=accession,filing_url=item.expected_filing_url,
                                  sections=[])  # fail without writing any files
        return FilingResearch(cik=snap.cik,accession=snap.accession,
                              filing_url=snap.filing_url,sections=snap.sections)


def test_versioned_plan_uses_actual_sec_canonical_filing_ids():
    plan, digest=load_intake_plan(PLAN)
    assert len(plan.filings)==4 and len(digest)==64
    assert sum(len(i.questions) for i in plan.filings)==16
    assert {x.issuer for x in plan.filings}=={'Apple','Microsoft','Alphabet','Amazon'}
    assert {x.split for x in plan.filings}=={'dev','heldout'}
    assert all(x.expected_filing_url.startswith('https://www.sec.gov/Archives/edgar/data/') for x in plan.filings)
    assert all(x.accession.replace('-','') in x.expected_filing_url for x in plan.filings)


@pytest.mark.parametrize('change,pattern',[
    (lambda p: p['filings'][0].update(expected_filing_url='https://evil.invalid/steal.htm'), 'canonical SEC'),
    (lambda p: p['filings'][1].update(cik=p['filings'][0]['cik'],split='heldout'), 'canonical SEC|issuer-disjoint'),
    (lambda p: p['filings'][0].update(split='heldout') or p['filings'][1].update(split='heldout'), 'issuer-disjoint'),
    (lambda p: p['filings'].append(p['filings'][0].copy()), 'Duplicate accession'),
])
def test_intake_plan_fails_closed_on_unsafe_or_unusable_metadata(change,pattern):
    raw=json.loads(PLAN.read_text())
    change(raw)
    with pytest.raises((ValueError,ValidationError),match=pattern):
        IntakePlan.model_validate(raw)


def test_plan_file_size_symlink_and_invalid_json_are_rejected(tmp_path):
    file=tmp_path/'oversized.json'
    file.write_bytes(b'{' + b' '*64001)
    with pytest.raises(ValueError,match='oversized'): load_intake_plan(file)
    original=tmp_path/'original.json'
    original.write_text(PLAN.read_text())
    alias=tmp_path/'alias.json'
    alias.symlink_to(original)
    with pytest.raises(ValueError,match='symbolic link'): load_intake_plan(alias)
    original.write_text('{}')
    with pytest.raises(ValidationError): load_intake_plan(original)


@pytest.mark.asyncio
async def test_intake_downloads_only_pinned_accessions_and_stores_unreviewed(tmp_path):
    plan=mini_plan()
    fake=FakeClient(plan)
    result=await collect_intake(plan,tmp_path,'ScaraScope user@university.edu',client=fake)
    assert result['status']=='collected_unreviewed' and result['reviewed_questions']==0
    assert len(load_snapshots(tmp_path))==2
    assert [x[-1] for x in fake.calls]==[spec.accession for spec in plan.filings]
    assert len(result['snapshots'][0]['source_text_sha256'])==64
    again=await collect_intake(plan,tmp_path,'ScaraScope user@university.edu',client=fake)
    assert again['filings']==2
    with pytest.raises(ValueError,match='SEC_USER_AGENT'):
        await collect_intake(plan,tmp_path,'',client=fake)


@pytest.mark.asyncio
async def test_batch_failure_before_writing_and_existing_snapshot_immutable(tmp_path):
    plan=mini_plan()
    with pytest.raises(ValueError,match='sections'):
        await collect_intake(plan,tmp_path,'App user@university.edu',client=FakeClient(plan,plan.filings[-1].cik))
    assert not list(tmp_path.glob('*.json'))
    good=FakeClient(plan)
    await collect_intake(plan,tmp_path,'App user@university.edu',client=good)
    class Changed(FakeClient):
        async def research(self,cik,question,form,accession):
            obj=await super().research(cik,question,form,accession)
            obj.sections[0].text+='Changed after labels were pinned!'
            return obj
    with pytest.raises(ValueError,match='Existing pinned evidence changed'):
        await collect_intake(plan,tmp_path,'App user@university.edu',client=Changed(plan))
    assert len(load_snapshots(tmp_path))==2


def test_drafts_are_unreviewed_and_never_overwrite_reviewer_edits(tmp_path):
    plan=mini_plan()
    snaps=[snapshot_for(item) for item in plan.filings]
    draft=question_drafts(plan,snaps)
    assert len(draft)==8
    assert all(not row.gold_evidence_ids and not row.gold_answer and row.review_status=='unreviewed' for row in draft)
    assert {d.split for d in draft}=={'dev','heldout'}
    path=tmp_path/'questions.jsonl'
    write_drafts(draft,path)
    read,_=load_annotations(path)
    assert read == draft
    with pytest.raises(FileExistsError): write_drafts(draft,path)
    with pytest.raises(ValueError,match='no pinned snapshot'):
        question_drafts(plan,snaps[:1])
    altered=snaps.copy()
    altered[-1]=altered[-1].model_copy(update={'filing_url':snaps[0].filing_url})
    with pytest.raises(ValueError,match='URL differs'):
        question_drafts(plan,altered)


def test_html_review_packet_escapes_untrusted_filing_and_blinds_gold(tmp_path):
    plan=mini_plan()
    snaps=[snapshot_for(item, text=('The company disclosed <script>alert(7)</script> '
          'and & characters alongside financial supply risk. '*12)) for item in plan.filings]
    drafts=question_drafts(plan,snaps)
    first=drafts[0].model_copy(update={'review_status':'reviewed','reviewer':'secret-identity',
        'reviewer_notes':'Secret reviewer note','gold_evidence_ids':[],
        'gold_answer':'PRIVATE ANSWER'})
    # Model-copy bypasses validation to test that packet never emits private labels.
    drafts[0]=first
    html=render_review_packet(snaps,drafts,max_passages_per_filing=3)
    assert '&lt;script&gt;' in html and '<script>' not in html
    assert 'PRIVATE ANSWER' not in html and 'secret-identity' not in html
    assert 'Secret reviewer note' not in html
    assert 'Content-Security-Policy' in html and 'default-src' in html
    assert 'www.sec.gov' in html and 'unscored' in html
    out=tmp_path/'packet.html'
    save_review_packet(html,out)
    with pytest.raises(ValueError,match='exists'): save_review_packet(html,out)
    with pytest.raises(ValueError,match='1–150'):
        render_review_packet(snaps,drafts,max_passages_per_filing=0)


def test_ci_workflow_remains_explicit_opt_in_and_no_accuracy_claims():
    ci=(ROOT/'.github/workflows/ci.yml').read_text()
    workflow=(ROOT/'.github/workflows/sec-intake.yml').read_text()
    assert 'plan-check' in ci
    assert 'workflow_dispatch:' in workflow
    assert 'secrets.SEC_USER_AGENT' in workflow
    assert 'ingest-plan' in workflow and 'draft-plan' in workflow and 'review-packet' in workflow
    assert 'upload-artifact' in workflow
    assert 'schedule:' not in workflow
    assert 'SEC_USER_AGENT=' not in workflow  # no hardcoded contact email


def test_draft_plan_and_blind_packet_cli(tmp_path,monkeypatch,capsys):
    import scarascope.evaluation.corpus.cli as cli
    plan=mini_plan()
    plan_file=tmp_path/'plan.json'
    plan_file.write_text(plan.model_dump_json())
    corpus=tmp_path/'corpus'
    corpus.mkdir()
    from scarascope.evaluation.corpus.snapshots import save_snapshot
    for item in plan.filings:
        snap=snapshot_for(item)
        save_snapshot(snap,corpus/f'{item.cik}_{item.accession}_{item.form}.json')
    questions=tmp_path/'questions.jsonl'
    monkeypatch.setattr(sys,'argv',['cli','draft-plan','--plan',str(plan_file),
                                   '--corpus',str(corpus),'--output',str(questions)])
    cli.main()
    assert json.loads(capsys.readouterr().out)['reviewed']==0
    monkeypatch.setattr(sys,'argv',['cli','review-packet','--plan',str(plan_file),
                                   '--corpus',str(corpus),'--annotations',str(questions),
                                   '--output',str(tmp_path/'packet.html')])
    cli.main()
    output=json.loads(capsys.readouterr().out)
    assert output['status']=='blind_packet_created_unscored' and output['reviewed_claims']==0
    assert (tmp_path/'packet.html').exists()
    monkeypatch.setattr(sys,'argv',['cli','plan-check','--plan',str(plan_file)])
    cli.main()
    assert json.loads(capsys.readouterr().out)['filings_downloaded']==0
