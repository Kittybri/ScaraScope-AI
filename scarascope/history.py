"""Small, local metadata-only research history. No prompts, reports, or tokens stored."""
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


def _connect(db_path: str) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5)
    conn.execute("""CREATE TABLE IF NOT EXISTS research_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL,
        data_kind TEXT NOT NULL,
        provider TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    return conn


def add_history(db_path: str, ticker: str, data_kind: str, provider: str) -> None:
    with _connect(db_path) as conn:
        conn.execute("INSERT INTO research_history(ticker, data_kind, provider, created_at) VALUES(?,?,?,?)", (ticker, data_kind, provider, datetime.now(timezone.utc).isoformat()))


def list_history(db_path: str, limit: int = 25) -> list[dict[str, str]]:
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT ticker, data_kind, provider, created_at FROM research_history ORDER BY id DESC LIMIT ?", (min(max(limit, 1), 100),)).fetchall()
    return [dict(zip(("ticker", "data_kind", "provider", "created_at"), row)) for row in rows]
