-- בסיס
CREATE TABLE IF NOT EXISTS show_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route TEXT,
    depart_time TEXT,
    arrive_time TEXT,
    price_text TEXT,
    currency TEXT,
    removed INTEGER DEFAULT 0,
    last_seen_at TEXT
);
