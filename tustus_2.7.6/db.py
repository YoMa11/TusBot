# db.py
from __future__ import annotations
import sqlite3
from typing import Optional
import time
import config

def get_conn(path: Optional[str] = None) -> sqlite3.Connection:
    db_path = path or config.DB_PATH
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_schema(conn: sqlite3.Connection) -> None:
    # טבלת flights מכסה את כל השדות בחוזה ה-HTML (ראה html_contract.html)
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;

        CREATE TABLE IF NOT EXISTS flights (
            id INTEGER PRIMARY KEY,
            item_id TEXT,
            selapp_item TEXT,
            category TEXT,
            provider TEXT,
            affiliation TEXT,
            promo_category TEXT,
            destination TEXT,
            dest_city TEXT,
            dest_country TEXT,
            trip_title TEXT,
            price REAL,
            currency TEXT,
            price_text TEXT,
            img_url TEXT,
            badge_text TEXT,

            out_from_city TEXT,
            out_from_date TEXT,
            out_from_time TEXT,
            out_to_city   TEXT,
            out_to_date   TEXT,
            out_to_time   TEXT,
            out_duration  TEXT,

            back_from_city TEXT,
            back_from_date TEXT,
            back_from_time TEXT,
            back_to_city   TEXT,
            back_to_date   TEXT,
            back_to_time   TEXT,
            back_duration  TEXT,

            note TEXT,
            more_like TEXT,
            url  TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(item_id, selapp_item)
        );

        CREATE INDEX IF NOT EXISTS ix_flights_city_country ON flights(dest_country, dest_city);
        CREATE INDEX IF NOT EXISTS ix_flights_last_seen    ON flights(last_seen);
        CREATE INDEX IF NOT EXISTS ix_flights_price        ON flights(price);
        """
    )
    conn.commit()

def touch_last_seen(conn: sqlite3.Connection, item_id: str, selapp_item: str) -> None:
    conn.execute(
        "UPDATE flights SET last_seen=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP "
        "WHERE item_id=? AND selapp_item=?",
        (item_id, selapp_item),
    )

def upsert_flight(conn: sqlite3.Connection, row: dict) -> None:
    # מפתח ייחודי: (item_id, selapp_item)
    cols = [
        "item_id","selapp_item","category","provider","affiliation","promo_category",
        "destination","dest_city","dest_country","trip_title","price","currency","price_text",
        "img_url","badge_text",
        "out_from_city","out_from_date","out_from_time","out_to_city","out_to_date","out_to_time","out_duration",
        "back_from_city","back_from_date","back_from_time","back_to_city","back_to_date","back_to_time","back_duration",
        "note","more_like","url"
    ]
    vals = [row.get(c) for c in cols]
    placeholders = ",".join("?" for _ in cols)
    set_expr = ",".join(f"{c}=excluded.{c}" for c in cols if c not in ("item_id","selapp_item"))
    sql = f"""
    INSERT INTO flights ({",".join(cols)})
    VALUES ({placeholders})
    ON CONFLICT(item_id, selapp_item)
    DO UPDATE SET {set_expr}, updated_at=CURRENT_TIMESTAMP, last_seen=CURRENT_TIMESTAMP
    """
    conn.execute(sql, vals)

def list_distinct_city_country(conn: sqlite3.Connection):
    # רשימת כל היעדים (גם כאלה שכבר לא באתר – ישבו בטבלה)
    return conn.execute(
        "SELECT DISTINCT COALESCE(dest_country,'') AS country, COALESCE(dest_city,'') AS city "
        "FROM flights "
        "WHERE TRIM(COALESCE(dest_city,'')) <> '' "
        "ORDER BY country, city"
    ).fetchall()
