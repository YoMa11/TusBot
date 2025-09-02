from __future__ import annotations
import sqlite3, pathlib, logging
log = logging.getLogger("tustus.db")

def open_db(path: str) -> sqlite3.Connection:
    p = pathlib.Path(path)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    log.info("📁 DB path: %s", str(p.resolve()))
    return conn

def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS show_item(id INTEGER PRIMARY KEY, title TEXT)")
    conn.commit()
    log.info("✅ DB schema ensured")
