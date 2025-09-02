-- Flights & lookups (minimal schema)
CREATE TABLE IF NOT EXISTS flights (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  origin TEXT,
  destination TEXT,
  depart_date TEXT,
  arrive_date TEXT,
  airline TEXT,
  price_value REAL,
  price_currency TEXT,
  status TEXT DEFAULT 'active', -- active / removed
  url TEXT,
  seats INTEGER
);

CREATE INDEX IF NOT EXISTS idx_dest ON flights(destination);
CREATE INDEX IF NOT EXISTS idx_dates ON flights(depart_date, arrive_date);
CREATE INDEX IF NOT EXISTS idx_status ON flights(status);
