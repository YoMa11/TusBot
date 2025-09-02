from __future__ import annotations
import sqlite3, time, logging, os, pathlib

__file_version__ = "tustus_2.7.4a"

log = logging.getLogger("tustus.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS show_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    destination TEXT NOT NULL,
    price REAL,
    currency TEXT,
    url TEXT,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_show_item_dest ON show_item(destination);
"""

def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
    log.info("✅ DB schema ensured")

def upsert_show_item(conn: sqlite3.Connection, destination: str, price: float|None, currency: str|None, url: str|None) -> None:
    conn.execute(
        """
        INSERT INTO show_item(destination, price, currency, url, last_seen)
        VALUES(?,?,?,?,CURRENT_TIMESTAMP)
        """,
        (destination, price, currency, url)
    )
    conn.commit()

def get_destinations(conn: sqlite3.Connection, limit: int = 50) -> list[tuple[str,int]]:
    cur = conn.execute("""
        SELECT destination, COUNT(*) as c
        FROM show_item
        GROUP BY destination
        ORDER BY c DESC, destination ASC
        LIMIT ?
    """, (limit,))
    return [(r["destination"], r["c"]) for r in cur]

def get_price_buckets(conn: sqlite3.Connection) -> dict[str,int]:
    cur = conn.execute("""
        SELECT COALESCE(currency,'?') as cur, COUNT(*) as c
        FROM show_item
        GROUP BY COALESCE(currency,'?')
    """)
    return {r["cur"]: r["c"] for r in cur}

def get_counts(conn: sqlite3.Connection) -> dict[str,int]:
    cur = conn.execute("SELECT COUNT(*) as c FROM show_item")
    total = cur.fetchone()["c"]
    # naive "new" window: last 24h
    cur = conn.execute("SELECT COUNT(*) as c FROM show_item WHERE last_seen >= datetime('now','-24 hours')")
    fresh = cur.fetchone()["c"]
    return {"total": total, "fresh_24h": fresh}
