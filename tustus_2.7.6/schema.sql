-- flights table: אין שום ON CONFLICT כאן. רק סכימה נקייה.
CREATE TABLE IF NOT EXISTS flights (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id       TEXT,                 -- data-ga item id
  selapp_item   TEXT,                 -- ite_selappitem
  destination   TEXT NOT NULL,        -- "אתונה - יוון" / "טיסה לאתונה" מפורק בלוגיקה
  city          TEXT,
  country       TEXT,
  price         REAL,
  currency      TEXT,
  price_raw     TEXT,                 -- למשל "$150"
  url           TEXT,
  img_url       TEXT,
  last_spots    INTEGER,              -- "5 מקומות אחרונים" אם קיים
  depart_city   TEXT,
  depart_time   TEXT,
  depart_date   TEXT,
  arrive_city   TEXT,
  arrive_time   TEXT,
  arrive_date   TEXT,
  return_depart_city TEXT,
  return_depart_time TEXT,
  return_depart_date TEXT,
  return_arrive_city TEXT,
  return_arrive_time TEXT,
  return_arrive_date TEXT,
  duration_go   TEXT,                 -- "2:10"
  duration_back TEXT,                 -- "1:50"
  ga_currency   TEXT,                 -- data_ga_currency
  ga_brand      TEXT,                 -- data_ga_item_brand
  ga_category   TEXT,                 -- data_ga_item_category
  ga_category2  TEXT,                 -- data_ga_item_category2
  ga_category4  TEXT,                 -- data_ga_item_category4
  updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_seen     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- אינדקס ייחודי עבור UPSERT בקוד פייתון:
CREATE UNIQUE INDEX IF NOT EXISTS uq_flights_ids
  ON flights(item_id, selapp_item);
