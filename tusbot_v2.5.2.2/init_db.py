__file_version__ = "init_db.py@1"  # added 2025-08-30 18:21
import sqlite3

DB_FILE = "flights.db"

schema = """
CREATE TABLE IF NOT EXISTS flights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_key TEXT UNIQUE,
    from_city TEXT,
    to_city TEXT,
    depart_date TEXT,
    return_date TEXT,
    price INTEGER,
    seats INTEGER,
    url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    chat_id INTEGER PRIMARY KEY,
    created_at TEXT,
    last_seen_at TEXT,
    subscribed INTEGER
);

CREATE TABLE IF NOT EXISTS prefs (
    chat_id INTEGER,
    destinations_csv TEXT,
    max_price INTEGER,
    min_seats INTEGER,
    show_new INTEGER,
    show_active INTEGER,
    show_removed INTEGER,
    quiet_mode INTEGER,
    max_items INTEGER,
    show_active_time INTEGER,
    updated_at TEXT,
    FOREIGN KEY(chat_id) REFERENCES users(chat_id)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    event_type TEXT,
    payload TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS clicks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    flight_key TEXT,
    clicked_at TEXT
);
"""

if __name__ == "__main__":
    conn = sqlite3.connect(DB_FILE)
    conn.executescript(schema)
    conn.commit()
    conn.close()
    print("✅ DB initialized with all required columns:", DB_FILE)

