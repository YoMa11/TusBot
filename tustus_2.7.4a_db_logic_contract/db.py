from __future__ import annotations
import sqlite3, pathlib

SCHEMA_FILE = pathlib.Path(__file__).with_name("schema.sql")

def get_conn(db_path: str = "./flights.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    return conn

def ensure_schema(conn: sqlite3.Connection) -> None:
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()

def upsert_items(conn: sqlite3.Connection, items: list[dict]) -> tuple[int,int]:
    """
    Insert or update items into flights table.
    Returns: (inserted, updated)
    """
    inserted = 0; updated = 0
    q = """
    INSERT INTO flights (
      item_id, selapp_item, category, provider, affiliation, promo_category,
      destination, dest_city, dest_country, trip_title, price, currency, price_text,
      img_url, badge_text,
      out_from_city, out_from_time, out_from_date,
      out_to_city, out_to_time, out_to_date, out_duration,
      back_from_city, back_from_time, back_from_date,
      back_to_city, back_to_time, back_to_date, back_duration,
      note, more_like, uniq_hash
    ) VALUES (
      :item_id, :selapp_item, :category, :provider, :affiliation, :promo_category,
      :destination, :dest_city, :dest_country, :trip_title, :price, :currency, :price_text,
      :img_url, :badge_text,
      :out_from_city, :out_from_time, :out_from_date,
      :out_to_city, :out_to_time, :out_to_date, :out_duration,
      :back_from_city, :back_from_time, :back_from_date,
      :back_to_city, :back_to_time, :back_to_date, :back_duration,
      :note, :more_like, :uniq_hash
    )
    ON CONFLICT(item_id, COALESCE(selapp_item,'')) DO UPDATE SET
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
    """
    cur = conn.cursor()
    for row in items:
        before = conn.execute("SELECT 1 FROM flights WHERE item_id=? AND COALESCE(selapp_item,'')=COALESCE(?, '')",
                              (row.get("item_id"), row.get("selapp_item"))).fetchone()
        cur.execute(q, row)
        inserted += (0 if before else 1)
        updated  += (1 if before else 0)
    conn.commit()
    return inserted, updated

def top_counts_by_currency(conn: sqlite3.Connection) -> dict[str,int]:
    d = {}
    for curr, cnt in conn.execute("SELECT currency, COUNT(*) FROM flights GROUP BY currency"):
        d[curr or ""] = cnt
    return d
