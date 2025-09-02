PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA legacy_alter_table=ON;

CREATE TABLE IF NOT EXISTS flights_new (
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

    back_from_city TEXT,
    back_from_date TEXT,
    back_from_time TEXT,
    back_to_city   TEXT,
    back_to_date   TEXT,
    back_to_time   TEXT,

    note TEXT,
    more_like TEXT,
    url TEXT,

    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(item_id, selapp_item)
);

INSERT INTO flights_new(destination, price, currency, url, last_seen, created_at, updated_at, is_active)
SELECT destination, price, currency, url, last_seen, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1
FROM flights;

DROP TABLE flights;
ALTER TABLE flights_new RENAME TO flights;

CREATE INDEX IF NOT EXISTS idx_flights_dest ON flights(dest_city, dest_country);
CREATE INDEX IF NOT EXISTS idx_flights_last_seen ON flights(last_seen);
CREATE INDEX IF NOT EXISTS idx_flights_active ON flights(is_active);
