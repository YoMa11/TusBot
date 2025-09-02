# -*- coding: utf-8 -*-
from __future__ import annotations
import sqlite3, logging, os, pathlib

log = logging.getLogger("tustus.db")

def connect_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_db(conn: sqlite3.Connection, schema_sql: str | None = None) -> None:
    if schema_sql:
        conn.executescript(schema_sql)
        conn.commit()
    # וידוא קיום טבלה
    conn.execute("""CREATE TABLE IF NOT EXISTS show_item (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        route TEXT,
        depart_time TEXT,
        arrive_time TEXT,
        price_text TEXT,
        currency TEXT,
        removed INTEGER DEFAULT 0,
        last_seen_at TEXT
    )""")
    conn.commit()

def get_destinations(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute("SELECT DISTINCT route FROM show_item ORDER BY route")
    return [r["route"] for r in cur.fetchall() if r["route"]]
