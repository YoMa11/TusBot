# --- file version marker ---
__file_version__ = "schema.sql@1"  # created 2025-08-29 22:59
-- schema.sql — מודל מלא
PRAGMA foreign_keys = ON;

-- טיסות
CREATE TABLE IF NOT EXISTS flights (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT,
    destination  TEXT,
    link         TEXT,
    price        INTEGER,
    go_date      TEXT,
    go_depart    TEXT,
    go_arrive    TEXT,
    back_date    TEXT,
    back_depart  TEXT,
    back_arrive  TEXT,
    seats        INTEGER,
    first_seen   TEXT,
    scraped_at   TEXT,
    flight_key   TEXT UNIQUE
);

-- שינויים בטיסות
CREATE TABLE IF NOT EXISTS flight_changes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_key  TEXT,
    changed_at  TEXT,
    field       TEXT,
    old_value   TEXT,
    new_value   TEXT
);

-- משתמשים
CREATE TABLE IF NOT EXISTS users (
    chat_id       INTEGER PRIMARY KEY,
    created_at    TEXT DEFAULT (datetime('now')),
    last_seen_at  TEXT,
    subscribed    INTEGER DEFAULT 1
);

-- העדפות משתמש
CREATE TABLE IF NOT EXISTS user_prefs (
    chat_id           INTEGER PRIMARY KEY,
    destinations_csv  TEXT,
    max_price         INTEGER,
    min_seats         INTEGER,
    min_days          INTEGER,
    max_days          INTEGER,
    date_start        TEXT,
    date_end          TEXT,
    show_new          INTEGER DEFAULT 1,
    show_active       INTEGER DEFAULT 1,
    show_removed      INTEGER DEFAULT 0,
    quiet_mode        INTEGER DEFAULT 0,
    max_items         INTEGER DEFAULT 7,
    show_active_time  INTEGER DEFAULT 0,
    updated_at        TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(chat_id) REFERENCES users(chat_id) ON DELETE CASCADE
);

-- לוגים כלליים
CREATE TABLE IF NOT EXISTS event_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id    INTEGER,
    event_type TEXT,
    payload    TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- קליקים על "הזמנה"
CREATE TABLE IF NOT EXISTS click_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     INTEGER,
    flight_key  TEXT,
    clicked_at  TEXT DEFAULT (datetime('now'))
);

-- אינדקסים
CREATE INDEX IF NOT EXISTS idx_flights_flight_key ON flights(flight_key);
CREATE INDEX IF NOT EXISTS idx_flights_scraped_at ON flights(scraped_at);
CREATE INDEX IF NOT EXISTS idx_changes_flight_key ON flight_changes(flight_key);
CREATE INDEX IF NOT EXISTS idx_users_chat_id ON users(chat_id);
CREATE INDEX IF NOT EXISTS idx_prefs_chat_id ON user_prefs(chat_id);
CREATE INDEX IF NOT EXISTS idx_event_logs_chat_id ON event_logs(chat_id);
CREATE INDEX IF NOT EXISTS idx_click_logs_chat_id ON click_logs(chat_id);

-- bookmarks table (saved flights)
CREATE TABLE IF NOT EXISTS saved_flights(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    flight_key TEXT NOT NULL,
    saved_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_saved_unique ON saved_flights(chat_id, flight_key);
