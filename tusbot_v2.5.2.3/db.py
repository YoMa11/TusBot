# db.py — SQLite helpers, schema ensure & CRUD
from __future__ import annotations
__file_version__ = "db.py@1"  # added 2025-08-30 18:21
import sqlite3
import logging
from typing import Optional, Dict, Any, List

DB_PATH = "flights.db"

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS flights(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT,
  destination TEXT,
  link TEXT,
  price INTEGER,
  go_date TEXT,
  go_depart TEXT,
  go_arrive TEXT,
  back_date TEXT,
  back_depart TEXT,
  back_arrive TEXT,
  seats INTEGER,
  first_seen TEXT,
  scraped_at TEXT,
  flight_key TEXT
);

CREATE TABLE IF NOT EXISTS flight_changes(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  flight_key TEXT,
  changed_at TEXT,
  field TEXT,
  old_value TEXT,
  new_value TEXT
);

CREATE TABLE IF NOT EXISTS users(
  chat_id INTEGER PRIMARY KEY,
  created_at TEXT,
  last_seen_at TEXT,
  subscribed INTEGER
);

CREATE TABLE IF NOT EXISTS user_prefs(
  chat_id INTEGER PRIMARY KEY,
  destinations_csv TEXT,
  max_price INTEGER,
  min_seats INTEGER,
  min_days INTEGER,
  max_days INTEGER,
  date_start TEXT,
  date_end TEXT,
  show_new INTEGER,
  show_active INTEGER,
  show_removed INTEGER,
  quiet_mode INTEGER,
  max_items INTEGER,
  show_active_time INTEGER,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS event_logs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id INTEGER,
  event_type TEXT,
  payload TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS saved_flights(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id INTEGER,
  flight_key TEXT,
  saved_at TEXT,
  UNIQUE(chat_id, flight_key)
);

CREATE TABLE IF NOT EXISTS click_logs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id INTEGER,
  flight_key TEXT,
  clicked_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_flights_flight_key ON flights(flight_key);
CREATE INDEX IF NOT EXISTS idx_flights_scraped_at ON flights(scraped_at);
CREATE INDEX IF NOT EXISTS idx_users_chat_id ON users(chat_id);
CREATE INDEX IF NOT EXISTS idx_prefs_chat_id ON user_prefs(chat_id);
CREATE INDEX IF NOT EXISTS idx_logs_chat_id ON event_logs(chat_id);
"""

def ensure_schema(conn: sqlite3.Connection) -> None:
    """ווידוא סכימה מלאה – בטוח להרצה חוזרת."""
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        logging.info("✅ DB schema ensured")
    except Exception:
        logging.exception("ensure_schema failed")

def _ensure_event_logs(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS event_logs(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      chat_id INTEGER,
      event_type TEXT,
      payload TEXT,
      created_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_logs_chat_id ON event_logs(chat_id);
    """)
    conn.commit()

def log_event(conn: sqlite3.Connection, chat_id: int, event_type: str, payload: str) -> None:
    """רישום אירוע עם הקשחה: יוודא event_logs ואז יכניס. ריטריי על OperationalError."""
    try:
        _ensure_event_logs(conn)
        conn.execute(
            "INSERT INTO event_logs(chat_id, event_type, payload, created_at) VALUES(?,?,?,datetime('now'))",
            (chat_id, event_type, payload),
        )
        conn.commit()
    except sqlite3.OperationalError:
        try:
            _ensure_event_logs(conn)
            conn.execute(
                "INSERT INTO event_logs(chat_id, event_type, payload, created_at) VALUES(?,?,?,datetime('now'))",
                (chat_id, event_type, payload),
            )
            conn.commit()
        except Exception as e2:
            logging.warning(f"⚠️ רישום event_logs נכשל לאחר ריטריי: {e2}")
    except Exception as e:
        logging.warning(f"⚠️ רישום event_logs נכשל: {e}")

# ===== CRUD minimal required by handlers/logic =====

