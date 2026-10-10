"""Regression gates for comparable reviewed SEC evidence-retrieval benchmarks.

Never compare non-identical datasets or filing text. A higher result on a
changed corpus is *not* evidence of a model improvement.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

METRICS = ("recall_at_1", "recall_at_3", "recall_at_5", "mrr_at_5", "abstention_accuracy")


def compare_to_baseline(current: dict[str, Any], baseline: dict[str, Any], *, tolerance: float = 0.0) -> dict[str, Any]:
    if not 0 <= tolerance <= 1:
        raise ValueError("Regression tolerance must be between 0 and 1.")
    if current.get("status") != "evaluated" or baseline.get("status") != "evaluated":
        raise ValueError("Both benchmark runs must contain reviewed, evaluated cases.")
    for key in ("benchmark", "split", "dataset_sha256", "snapshot_digests"):
        if current.get(key) != baseline.get(key):
            raise ValueError(f"Incomparable benchmark: {key} changed.")
    if current.get("review_policy") != baseline.get("review_policy"):
        raise ValueError("Incomparable benchmark: review policy changed.")
    for key in ("questions_in_split", "reviewed_in_split"):
        if current.get(key) != baseline.get(key):
            raise ValueError(f"Incomparable benchmark: {key} changed.")
    if set(current["methods"]) != set(baseline["methods"]):
        raise ValueError("Incomparable benchmark: retrieval methods changed.")
    names = sorted(current["methods"])
    if not names:
        raise ValueError("No shared retrieval methods exist for comparison.")
    comparisons = []
    for name in names:
        new = current["methods"][name]["metrics"]
        old = baseline["methods"][name]["metrics"]
        for denominator in ("answerable", "unanswerable"):
            if new.get(denominator) != old.get(denominator):
                raise ValueError("Benchmark class denominator changed.")
        for metric in METRICS:
            previous = float(old[metric])
            observed = float(new[metric])
            if not (0 <= previous <= 1 and 0 <= observed <= 1):
                raise ValueError("Invalid metric value in report.")
            comparisons.append({"method":name,"metric":metric,"baseline":previous,"current":observed,
                                "delta":round(observed-previous,5),
                                "regressed":observed + tolerance < previous})
    return {"status":"regression" if any(c["regressed"] for c in comparisons) else "pass",
            "comparable":True,"tolerance":tolerance,"shared_methods":names,
            "regressions":[c for c in comparisons if c["regressed"]],"comparisons":comparisons}


def load_baseline(path: Path) -> dict[str, Any]:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1_000_000:
        raise ValueError("Baseline report missing, oversized, or a symbolic link.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload,dict):
        raise ValueError("Baseline report must be an object.")
    return payload
