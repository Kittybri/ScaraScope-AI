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
    if args.command=="ingest":
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
