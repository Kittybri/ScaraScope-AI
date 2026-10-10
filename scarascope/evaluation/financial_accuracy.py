"""Offline benchmark against fixed, source-linked historical SEC statement figures.

The reference figures and expected answers are recorded in a reviewed JSON file.
This evaluates deterministic handling of *recorded* facts, not LLM comprehension,
not live retrieval, and not independently validated EDGAR CompanyFacts taxonomy.
"""
from __future__ import annotations

import json
from datetime import date
from hashlib import sha256
from math import isclose
from pathlib import Path
from ..core.models import AnnualFinancials, FactSource
from ..finance.calculations import enrich_financials
from ..verification.financial_claims import FinancialClaim, check_claim

DATASET = Path(__file__).parent / "datasets" / "sec_annual_reference_v1.json"


def load_reference(path: Path = DATASET) -> tuple[dict, str]:
    raw = path.read_bytes()
    data = json.loads(raw)
    if data.get("version") != 1 or data.get("dataset") != "sec-10k-historical-reference-v1":
        raise ValueError("Unsupported historical financial benchmark dataset.")
    return data, sha256(raw).hexdigest()


def _rows(company: dict) -> list[AnnualFinancials]:
    source = company["source"]
    rows = []
    for snapshot in company["rows"]:
        date_end = date.fromisoformat(snapshot["period_end"])
        refs = [FactSource(metric=field, form=source["form"], accession=source["accession"],
                           filed=source["filed"], period_end=date_end, source_url=source["url"])
                for field in ("revenue", "operating_income", "net_income")]
        rows.append(AnnualFinancials(**snapshot, sources=refs))
    return enrich_financials(rows)


def run_financial_benchmark(path: Path = DATASET) -> dict:
    data, digest = load_reference(path)
    companies = {co["ticker"]: _rows(co) for co in data["companies"]}
    results = []
    for case in data["cases"]:
        key = (case["ticker"], case["fiscal_year"])
        rows = companies.get(key[0], [])
        target = next((row for row in rows if row.fiscal_year == key[1]), None)
        metric = case["metric"]
        observed = getattr(target, metric, None) if target is not None and metric in {
            "revenue", "operating_income", "net_income", "revenue_growth_pct", "operating_margin_pct", "net_margin_pct"} else None
        claim = FinancialClaim(fiscal_year=key[1], metric=metric, value=case["expected"], unit=case["unit"])
        issues = check_claim(claim, rows) if rows else ["Missing company in benchmark data."]
        passed = (not issues and observed is not None and isclose(observed, case["expected"], rel_tol=0, abs_tol=0.011 if case["unit"] == "percent" else 1e-4))
        results.append({"id":case["id"],"ticker":key[0],"fiscal_year":key[1],"metric":metric,
                        "expected":case["expected"],"observed":observed,"unit":case["unit"],
                        "passed":passed,"issues":issues})
    count = sum(case["passed"] for case in results)
    total = len(results)
    return {"suite":"historical_sec_financial_fixtures", "dataset_version":data["version"],
            "dataset_sha256":digest, "passed":count,"total":total,
            "accuracy_pct":round(100 * count / total, 2) if total else 0,
            "companies":sorted(companies),"sources":[co["source"]["url"] for co in data["companies"]],
            "results":results,
            "scope":"Offline historical amounts manually transcribed from cited 10-K consolidated statements; tests Python ratios, periods and source metadata. NOT live SEC ingestion or LLM question-answer accuracy."}
