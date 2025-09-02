-- Rebuilt schema based on new Arkia card structure
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS flights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,                 -- data_ga_item_id / ite_item
    selapp_item TEXT,                      -- ite_selappitem
    category TEXT,                         -- @category
    provider TEXT,                         -- data_ga_item_category4 (Arkia)
    affiliation TEXT,                      -- data_ga_affiliation
    promo_category TEXT,                   -- data_ga_item_category (e.g., "שעתיים גג...")
    destination TEXT,                      -- data_ga_item_name or con_desc (e.g., "אתונה - יוון")
    dest_city TEXT,
    dest_country TEXT,
    trip_title TEXT,                       -- .show_item_name (e.g., "טיסה לאתונה")
    price REAL,
    currency TEXT,                         -- "USD" / "ILS"
    price_text TEXT,                       -- "$150" / "₪300"
    img_url TEXT,
    badge_text TEXT,                       -- "5 מקומות אחרונים"
    out_from_city TEXT, out_from_time TEXT, out_from_date TEXT,
    out_to_city TEXT,   out_to_time TEXT,   out_to_date TEXT,
    out_duration TEXT,
    back_from_city TEXT, back_from_time TEXT, back_from_date TEXT,
    back_to_city TEXT,   back_to_time TEXT,   back_to_date TEXT,
    back_duration TEXT,
    note TEXT,                              -- flight_note
    more_like TEXT,                         -- "עוד טיסות ל..."
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uniq_hash TEXT,                         -- fingerprint of core fields for auditing
    UNIQUE(item_id, COALESCE(selapp_item,'')) ON CONFLICT DO UPDATE SET
        price=excluded.price,
        currency=excluded.currency,
        price_text=excluded.price_text,
        img_url=excluded.img_url,
        badge_text=excluded.badge_text,
        out_from_city=excluded.out_from_city,
        out_from_time=excluded.out_from_time,
        out_from_date=excluded.out_from_date,
        out_to_city=excluded.out_to_city,
        out_to_time=excluded.out_to_time,
        out_to_date=excluded.out_to_date,
        out_duration=excluded.out_duration,
        back_from_city=excluded.back_from_city,
        back_from_time=excluded.back_from_time,
        back_from_date=excluded.back_from_date,
        back_to_city=excluded.back_to_city,
        back_to_time=excluded.back_to_time,
        back_to_date=excluded.back_to_date,
        back_duration=excluded.back_duration,
        note=excluded.note,
        more_like=excluded.more_like,
        last_seen=CURRENT_TIMESTAMP,
        uniq_hash=excluded.uniq_hash
);
