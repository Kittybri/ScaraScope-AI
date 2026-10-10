"""Versioned benchmark report, JSON artifact writer, and runnable CLI.

CLI: python -m scarascope.evaluation.runner --output data/benchmarks/run.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from .benchmark import run_benchmark
from .financial_accuracy import run_financial_benchmark
from .reliability import run_reliability_checks
from .retrieval import evaluate_retrieval
from .heldout.evaluator import compare_retrievers

DEFAULT_DIR = Path("data/benchmarks")
MAX_HISTORY_BYTES = 2_000_000


async def run_all() -> dict:
    financial = run_financial_benchmark()
    arithmetic = run_benchmark().model_dump()
    retrieval = evaluate_retrieval()
    reliability = await run_reliability_checks()
    groups = {"financial":financial,"arithmetic":arithmetic,"retrieval":retrieval,"reliability":reliability}
    qa = compare_retrievers(split="heldout")
    baseline = qa["methods"]["lexical"]["metrics"]
    candidate = qa["methods"]["bm25"]["metrics"]
    gates = {"bm25_recall_at_3_not_below_lexical": candidate["recall_at_3"] >= baseline["recall_at_3"],
             "bm25_abstention_not_below_lexical": candidate["abstention_accuracy"] >= baseline["abstention_accuracy"]}
    status = "passed" if all(group["passed"] == group["total"] and group["total"] > 0 for group in groups.values()) and all(gates.values()) else "failed"
    return {"report_version":2,"generated_at":datetime.now(timezone.utc).isoformat(),
            "status":status,"runtime":{"python":platform.python_version(),"commit":os.getenv("GITHUB_SHA","")[:40] or None},
            "suites":groups, "qa_retrieval":qa, "retrieval_regression_gates":gates,
            "limitations":["Includes historical SEC-sourced numerical fixtures and synthetic retrieval/provider simulations.",
                           "QA A/B uses source-linked reconstructed table extracts, not raw filing passages. Questions are held out, issuers/figures are not.",
                           "No network calls, paid APIs, live model reasoning or live SEC parsing were evaluated.",
                           "Citation labels or source domains do not establish semantic truth of an LLM response."]}


def save_report(report: dict, target: Path) -> Path:
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replacement avoids half-written JSON under simultaneous readers.
    content = json.dumps(report, indent=2, allow_nan=False, ensure_ascii=True) + "\n"
    temp = target.with_name(target.name + ".tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(target)
    return target


def recent_reports(directory: Path = DEFAULT_DIR, limit: int = 8) -> list[dict]:
    """Local bounded file reads; user input never selects an arbitrary path via HTTP."""
    directory = Path(directory)
    if not directory.is_dir():
        return []
    reports = []
    for path in sorted(directory.glob("*.json"), key=lambda p:p.name, reverse=True)[:max(1,min(limit,20))]:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_HISTORY_BYTES:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("report_version") in (1, 2) and "suites" in payload:
                reports.append({"file":path.name,"generated_at":payload.get("generated_at"),
                                "status":payload.get("status"),
                                "suites":{name:{"passed":v.get("passed"),"total":v.get("total")}
                                          for name,v in payload["suites"].items()}})
        except (ValueError, OSError, AttributeError, TypeError):
            continue
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ScaraScope reproducible financial-engineering evaluations")
    parser.add_argument("--output",type=Path,help="Write JSON results to this local file (not committed automatically)")
    parser.add_argument("--no-save",action="store_true",help="Print results but don't create a results file")
    parser.add_argument("--fail-on-regression",action="store_true",help="Return nonzero if any evaluation fails")
    args = parser.parse_args()
    report = asyncio.run(run_all())
    if not args.no_save:
        target = args.output or DEFAULT_DIR / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
        save_report(report,target)
        print(f"Saved local benchmark: {target}", file=sys.stderr)
    print(json.dumps(report, indent=2))
    if report["status"] != "passed" and args.fail_on_regression:
        sys.exit(1)


if __name__ == "__main__":
    main()
