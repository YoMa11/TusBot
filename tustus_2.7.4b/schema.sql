-- schema.sql
CREATE TABLE IF NOT EXISTS show_item (
  id INTEGER PRIMARY KEY,
  destination TEXT NOT NULL,
  price REAL,
  currency TEXT,
  url TEXT,
  last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_show_item_dest ON show_item(destination);