def upsert_user(conn: sqlite3.Connection, chat_id: int) -> None:
    ensure_schema(conn)
    # אם לא קיים – יצירה; אם קיים – עדכון last_seen_at
    cur = conn.execute("SELECT chat_id FROM users WHERE chat_id=?", (chat_id,))
    if cur.fetchone() is None:
        conn.execute(
            "INSERT INTO users(chat_id, created_at, last_seen_at, subscribed) "
            "VALUES(?, datetime('now'), datetime('now'), 1)",
            (chat_id,),
        )
    else:
        conn.execute("UPDATE users SET last_seen_at=datetime('now') WHERE chat_id=?", (chat_id,))
    conn.commit()

def get_user_prefs(conn: sqlite3.Connection, chat_id: int) -> Optional[Dict[str, Any]]:
    ensure_schema(conn)
    cur = conn.execute("SELECT * FROM user_prefs WHERE chat_id=?", (chat_id,))
    row = cur.fetchone()
    if not row:
        return None
    if isinstance(row, sqlite3.Row):
        return {k: row[k] for k in row.keys()}
    # tuple fallback
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))

def set_user_prefs(conn: sqlite3.Connection, chat_id: int, prefs: Dict[str, Any]) -> None:
    ensure_schema(conn)
    # בונים upsert ידני
    existing = get_user_prefs(conn, chat_id)
    fields = [
        "destinations_csv", "max_price", "min_seats", "min_days", "max_days",
        "date_start", "date_end", "show_new", "show_active", "show_removed",
        "quiet_mode", "max_items", "show_active_time", "updated_at"
    ]
    payload = {k: prefs.get(k) for k in fields}
    payload["updated_at"] = payload.get("updated_at") or None
    if existing is None:
        conn.execute(
            "INSERT INTO user_prefs(chat_id, destinations_csv, max_price, min_seats, min_days, max_days, "
            "date_start, date_end, show_new, show_active, show_removed, quiet_mode, max_items, show_active_time, updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))",
            (chat_id,
             payload["destinations_csv"], payload["max_price"], payload["min_seats"], payload["min_days"], payload["max_days"],
             payload["date_start"], payload["date_end"], payload["show_new"], payload["show_active"], payload["show_removed"],
             payload["quiet_mode"], payload["max_items"], payload["show_active_time"]),
        )
    else:
        conn.execute(
            "UPDATE user_prefs SET destinations_csv=?, max_price=?, min_seats=?, min_days=?, max_days=?, "
            "date_start=?, date_end=?, show_new=?, show_active=?, show_removed=?, quiet_mode=?, max_items=?, "
            "show_active_time=?, updated_at=datetime('now') WHERE chat_id=?",
            (payload["destinations_csv"], payload["max_price"], payload["min_seats"], payload["min_days"], payload["max_days"],
             payload["date_start"], payload["date_end"], payload["show_new"], payload["show_active"], payload["show_removed"],
             payload["quiet_mode"], payload["max_items"], payload["show_active_time"], chat_id),
        )
    conn.commit()

def list_all_destinations(conn: sqlite3.Connection) -> List[str]:
    ensure_schema(conn)
    try:
        cur = conn.execute("SELECT DISTINCT destination FROM flights WHERE destination IS NOT NULL AND TRIM(destination)!='' ORDER BY destination COLLATE NOCASE")
        return [r[0] for r in cur.fetchall()]
    except Exception:
        return []

# עזר לקליקים (לא חובה; לשימוש עתידי)
def log_click(conn: sqlite3.Connection, chat_id: int, flight_key: str) -> None:
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO click_logs(chat_id, flight_key, clicked_at) VALUES(?,?,datetime('now'))",
        (chat_id, flight_key),
    )
    conn.commit()

# --- appended by fix: reset_user_prefs ---
import logging

def reset_user_prefs(conn, chat_id: int) -> None:
    """
    מאפס העדפות משתמש:
    - מוחק את הרשומה מ-user_prefs עבור chat_id
    - כותב event_logs (אם הטבלה קיימת)
    """
    try:
        with conn:
            conn.execute("DELETE FROM user_prefs WHERE chat_id=?", (chat_id,))
        try:
            # אם יש פונקציית לוגינג של אירועים, נשתמש בה; אחרת נתעלם בשקט
            from db import log_event as _log_event  # self-import תקין כאן
            _log_event(conn, chat_id, "prefs_reset", "{}")
        except Exception:
            pass
    except Exception:
        logging.exception("reset_user_prefs failed")
