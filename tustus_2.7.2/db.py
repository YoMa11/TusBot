from __future__ import annotations
import sqlite3, logging, pathlib

def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_schema(conn: sqlite3.Connection):
    schema_path = pathlib.Path(__file__).with_name("schema.sql")
    sql = schema_path.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()
    logging.info("✅ DB schema ensured")

def get_distinct(conn: sqlite3.Connection, col: str) -> list[str]:
    q = f"SELECT DISTINCT {col} AS v FROM flights WHERE {col} IS NOT NULL AND {col}!='' ORDER BY 1"
    return [r["v"] for r in conn.execute(q)]

def get_price_ranges(conn: sqlite3.Connection):
    # מחזיר רשימת מחרוזות מחיר מקוריות (ערכים כפי שב-DB)
    q = "SELECT DISTINCT price_value, price_currency FROM flights WHERE price_value IS NOT NULL ORDER BY price_value"
    return [f"{r['price_value']:g} {r['price_currency']}" for r in conn.execute(q)]
