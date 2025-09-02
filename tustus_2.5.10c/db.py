# -*- coding: utf-8 -*-
from __future__ import annotations
import sqlite3, logging

SCHEMA = """
CREATE TABLE IF NOT EXISTS flights (
  id TEXT PRIMARY KEY,
  origin TEXT,
  dest TEXT,
  depart_ts INTEGER,
  arrive_ts INTEGER,
  price_amount REAL,
  price_currency TEXT,
  seats INTEGER,
  status TEXT
);
"""

def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute(SCHEMA)
    logging.info("✅ DB schema ensured")
    return conn
