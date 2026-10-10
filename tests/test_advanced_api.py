"""Exercise newly registered routes without any API keys or network calls."""
from fastapi.testclient import TestClient
from scarascope.api import app

client=TestClient(app)

def test_valuation_and_benchmark_endpoint():
    payload={"starting_unlevered_fcf":100,"fcf_growth_pct":0,"discount_rate_pct":10,"terminal_growth_pct":0,"forecast_years":1}
    resp=client.post("/api/valuation/dcf",json=payload)
    assert resp.status_code==200
    assert resp.json()["result"]["implied_enterprise_value"]==1000
    assert client.post("/api/valuation/dcf",json={**payload,"terminal_growth_pct":10}).status_code==422
    result=client.get("/api/evaluation/deterministic").json()
    assert result["passed"]==result["total"]

def test_demo_agent_and_export_endpoints():
    resp=client.post("/api/agent/research",json={"ticker":"DEMO","provider":"none"})
    assert resp.status_code==200,resp.text
    assert resp.json()["verification"]["passed"]
    pdf=client.post("/api/reports/research.pdf",json={"ticker":"DEMO","provider":"none"})
    assert pdf.status_code==200
    assert pdf.content.startswith(b"%PDF-")
    workbook=client.post("/api/reports/research.xlsx",json={"ticker":"DEMO","provider":"none"})
    assert workbook.status_code==200
    assert workbook.content.startswith(b"PK")

def test_local_only_cloud_rejected_in_new_agent_routes():
    bad={"ticker":"DEMO","privacy":"local_only","provider":"cloud"}
    assert client.post("/api/agent/research",json=bad).status_code==400
    assert client.post("/api/reports/research.pdf",json=bad).status_code==400

def test_compare_same_ticker_does_not_need_sec():
    r=client.post("/api/compare",json={"left":"DEMO","right":"DEMO"})
    assert r.status_code==422

def test_watchlist_roundtrip(tmp_path,monkeypatch):
    from scarascope.api.dependencies import get_settings
    from scarascope.core.config import Settings
    app.dependency_overrides[get_settings]=lambda:Settings(history_db_path=str(tmp_path/"history.sqlite3"))
    try:
        assert client.post("/api/watchlist",json={"ticker":"msft"}).status_code==200
        assert client.get("/api/watchlist").json()["items"][0]["ticker"]=="MSFT"
        assert client.delete("/api/watchlist/MSFT").status_code==200
        assert client.get("/api/watchlist").json()["items"]==[]
    finally:
        app.dependency_overrides.clear()