# --- end appended by fix ---


# ==== saved flights helpers ====
def save_flight(conn: sqlite3.Connection, chat_id: int, flight_key: str) -> bool:
    """Save a flight for a user. Returns True if inserted, False if existed."""
    ensure_schema(conn)
    try:
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO saved_flights(chat_id, flight_key, saved_at) VALUES(?,?,datetime('now'))",
                (chat_id, flight_key)
            )
        cur = conn.execute("SELECT changes()")
        return cur.fetchone()[0] > 0
    except Exception:
        return False

def unsave_flight(conn: sqlite3.Connection, chat_id: int, flight_key: str) -> bool:
    ensure_schema(conn)
    with conn:
        conn.execute("DELETE FROM saved_flights WHERE chat_id=? AND flight_key=?", (chat_id, flight_key))
    return True

def is_saved(conn: sqlite3.Connection, chat_id: int, flight_key: str) -> bool:
    ensure_schema(conn)
    cur = conn.execute("SELECT 1 FROM saved_flights WHERE chat_id=? AND flight_key=? LIMIT 1", (chat_id, flight_key))
    return cur.fetchone() is not None

def list_saved_flights(conn: sqlite3.Connection, chat_id: int) -> List[str]:
    ensure_schema(conn)
    cur = conn.execute("SELECT flight_key FROM saved_flights WHERE chat_id=? ORDER BY saved_at DESC", (chat_id,))
    return [r[0] for r in cur.fetchall()]


def get_flights_by_keys(conn: sqlite3.Connection, keys: List[str]) -> List[Dict[str, Any]]:
    """Return flight rows (dicts) by a list of flight_key values, newest first."""
    ensure_schema(conn)
    if not keys:
        return []
    qmarks = ",".join("?" for _ in keys)
    cur = conn.execute(f"SELECT * FROM flights WHERE flight_key IN ({qmarks}) ORDER BY scraped_at DESC", keys)
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r.setdefault("link", "https://www.tustus.co.il/Arkia/Home")
    return rows



def toggle_saved(conn, chat_id: int, flight_key: str) -> bool:
    """Toggle bookmark for user/flight_key. Returns True if now saved, False if removed."""
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM saved_flights WHERE chat_id=? AND flight_key=?", (chat_id, flight_key))
    if cur.fetchone():
        cur.execute("DELETE FROM saved_flights WHERE chat_id=? AND flight_key=?", (chat_id, flight_key))
        conn.commit()
        return False
    cur.execute("INSERT OR IGNORE INTO saved_flights(chat_id, flight_key, saved_at) VALUES(?,?,datetime('now'))", (chat_id, flight_key))
    conn.commit()
    return True

def get_saved_flights(conn, chat_id: int):
    cur = conn.cursor()
    try:
        cur.execute("""

            SELECT f.*

            FROM saved_flights s

            LEFT JOIN flights f ON f.flight_key = s.flight_key

            WHERE s.chat_id=?

            ORDER BY s.saved_at DESC

        """, (chat_id,))
        rows = [dict(r) for r in cur.fetchall()]
    except Exception:
        cur.execute("SELECT * FROM saved_flights WHERE chat_id=? ORDER BY saved_at DESC", (chat_id,))
        rows = [dict(r) for r in cur.fetchall()]
    return rows


def cleanup_invalid_prices(conn: sqlite3.Connection) -> int:
    """Remove obvious garbage prices from old runs (e.g., 0/1/26 from date parsing)."""
    cur = conn.execute("SELECT COUNT(*) FROM flights WHERE price IS NOT NULL AND price < 50")
    before = int(cur.fetchone()[0])
    conn.execute("DELETE FROM flights WHERE price IS NOT NULL AND price < 50")
    conn.commit()
    logging.info("🧹 cleaned invalid prices (<50): %s", before)
    return before
