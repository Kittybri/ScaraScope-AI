"""Lightweight local ticker watchlist. No accounts/multi-tenant claims."""
import sqlite3
from pathlib import Path

def _connect(path: str):
    location=Path(path)
    location.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(str(location),timeout=8)
    db.execute("CREATE TABLE IF NOT EXISTS watched_tickers (ticker TEXT PRIMARY KEY, last_accession TEXT, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    return db

def add_watch(path: str, ticker: str):
    with _connect(path) as db:
        db.execute("INSERT OR IGNORE INTO watched_tickers (ticker) VALUES (?)",(ticker,))

def delete_watch(path: str, ticker: str):
    with _connect(path) as db:
        db.execute("DELETE FROM watched_tickers WHERE ticker=?",(ticker,))

def get_watches(path: str) -> list[dict]:
    with _connect(path) as db:
        return [{"ticker":r[0],"last_accession":r[1],"updated_at":r[2]} for r in db.execute(
            "SELECT ticker,last_accession,updated_at FROM watched_tickers ORDER BY ticker LIMIT 50").fetchall()]

def update_accession(path: str, ticker: str, accession: str) -> bool:
    with _connect(path) as db:
        before=db.execute("SELECT last_accession FROM watched_tickers WHERE ticker=?",(ticker,)).fetchone()
        if before is None:
            raise ValueError("Ticker is not on the watchlist.")
        changed=bool(before[0] and before[0]!=accession)
        db.execute("UPDATE watched_tickers SET last_accession=?,updated_at=CURRENT_TIMESTAMP WHERE ticker=?",(accession,ticker))
        return changed
