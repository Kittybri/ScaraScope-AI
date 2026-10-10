from pathlib import Path
from fastapi.testclient import TestClient
from scarascope.api import app, get_settings
from scarascope.core.config import Settings


def test_demo_and_browser_without_keys(tmp_path: Path):
    app.dependency_overrides[get_settings] = lambda: Settings(ollama_enabled=False, groq_api_key="", history_db_path=str(tmp_path / "hist.sqlite"))
    try:
        with TestClient(app) as client:
            assert client.get("/").status_code == 200
            assert client.get("/api/health").json()["status"] == "ok"
            res = client.get("/api/demo")
            assert res.status_code == 200
            data = res.json()
            assert data["data_kind"] == "synthetic_demo"
            assert data["llm"]["provider"] == "deterministic"
            assert data["financials"][0]["revenue"] == 128000000
            assert data["financials"][0]["sources"] == []
            assert client.post("/api/research", json={"ticker": "DEMO"}).status_code == 200
            history = client.get("/api/history").json()["items"]
            assert len(history) == 1 and history[0]["ticker"] == "DEMO"
    finally:
        app.dependency_overrides.clear()


def test_api_auth_and_privacy_enforced(tmp_path: Path):
    app.dependency_overrides[get_settings] = lambda: Settings(app_api_key="super-secret", history_db_path=str(tmp_path / "hist.sqlite"))
    try:
        with TestClient(app) as client:
            assert client.post("/api/research", json={"ticker": "DEMO"}).status_code == 401
            assert client.get("/api/history").status_code == 401
            headers={"X-API-Key": "super-secret"}
            assert client.post("/api/research", headers=headers, json={"ticker": "DEMO", "provider": "cloud", "privacy": "local_only"}).status_code == 400
            assert client.post("/api/research", headers=headers, json={"ticker": "DEMO"}).status_code == 200
    finally:
        app.dependency_overrides.clear()
