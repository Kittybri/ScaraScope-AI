"""Operator-only real-SEC snapshot and reviewer-gated retrieval CLI.

python -m scarascope.evaluation.corpus.cli ingest --cik 320193 --form 10-K
python -m scarascope.evaluation.corpus.cli inventory
python -m scarascope.evaluation.corpus.cli evaluate --annotations data/sec-corpus/questions.jsonl
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import re
from ..runner import save_report
from .snapshots import make_snapshot, save_snapshot, load_snapshots
from .annotations import Annotation, load_annotations
from .scoring import compare_corpus
from .baselines import compare_to_baseline, load_baseline
from .review_audit import review_audit
from .intake import load_intake_plan, collect_intake, question_drafts, write_drafts
from .review_packet import render_review_packet, save_review_packet
from ...data.sec.filings import FilingClient
from ...ai.retrieval import chunk_sections
from ...ai.retrieval.semantic import LocalSentenceEncoder

DEFAULT_CORPUS = Path("data/sec-corpus")


async def ingest(ciks: list[str], form: str, output: Path, user_agent: str,
                 accession: str | None = None) -> list[Path]:
    if accession is not None and len(ciks) != 1:
        raise ValueError("--accession requires exactly one --cik to prevent misattribution.")
    if len(ciks)>8 or len(ciks)!=len(set(ciks)) or not ciks:
        raise ValueError("Select 1–8 distinct company CIKs per ingestion command.")
    if not user_agent or "@" not in user_agent or "example.com" in user_agent.lower():
        raise ValueError("Set a genuine SEC_USER_AGENT contact email in .env or the environment.")
    paths=[]
    client = FilingClient(user_agent)
    for cik in ciks:
        if not re.fullmatch(r"\d{1,10}",cik):
            raise ValueError("Invalid CIK; use decimal digits only.")
        filing = await client.research(cik, "risk operations revenue cybersecurity", form=form,
                                       **({"accession": accession} if accession else {}))
        snapshot = make_snapshot(filing, form)
        target = output / f"{snapshot.cik}_{snapshot.accession}_{snapshot.form}.json"
        paths.append(save_snapshot(snapshot,target))
    return paths


def inventory(folder: Path, *, all_passages: bool = False) -> dict:
    snapshots=load_snapshots(folder)
    return {"count":len(snapshots),"files":[{
        "cik":s.cik,"accession":s.accession,"form":s.form,
        "filed":s.sections[0].filed,"text_sha256":s.text_sha256,
        "sections":[{"item":sec.item,"chars":len(sec.text)} for sec in s.sections],
        "passages":[{"id":p.evidence_id,"section":p.item,"start":p.start_char,
                     "preview":p.excerpt[:120]} for p in chunk_sections(s.sections)][:1200 if all_passages else 35]
    } for s in snapshots]}


def draft_review_questions(snapshots, heldout_ciks: set[str]) -> list[Annotation]:
    """Question scaffolding, not verified answers or gold evidence labels."""
    actual={s.cik for s in snapshots}
    if not actual or not heldout_ciks or not heldout_ciks < actual:
        raise ValueError("Choose a nonempty, proper subset of CIKs as issuer-held-out.")
    cases=[]
    for snap in snapshots:
        for index, sec in enumerate(snap.sections):
            if "Risk" in sec.title:
                question="What operational or business risks does this company discuss in this filing section?"
            else:
                question="What changes in operating performance does management discuss in this filing section?"
            cases.append(Annotation(id=f"c_{snap.cik}_{snap.accession.replace('-', '')}_{index}",
                     split="heldout" if snap.cik in heldout_ciks else "dev",
                     cik=snap.cik,accession=snap.accession,question=question,answerable=True,
                     review_status="unreviewed",
                     reviewer_notes="DRAFT ONLY. Edit question, select evidence IDs, review filing passage and mark reviewed."))
    return cases


def main() -> None:
    parser=argparse.ArgumentParser(description="Opt-in live SEC snapshots, reviewer-audited corpus retrieval")
    sub=parser.add_subparsers(dest="command",required=True)
    ing=sub.add_parser("ingest",help="Download recent 10-K or 10-Q and freeze extracted sections")
    ing.add_argument("--cik",action="append",required=True,help="CIK; repeat up to eight times")
    ing.add_argument("--form",choices=["10-K","10-Q"],default="10-K")
    ing.add_argument("--accession",help="Optional exact historical SEC accession; must belong to the CIK and filing form")
    for p in (ing,sub.add_parser("inventory"),sub.add_parser("evaluate")):
        p.add_argument("--corpus",type=Path,default=DEFAULT_CORPUS)
    audit=sub.add_parser("audit",help="Summarize review completeness without publishing accuracy scores")
    audit.add_argument("--corpus",type=Path,default=DEFAULT_CORPUS)
    audit.add_argument("--annotations",type=Path,required=True)
    audit.add_argument("--output",type=Path)
    dra=sub.add_parser("draft",help="Create unreviewed question scaffolding; never auto-label gold evidence")
    dra.add_argument("--corpus",type=Path,default=DEFAULT_CORPUS)
    dra.add_argument("--heldout-cik",action="append",required=True,help="CIK reserved for held-out evaluation")
    dra.add_argument("--output",type=Path,required=True,help="New JSONL file; refuses to overwrite existing annotations")
    check=sub.add_parser("plan-check",help="Validate the pinned SEC intake plan offline")
    check.add_argument("--plan",type=Path,required=True)
    batch=sub.add_parser("ingest-plan",help="Fetch all specified accession-pinned SEC filings")
    batch.add_argument("--plan",type=Path,required=True)
    batch.add_argument("--corpus",type=Path,default=DEFAULT_CORPUS)
    seeded=sub.add_parser("draft-plan",help="Create unreviewed source-linked question drafts")
    seeded.add_argument("--plan",type=Path,required=True)
    seeded.add_argument("--corpus",type=Path,default=DEFAULT_CORPUS)
    seeded.add_argument("--output",type=Path,required=True)
    packet=sub.add_parser("review-packet",help="Create a read-only, blind HTML SEC source packet")
    packet.add_argument("--plan",type=Path,required=True)
    packet.add_argument("--corpus",type=Path,default=DEFAULT_CORPUS)
    packet.add_argument("--annotations",type=Path,help="Existing questions; hides gold labels in packet")
    packet.add_argument("--output",type=Path,required=True)
    packet.add_argument("--max-passages",type=int,default=36)
    inv=sub.choices["inventory"]
    inv.add_argument("--all-passages",action="store_true",help="List all bounded evidence passage IDs for reviewer audit")
    ev=sub.choices["evaluate"]
    ev.add_argument("--annotations",type=Path,required=True)
    ev.add_argument("--split",choices=["dev","heldout"],default="heldout")
    ev.add_argument("--embedding-model-path",default="")
    ev.add_argument("--output",type=Path)
    ev.add_argument("--require-second-review",action="store_true",help="Score only labels with two distinct reviewers and rationale")
    ev.add_argument("--baseline",type=Path,help="Compare with pinned, identical benchmark report")
    ev.add_argument("--fail-on-regression",action="store_true",help="Nonzero exit when any comparable retrieval metric decreases")
    args=parser.parse_args()
    if args.command=="plan-check":
        plan,digest=load_intake_plan(args.plan)
        print(json.dumps({"status":"plan_validated_offline", "filings":len(plan.filings),
                          "draft_questions":sum(len(x.questions) for x in plan.filings),
                          "plan_sha256":digest,"filings_downloaded":0,"reviewed_questions":0},indent=2))
    elif args.command=="ingest-plan":
        from dotenv import load_dotenv
        load_dotenv()
        plan,digest=load_intake_plan(args.plan)
        result=asyncio.run(collect_intake(plan,args.corpus,os.getenv("SEC_USER_AGENT","")))
        result["plan_sha256"]=digest
        print(json.dumps(result,indent=2))
    elif args.command=="draft-plan":
        plan,digest=load_intake_plan(args.plan)
        cases=question_drafts(plan,load_snapshots(args.corpus))
        write_drafts(cases,args.output)
        print(json.dumps({"status":"unreviewed_drafts", "questions":len(cases),
                          "reviewed":0,"file":str(args.output),"plan_sha256":digest},indent=2))
    elif args.command=="review-packet":
        plan,_=load_intake_plan(args.plan)
        snaps=load_snapshots(args.corpus)
        if args.annotations:
            cases,_=load_annotations(args.annotations)
        else:
            cases=question_drafts(plan,snaps)
        # Verify corpus matches plan BEFORE revealing any excerpts.
        question_drafts(plan,snaps)
        selected={(x.cik,x.accession,x.form) for x in plan.filings}
        html=render_review_packet([s for s in snaps if (s.cik,s.accession,s.form) in selected],cases,
                                  max_passages_per_filing=args.max_passages)
        save_review_packet(html,args.output)
        print(json.dumps({"status":"blind_packet_created_unscored","file":str(args.output),
                          "questions":len(cases),"reviewed_claims":0},indent=2))
    elif args.command=="ingest":
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        files=asyncio.run(ingest(args.cik,args.form,args.corpus,os.getenv("SEC_USER_AGENT",""),
                                 accession=args.accession))
        print(json.dumps({"saved":[str(p) for p in files]},indent=2))
    elif args.command=="inventory":
        print(json.dumps(inventory(args.corpus,all_passages=args.all_passages),indent=2))
    elif args.command=="audit":
        snapshots=load_snapshots(args.corpus)
        cases,digest=load_annotations(args.annotations)
        report=review_audit(cases,snapshots)
        report["annotation_sha256"]=digest
        if args.output:
            save_report(report,args.output)
        print(json.dumps(report,indent=2))
    elif args.command=="draft":
        snapshots=load_snapshots(args.corpus)
        heldout={str(int(cik)).zfill(10) for cik in args.heldout_cik if re.fullmatch(r"\d{1,10}",cik)}
        if len(heldout)!=len(args.heldout_cik):
            raise ValueError("Heldout CIKs must be numeric and unique.")
        questions=draft_review_questions(snapshots,heldout)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open("x",encoding="utf-8") as fp:
            for row in questions:
                fp.write(row.model_dump_json()+"\n")
        print(json.dumps({"draft_questions":len(questions),"reviewed":0,"file":str(args.output)}))
    else:
        snapshots=load_snapshots(args.corpus)
        cases,_=load_annotations(args.annotations)
        encoder=LocalSentenceEncoder(args.embedding_model_path) if args.embedding_model_path else None
        report=compare_corpus(snapshots,cases,split=args.split,encoder=encoder,
                              require_second_review=args.require_second_review)
        if args.fail_on_regression and not args.baseline:
            raise ValueError("--fail-on-regression requires --baseline.")
        if args.baseline:
            report["baseline_comparison"]=compare_to_baseline(report,load_baseline(args.baseline))
        if args.output:
            save_report(report,args.output)
        print(json.dumps(report,indent=2))
        if args.fail_on_regression and report["baseline_comparison"]["status"]!="pass":
            raise SystemExit(3)
        if report["status"]!="evaluated":
            raise SystemExit(2)  # Not a false green benchmark on unreviewed data.


if __name__=="__main__":
    main()
