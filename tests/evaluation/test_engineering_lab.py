"""Demonstrate what the offline scores do, and what they cannot prove."""
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from scarascope.api.app import app
from scarascope.api.dependencies import get_settings
from scarascope.core.config import Settings
from scarascope.core.models import AnnualFinancials, FactSource
from scarascope.evaluation.financial_accuracy import DATASET, load_reference, run_financial_benchmark
from scarascope.evaluation.reliability import run_reliability_checks
from scarascope.evaluation.runner import recent_reports, run_all, save_report
from scarascope.observability.metrics import snapshot
from scarascope.verification.financial_claims import FinancialClaim, check_claim
from scarascope.verification.period_checks import check_periods
from scarascope.verification.source_validation import check_financial_sources
from scarascope.verification.citations import check_answer_citations
from scarascope.services.document_qa import valid_citations


def test_real_historical_benchmark_case_denominator_and_official_sources():
    result = run_financial_benchmark()
    assert result["passed"] == result["total"] == 34, result
    assert result["companies"] == ["AAPL", "MSFT"]
    assert len(result["dataset_sha256"]) == 64
    assert all(url.startswith("https://www.sec.gov/Archives/") for url in result["sources"])
    msft = next(row for row in result["results"] if row["id"] == "MSFT-2024-revenue")
    assert msft["expected"] == msft["observed"] == 245122
    apple = next(row for row in result["results"] if row["id"] == "AAPL-2023-net_income")
    assert apple["expected"] == apple["observed"] == 96995


def test_dataset_checksum_is_reproducible_and_changes_after_edit(tmp_path):
    data, digest = load_reference()
    twin = tmp_path / "reference.json"
    twin.write_bytes(DATASET.read_bytes())
    assert load_reference(twin)[1] == digest
    changed = json.loads(twin.read_text())
    changed["companies"][0]["rows"][0]["revenue"] += 100
    twin.write_text(json.dumps(changed))
    changed_result = run_financial_benchmark(twin)
    assert changed_result["passed"] < changed_result["total"]
    assert changed_result["dataset_sha256"] != digest


def _rows():
    first = AnnualFinancials(fiscal_year=2024,period_end="2024-06-30",revenue=120,
                             operating_income=30,net_income=12,operating_margin_pct=25,
                             net_margin_pct=10,revenue_growth_pct=20)
    prior = AnnualFinancials(fiscal_year=2023,period_end="2023-06-30",revenue=100,
                             operating_income=25,net_income=10)
    for row in (first,prior):
        row.sources=[FactSource(metric=metric,form="10-K",accession="0000950170-24-087843",
                    filed="2024-07-30",period_end=row.period_end,
                    source_url="https://www.sec.gov/Archives/edgar/data/789019/000095017024087843/msft-20240630.htm")
                    for metric in ("revenue","operating_income","net_income")]
    return [first,prior]


def test_wrong_fiscal_year_unit_period_and_numeric_claim_are_rejected():
    rows=_rows()
    assert not check_claim(FinancialClaim(2024,"revenue",120,"USD_millions"), rows)
    assert any("Unit mismatch" in x for x in check_claim(FinancialClaim(2024,"revenue",120,"percent"),rows))
    assert any("Value mismatch" in x for x in check_claim(FinancialClaim(2024,"revenue",999,"USD_millions"),rows))
    assert any("not in available" in x for x in check_claim(FinancialClaim(2022,"revenue",120,"USD_millions"),rows))
    assert any("annual" in x for x in check_periods([rows[0], rows[0].model_copy(update={"period_end":rows[0].period_end})]))
    assert check_periods(rows) == []


def test_invalid_sec_url_source_period_and_accession_rejected():
    rows=_rows()
    rows[0].sources[0].source_url="https://www.sec.gov.evil.test/Archives/fake"
    rows[0].sources[1].accession="MISSING"
    rows[0].sources[2].period_end=rows[1].period_end
    problems=check_financial_sources(rows)
    assert any("invalid SEC domain" in x for x in problems)
    assert any("invalid accession" in x for x in problems)
    assert any("period mismatch" in x for x in problems)


def test_citation_guard_rejects_invented_numbers_even_with_valid_evidence_id():
    references=[SimpleNamespace(label="E1",excerpt="Revenue was 120 million USD for the period.")]
    assert valid_citations("Revenue was 120 million USD. [E1]",references)
    assert check_answer_citations("Revenue was 900 million USD. [E1]",references)
    assert not valid_citations("Revenue was 900 million USD. [E1]",references)
    assert check_answer_citations("Revenue was 120 million USD. [E8]",references)
    assert check_answer_citations("Revenue was 120 million USD.",references)


@pytest.mark.asyncio
async def test_runner_is_offline_and_does_not_fabricate_live_provider_calls():
    before=snapshot()["counters"]
    outcome=await run_all()
    after=snapshot()["counters"]
    assert outcome["status"] == "passed"
    assert outcome["suites"]["reliability"]["passed"] == 6
    assert after == before
    assert "No network" in " ".join(outcome["limitations"])


@pytest.mark.asyncio
async def test_reliability_simulation_enforces_zero_cloud_calls_for_local_only():
    result=await run_reliability_checks()
    assert result["passed"] == result["total"]
    private=next(row for row in result["results"] if row["id"]=="local_only_outage_no_leak")
    assert private["cloud_calls"] == 0


def test_atomic_json_history_is_bounded_and_does_not_follow_symlinks(tmp_path):
    payload={"report_version":1,"generated_at":"2026-10-10T12:00:00Z","status":"passed","suites":{"financial":{"passed":1,"total":1}}}
    saved=save_report(payload,tmp_path/"20261010.json")
    assert json.loads(saved.read_text())["status"]=="passed"
    (tmp_path/"broken.json").write_text("bad json")
    (tmp_path/"20261011.json").symlink_to(saved)
    history=recent_reports(tmp_path)
    assert len(history)==1 and history[0]["file"]=="20261010.json"


def test_engineering_lab_http_and_protected_endpoints():
    client=TestClient(app)
    page=client.get("/engineering")
    assert page.status_code==200 and "Engineering Lab" in page.text
    assert "engineering/lab.js" in page.text
    result=client.get("/api/engineering/benchmark")
    assert result.status_code==200 and result.json()["suites"]["financial"]["total"]==34
    assert client.get("/api/engineering/history").status_code==200
    assert client.get("/api/engineering/runtime").status_code==200
    app.dependency_overrides[get_settings]=lambda:Settings(app_api_key="secret",require_auth=True)
    try:
        assert client.get("/api/engineering/benchmark").status_code==401
        assert client.get("/api/engineering/benchmark",headers={"X-API-Key":"secret"}).status_code==200
    finally:
        app.dependency_overrides.clear()
