#!/usr/bin/env bash
set -euo pipefail

# usage: ./apply_release_2_4_7.sh /full/path/to/tusbot_v2.4.6.zip
SRC_ZIP="${1:-tusbot_v2.4.6.zip}"
[[ -f "$SRC_ZIP" ]] || { echo "❌ not found: $SRC_ZIP"; exit 1; }

WORK="$(mktemp -d)"
STAGE_NAME="tusbot_v2.4.7"
STAGE="$WORK/$STAGE_NAME"

unzip -q "$SRC_ZIP" -d "$WORK"
# detect inner root
if [[ $(find "$WORK" -mindepth 1 -maxdepth 1 -type d | wc -l) -eq 1 ]] && \
   [[ $(find "$WORK" -mindepth 1 -maxdepth 1 -type f | wc -l) -eq 0 ]]; then
  SRC_ROOT="$(find "$WORK" -mindepth 1 -maxdepth 1 -type d)"
else
  SRC_ROOT="$WORK"
fi
cp -a "$SRC_ROOT"/ "$STAGE"

_write() { mkdir -p "$(dirname "$STAGE/$1")"; cat > "$STAGE/$1"; }

# -------- files with running version header @@file_version: v2.4.7 --------
_write config.py <<'PY'
# @@file_version: v2.4.7
"""Runtime configuration for tusbot."""
BOT_TOKEN = "PUT_YOUR_TELEGRAM_BOT_TOKEN_HERE"
DB_FILE = "tustus.db"
INTERVAL = 900
LOG_LEVEL = "INFO"
PY

_write db.py <<'PY'
# @@file_version: v2.4.7
from __future__ import annotations
import sqlite3

def ensure_user(conn: sqlite3.Connection, chat_id: int):
    conn.execute("""
      CREATE TABLE IF NOT EXISTS users(
        chat_id INTEGER PRIMARY KEY,
        created_at TEXT DEFAULT (datetime('now')),
        last_seen_at TEXT DEFAULT (datetime('now')),
        subscribed INTEGER DEFAULT 1
      )""")
    conn.execute("""
      CREATE TABLE IF NOT EXISTS user_prefs(
        chat_id INTEGER PRIMARY KEY,
        destinations_csv TEXT DEFAULT '',
        max_price INTEGER,
        min_seats INTEGER DEFAULT 1,
        min_days INTEGER,
        max_days INTEGER,
        date_start TEXT,
        date_end TEXT,
        show_new INTEGER DEFAULT 1,
        show_active INTEGER DEFAULT 1,
        show_removed INTEGER DEFAULT 0,
        quiet_mode INTEGER DEFAULT 0,
        max_items INTEGER DEFAULT 30,
        show_active_time INTEGER DEFAULT 1,
        updated_at TEXT DEFAULT (datetime('now'))
      )""")
    conn.execute("""
      CREATE TABLE IF NOT EXISTS saved_flights(
        chat_id INTEGER NOT NULL,
        flight_key TEXT NOT NULL,
        saved_at TEXT DEFAULT (datetime('now')),
        PRIMARY KEY(chat_id, flight_key)
      )""")
    conn.commit()

def ensure_schema(conn: sqlite3.Connection):
    for sql in [
        "ALTER TABLE flights ADD COLUMN status TEXT DEFAULT 'active'",
        "ALTER TABLE flights ADD COLUMN currency TEXT",
        "ALTER TABLE flights ADD COLUMN price_text TEXT",
    ]:
        try: conn.execute(sql)
        except Exception: pass
    conn.commit()

def ensure_price_catalog(conn: sqlite3.Connection):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS price_catalog(
      currency  TEXT NOT NULL,
      value     INTEGER NOT NULL,
      first_seen TEXT DEFAULT (datetime('now')),
      last_seen  TEXT DEFAULT (datetime('now')),
      PRIMARY KEY(currency, value)
    )""")
    conn.execute("""
      INSERT OR IGNORE INTO price_catalog(currency, value)
      SELECT
        COALESCE(currency,
                 CASE WHEN instr(COALESCE(price_text,''),'$')>0 THEN 'USD' ELSE 'ILS' END),
        price
      FROM flights
      WHERE price IS NOT NULL
    """)
    conn.execute("""
      UPDATE price_catalog
         SET last_seen = datetime('now')
       WHERE (currency,value) IN (
             SELECT COALESCE(currency,
                              CASE WHEN instr(COALESCE(price_text,''),'$')>0 THEN 'USD' ELSE 'ILS' END),
                    price
               FROM flights
              WHERE price IS NOT NULL)
    """)
    conn.commit()

def get_price_catalog(conn: sqlite3.Connection):
    ensure_price_catalog(conn)
    cur = conn.execute("""
      SELECT currency, value
        FROM price_catalog
    ORDER BY (currency='ILS') DESC, value ASC
    """)
    out = []
    for c, v in cur.fetchall():
        sym = "$" if (c or "").upper() == "USD" else "₪"
        out.append(f"{v}{sym}")
    return out

def toggle_saved(conn: sqlite3.Connection, chat_id: int, flight_key: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM saved_flights WHERE chat_id=? AND flight_key=?",
        (chat_id, flight_key))
    if cur.fetchone():
        conn.execute("DELETE FROM saved_flights WHERE chat_id=? AND flight_key=?",
                     (chat_id, flight_key))
        conn.commit()
        return False
    conn.execute("INSERT OR IGNORE INTO saved_flights(chat_id, flight_key) VALUES(?,?)",
                 (chat_id, flight_key))
    conn.commit()
    return True

def get_saved_flights(conn: sqlite3.Connection, chat_id: int):
    conn.row_factory = sqlite3.Row
    cur = conn.execute("""
        SELECT f.*
          FROM saved_flights s
          JOIN flights f ON f.flight_key = s.flight_key
         WHERE s.chat_id=?
      ORDER BY datetime(COALESCE(f.scraped_at, f.first_seen, '1970-01-01T00:00:00')) DESC
         LIMIT 200
    """, (chat_id,))
    return [dict(r) for r in cur.fetchall()]
PY

_write telegram_view.py <<'PY'
# @@file_version: v2.4.7
from __future__ import annotations
import html, math
from typing import List
from datetime import datetime
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from db import get_price_catalog

def _center_title(txt: str) -> str:
    return f"<b>{html.escape(txt)}</b>"

def main_menu_kb():
    rows = [
        [InlineKeyboardButton("כל הטיסות 🔎", callback_data="SHOW_ALL"),
         InlineKeyboardButton("לפי העדפות 🎯", callback_data="BY_PREFS"),
         InlineKeyboardButton("שמורים ⭐", callback_data="SAVED")],
        [InlineKeyboardButton("יעדים 🎯", callback_data="DESTS"),
         InlineKeyboardButton("מחיר 💸", callback_data="PRICE"),
         InlineKeyboardButton("מושבים 🪑", callback_data="SEATS")],
        [InlineKeyboardButton("תאריכים 🗓", callback_data="DATES"),
         InlineKeyboardButton("אורך טיול 🧾", callback_data="TRIP"),
         InlineKeyboardButton("נראות 👀", callback_data="VIS")],
        [InlineKeyboardButton("סיכום לפי יעד 📊", callback_data="SUMMARY"),
         InlineKeyboardButton("מצב שקט 🔕", callback_data="QUIET_TOGGLE"),
         InlineKeyboardButton("איפוס ♻️", callback_data="RESET")],
        [InlineKeyboardButton("בית 🏠", callback_data="HOME")]
    ]
    return InlineKeyboardMarkup(rows)

def feed_nav_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("בית 🏠", callback_data="HOME"),
                                  InlineKeyboardButton("לפי העדפות 🎯", callback_data="BY_PREFS"),
                                  InlineKeyboardButton("שמורים ⭐", callback_data="SAVED")]])

def _truncate(s: str, n: int = 18) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"

def destinations_page(selected_csv: str, page: int, per_page: int, all_dests: List[str]):
    selected = set(d.strip() for d in (selected_csv or "").split(",") if d.strip())
    all_sorted = sorted(all_dests, key=lambda x: x)
    import math as _m
    total_pages = max(1, _m.ceil(len(all_sorted) / per_page))
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    chunk = all_sorted[start : start + per_page]

    rows = [[InlineKeyboardButton("🟩 הכל", callback_data="DEST_ALL_TOGGLE"),
             InlineKeyboardButton("שמור וחזור ✅", callback_data="DEST_SAVE")]]

    row = []
    for d in chunk:
        mark = "✅ " if d in selected else "⬜️ "
        row.append(InlineKeyboardButton(f"{mark}{_truncate(d)}", callback_data=f"DEST_TOGGLE::{d}|PAGE_{page}"))
        if len(row) == 3:
            rows.append(row); row = []
    if row: rows.append(row)

    rows.append([InlineKeyboardButton(f"{page}/{total_pages}", callback_data="DESTS_NOP")])
    rows.append([InlineKeyboardButton("בית 🏠", callback_data="HOME")])
    return InlineKeyboardMarkup(rows)

def price_menu_kb(prefs, conn=None):
    try: values = get_price_catalog(conn) if conn else []
    except Exception: values = []
    if not values:
        values = ["100$","150$","300$","200₪"]
    rows, row = [], []
    for p in values:
        row.append(InlineKeyboardButton(p, callback_data=f"PRICE_SET_{p}"))
        if len(row) == 4:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("נקה", callback_data="PRICE_CLEAR"),
                 InlineKeyboardButton("בית 🏠", callback_data="HOME")])
    return InlineKeyboardMarkup(rows)

def seats_menu_kb(prefs):
    rows = [[InlineKeyboardButton(str(n), callback_data=f"SEATS_SET_{n}") for n in [1,2,3,4,5]]]
    rows.append([InlineKeyboardButton("נקה", callback_data="SEATS_CLEAR"),
                 InlineKeyboardButton("בית 🏠", callback_data="HOME")])
    return InlineKeyboardMarkup(rows)

def dates_menu_kb():
    rows = [[InlineKeyboardButton("שבוע קדימה", callback_data="DATES_WEEK"),
             InlineKeyboardButton("חודש קדימה", callback_data="DATES_MONTH")],
            [InlineKeyboardButton("נקה", callback_data="DATES_CLEAR"),
             InlineKeyboardButton("בית 🏠", callback_data="HOME")]]
    return InlineKeyboardMarkup(rows)

def trip_len_menu_kb():
    opts = ["2-3","3-4","4-5","5-7","7-10","10-14"]
    rows, row = [], []
    for o in opts:
        row.append(InlineKeyboardButton(o, callback_data=f"TRIP_SET_{o}"))
        if len(row)==3: rows.append(row); row=[]
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("נקה", callback_data="TRIP_CLEAR"),
                 InlineKeyboardButton("בית 🏠", callback_data="HOME")])
    return InlineKeyboardMarkup(rows)

def visibility_menu_kb(prefs):
    def box(flag): return "✅" if int(prefs.get(flag) or 0) else "⬜️"
    rows = [[InlineKeyboardButton(f"חדשים {box('show_new')}", callback_data="VIS_TOGGLE_NEW"),
             InlineKeyboardButton(f"פעילים {box('show_active')}", callback_data="VIS_TOGGLE_ACTIVE")],
            [InlineKeyboardButton(f"הוסרו {box('show_removed')}", callback_data="VIS_TOGGLE_REMOVED"),
             InlineKeyboardButton("בית 🏠", callback_data="HOME")]]
    return InlineKeyboardMarkup(rows)

FLAGS = {"יוון":"🇬🇷","קפריסין":"🇨🇾","ספרד":"🇪🇸","מונטנגרו":"🇲🇪","גאורגיה":"🇬🇪",
         "איטליה":"🇮🇹","צרפת":"🇫🇷","פורטוגל":"🇵🇹","רודוס":"🇬🇷","כרתים":"🇬🇷",
         "קורפו":"🇬🇷","אתונה":"🇬🇷"}
def flag_for(dest: str) -> str:
    for k,v in FLAGS.items():
        if k in (dest or ""): return v
    return "🌍"

def _arrow(a: str, b: str) -> str:
    try:
        t1 = datetime.strptime(a, "%H:%M"); t2 = datetime.strptime(b, "%H:%M")
        return "→" if t2 >= t1 else "←"
    except Exception:
        return "→"

def _fmt_price_raw(f: dict) -> str:
    if f.get("price_text"): return f["price_text"]
    v = f.get("price")
    if v is None: return "—"
    sym = "$" if (f.get("currency") or "").upper()=="USD" else "₪"
    return f"{v}{sym}"

def _fmt_seats(f: dict) -> str:
    s = f.get("seats"); return str(s) if s else "🎟️?"

def _age_text(f: dict) -> str:
    fs = f.get("first_seen") or f.get("scraped_at")
    if not fs: return ""
    try:
        from datetime import datetime as _dt
        dt = _dt.fromisoformat(fs)
    except Exception:
        return ""
    delta = datetime.utcnow() - dt
    h = delta.days*24 + delta.seconds//3600
    m = (delta.seconds%3600)//60
    return f"⏱ פעילה: {h} שע' {m} דק'"

def format_flight_card(f: dict, show_removed: bool=False) -> str:
    removed = (f.get("status") == "removed") or show_removed
    dest = (f.get("destination") or f.get("name") or "יעד").strip()
    url  = f.get("link") or "#"
    go_d, go_t1, go_t2 = f.get("go_date") or "", f.get("go_depart") or "", f.get("go_arrive") or ""
    bk_d, bk_t1, bk_t2 = f.get("back_date") or "", f.get("back_depart") or "", f.get("back_arrive") or ""
    arr1, arr2 = _arrow(go_t1, go_t2), _arrow(bk_t1, bk_t2)
    price, seats, age = _fmt_price_raw(f), _fmt_seats(f), _age_text(f)
    badge_removed = "  <b>🚫 הוסר</b>" if removed else ""
    line1 = f"<b><a href=\"{html.escape(url)}\">{html.escape(dest)}</a></b>{badge_removed} 🌍"
    line2 = f"{go_t1} {arr1} {go_t2} · {go_d}"
    line3 = f"{bk_t1} {arr2} {bk_t2} · {bk_d}"
    line4 = f"— מושבים: {seats}  ·  מחיר: {price}  🪙"
    line5 = age
    return "\n".join([line1, line2, line3, line4, line5])

MAX_TG = 4000
def chunk_messages(cards: List[str], header: str=""):
    out, cur = [], (header.strip()+"\n\n" if header else "")
    for c in cards:
        block = (c.strip()+"\n\n")
        if len(cur)+len(block) > MAX_TG:
            out.append(cur.rstrip()); cur = ""
        cur += block
    if cur.strip(): out.append(cur.rstrip())
    return out

def paginate_cards(flights: List[dict], prefs: dict, page: int=1, page_size: int=10, show_active_time: bool=True):
    cards = [format_flight_card(f) for f in flights]
    total = max(1, math.ceil(len(cards)/page_size))
    page = max(1, min(page, total))
    start = (page-1)*page_size
    chunk = cards[start:start+page_size]
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀️", callback_data=f"PAGE_{page-1}" if page>1 else "NOP"),
                                InlineKeyboardButton(f"{page}/{total}", callback_data="NOP"),
                                InlineKeyboardButton("▶️", callback_data=f"PAGE_{page+1}" if page<total else "NOP")]])
    return chunk, kb, page, total
PY

_write handlers.py <<'PY'
# @@file_version: v2.4.7
from __future__ import annotations
import re, sqlite3, html
from datetime import datetime, timedelta
from typing import List, Dict, Any
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from db import toggle_saved, get_saved_flights, ensure_user
from telegram_view import (
    main_menu_kb, destinations_page, price_menu_kb, seats_menu_kb, dates_menu_kb,
    trip_len_menu_kb, visibility_menu_kb, feed_nav_kb, format_flight_card,
    chunk_messages, paginate_cards, _center_title, flag_for
)

def _row_to_dict(r: sqlite3.Row) -> Dict[str, Any]:
    return {k: r[k] for k in r.keys()}

def get_prefs(conn: sqlite3.Connection, chat_id: int) -> Dict[str, Any]:
    r = conn.execute("SELECT * FROM user_prefs WHERE chat_id=?", (chat_id,)).fetchone()
    return _row_to_dict(r) if r else {}

def update_prefs(conn: sqlite3.Connection, chat_id: int, **fields):
    if not fields: return
    sets = ", ".join([f"{k}=?" for k in fields])
    params = list(fields.values()) + [chat_id]
    conn.execute(f"UPDATE user_prefs SET {sets}, updated_at=datetime('now') WHERE chat_id=?", params)
    conn.commit()

def reset_prefs(conn: sqlite3.Connection, chat_id: int):
    conn.execute("""
      UPDATE user_prefs SET
        destinations_csv='', max_price=NULL, min_seats=1,
        min_days=NULL, max_days=NULL, date_start=NULL, date_end=NULL,
        show_new=1, show_active=1, show_removed=0, quiet_mode=0,
        max_items=30, show_active_time=1, updated_at=datetime('now')
      WHERE chat_id=?
    """, (chat_id,)); conn.commit()

def get_all_destinations(conn: sqlite3.Connection) -> List[str]:
    cur = conn.execute("SELECT DISTINCT destination FROM flights WHERE destination IS NOT NULL AND destination<>'' ORDER BY destination COLLATE NOCASE")
    return [r[0] for r in cur.fetchall()]

def query_flights_all(conn: sqlite3.Connection, limit: int = 30) -> List[Dict[str, Any]]:
    cur = conn.execute("""
    SELECT id, name, destination, link, price, currency, price_text, go_date, go_depart, go_arrive,
           back_date, back_depart, back_arrive, seats, status, first_seen, scraped_at, flight_key
      FROM flights
  ORDER BY datetime(COALESCE(scraped_at, first_seen, '1970-01-01T00:00:00')) DESC
     LIMIT ?
    """, (limit,))
    return [_row_to_dict(r) for r in cur.fetchall()]

def query_flights_by_prefs(conn: sqlite3.Connection, prefs: Dict[str, Any], limit: int = 30) -> List[Dict[str, Any]]:
    where, params = [], []
    dests_csv = (prefs.get("destinations_csv") or "").strip()
    if dests_csv:
        dests = [d.strip() for d in dests_csv.split(",") if d.strip()]
        if dests:
            where.append("(" + " OR ".join(["destination = ?" for _ in dests]) + ")"); params.extend(dests)
    max_price = prefs.get("max_price")
    if max_price not in (None, "", 0, "0"):
        where.append("price IS NOT NULL AND price <= ?"); params.append(int(max_price))
    min_seats = prefs.get("min_seats")
    if min_seats not in (None, "", 0, "0"):
        where.append("(seats IS NULL OR seats >= ?)"); params.append(int(min_seats))
    date_start = prefs.get("date_start"); date_end = prefs.get("date_end")
    if date_start: where.append("(go_date IS NOT NULL AND go_date >= ?)"); params.append(date_start)
    if date_end:   where.append("(go_date IS NOT NULL AND go_date <= ?)"); params.append(date_end)
    min_days = prefs.get("min_days"); max_days = prefs.get("max_days")
    if min_days or max_days:
        where.append("(go_date IS NOT NULL AND back_date IS NOT NULL)")
        if min_days: where.append("(julianday(back_date) - julianday(go_date) + 1) >= ?"); params.append(int(min_days))
        if max_days: where.append("(julianday(back_date) - julianday(go_date) + 1) <= ?"); params.append(int(max_days))
    where_sql = "WHERE " + " AND ".join(where) if where else ""
    sql = f"""
    SELECT id, name, destination, link, price, currency, price_text, go_date, go_depart, go_arrive,
           back_date, back_depart, back_arrive, seats, status, first_seen, scraped_at, flight_key
      FROM flights
      {where_sql}
  ORDER BY datetime(COALESCE(scraped_at, first_seen, '1970-01-01T00:00:00')) DESC
     LIMIT ?
    """
    params.append(limit)
    cur = conn.execute(sql, tuple(params))
    return [_row_to_dict(r) for r in cur.fetchall()]

def query_saved(conn: sqlite3.Connection, chat_id: int, limit: int = 30) -> List[Dict[str, Any]]:
    cur = conn.execute("""
    SELECT f.* FROM saved_flights s
    JOIN flights f ON f.flight_key = s.flight_key
    WHERE s.chat_id=?
    ORDER BY datetime(COALESCE(f.scraped_at, f.first_seen, '1970-01-01T00:00:00')) DESC
    LIMIT ?
    """, (chat_id, limit))
    return [_row_to_dict(r) for r in cur.fetchall()]

async def _send_feed(update: Update, context: ContextTypes.DEFAULT_TYPE, flights: List[Dict[str, Any]], header: str):
    if not flights:
        text = header + "\n\nלא נמצאו טיסות מתאימות כרגע."
        q = update.callback_query
        if q:
            try: await q.answer()
            except Exception: pass
            try:
                await q.edit_message_text(text, reply_markup=feed_nav_kb(),
                                          parse_mode=ParseMode.HTML, disable_web_page_preview=True)
                return
            except BadRequest: pass
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text,
                                       reply_markup=feed_nav_kb(), parse_mode=ParseMode.HTML,
                                       disable_web_page_preview=True)
        return
    cards = [format_flight_card(f) for f in flights]
    chunks = chunk_messages(cards, header=header)
    q = update.callback_query
    if q:
        try: await q.answer()
        except Exception: pass
    first = True
    for ch in chunks:
        if q and first:
            try:
                await q.edit_message_text(ch, reply_markup=feed_nav_kb(),
                                          parse_mode=ParseMode.HTML, disable_web_page_preview=True)
                first = False
                continue
            except BadRequest: pass
        await context.bot.send_message(chat_id=update.effective_chat.id, text=ch,
                                       reply_markup=feed_nav_kb(), parse_mode=ParseMode.HTML,
                                       disable_web_page_preview=True)
        first = False

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE, conn: sqlite3.Connection, cfg):
    chat_id = update.effective_chat.id
    ensure_user(conn, chat_id)
    await context.bot.send_message(chat_id=chat_id, text="🏠 תפריט ראשי", reply_markup=main_menu_kb())

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, conn: sqlite3.Connection, cfg):
    chat_id = update.effective_chat.id
    ensure_user(conn, chat_id)
    prefs = get_prefs(conn, chat_id)
    max_items = int(prefs.get("max_items") or 30)
    q = update.callback_query
    msg = update.effective_message
    data = (q.data if q else (msg.text if (msg and msg.text) else "")) or ""
    key = data.upper().strip()

    if q and data.startswith("SAVE|"):
        _, flight_key = data.split("|", 1)
        saved_now = toggle_saved(conn, update.effective_user.id, flight_key)
        await q.answer("✅ נשמר" if saved_now else "❎ הוסר", show_alert=False)
        return

    if q and data.startswith("SAVED"):
        flights = get_saved_flights(conn, update.effective_user.id)
        if not flights:
            try: await q.edit_message_text("אין טיסות שמורות עדיין.", parse_mode=ParseMode.HTML)
            except BadRequest: await context.bot.send_message(chat_id=chat_id, text="אין טיסות שמורות עדיין.", parse_mode=ParseMode.HTML)
            return
        cards, nav_kb, page, total = paginate_cards(flights, {"show_active_time":1}, page=1, page_size=10, show_active_time=True)
        try: await q.edit_message_text("\n\n".join(cards), reply_markup=nav_kb, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        except BadRequest: await context.bot.send_message(chat_id=chat_id, text="\n\n".join(cards), reply_markup=nav_kb, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        return

    if key in ("HOME","START","/START","בית","תפריט"):
        if q:
            try: await q.answer()
            except Exception: pass
            try: await q.edit_message_text("🏠 תפריט ראשי", reply_markup=main_menu_kb()); return
            except BadRequest: pass
        await context.bot.send_message(chat_id=chat_id, text="🏠 תפריט ראשי", reply_markup=main_menu_kb()); return

    if key in ("SHOW_ALL","SEND_NOW","ALL","כל הטיסות"):
        flights = query_flights_all(conn, limit=max_items)
        await _send_feed(update, context, flights, header="👀 כל הדילים (ללא סינון)")
        return

    if key in ("BY_PREFS","APPLY_PREFS","SHOW_PREFS"):
        flights = query_flights_by_prefs(conn, prefs, limit=max_items)
        await _send_feed(update, context, flights, header="🎯 דילים לפי העדפות")
        return

    if key.startswith("SUMMARY") or key == "סיכום לפי יעד":
        row = conn.execute("SELECT MAX(scraped_at) FROM flights").fetchone()
        last_ts = row[0] if row else None
        sql = """SELECT destination, COUNT(*) c FROM flights
                 WHERE destination IS NOT NULL AND destination<>'' {flt}
                 GROUP BY destination ORDER BY c DESC, destination LIMIT 50"""
        flt = "AND scraped_at=?" if last_ts else ""
        cur = conn.execute(sql.format(flt=flt), (last_ts,) if last_ts else ())
        rows = cur.fetchall()
        if not rows:
            txt = "אין כרגע טיסות זמינות לריצה האחרונה."
        else:
            lines = ["<b>📊 סיכום לפי יעד (זמין כרגע):</b>",""]
            for i,(d,c) in enumerate(rows,1):
                from telegram_view import flag_for
                flag = flag_for(d)
                medal = "🥇 " if i==1 else "🥈 " if i==2 else "🥉 " if i==3 else ""
                lines.append(f"{medal}{flag} {d} — {c}")
            txt = "\n".join(lines)
        if q:
            try: await q.answer()
            except Exception: pass
            try: await q.edit_message_text(txt, reply_markup=feed_nav_kb(), parse_mode=ParseMode.HTML); return
            except BadRequest: pass
        await context.bot.send_message(chat_id=chat_id, text=txt, reply_markup=feed_nav_kb(), parse_mode=ParseMode.HTML); return

    if key in ("RESET","איפוס"):
        reset_prefs(conn, chat_id)
        if q:
            try: await q.answer()
            except Exception: pass
            try: await q.edit_message_text("♻️ ההגדרות אופסו. חזרה לתפריט.", reply_markup=main_menu_kb()); return
            except BadRequest: pass
        await context.bot.send_message(chat_id=chat_id, text="♻️ ההגדרות אופסו.", reply_markup=main_menu_kb()); return

    if key in ("QUIET","QUIET_TOGGLE","מצב שקט"):
        new_val = 0 if int(prefs.get("quiet_mode") or 0) else 1
        update_prefs(conn, chat_id, quiet_mode=new_val)
        msg_txt = "🔕 מצב שקט הופעל — תקבל רק התראות קריטיות" if new_val else "🔔 מצב שקט בוטל — תחזור לקבל הכל"
        if q:
            try: await q.answer()
            except Exception: pass
            try: await q.edit_message_text(msg_txt, reply_markup=main_menu_kb()); return
            except BadRequest: pass
        await context.bot.send_message(chat_id=chat_id, text=msg_txt, reply_markup=main_menu_kb()); return

    if key in ("DESTS","יעדים"):
        dests_all = get_all_destinations(conn)
        page = 1
        header = _center_title("בחר/י יעדים (בחירה מרובה) — ✅/⬜️")
        kb = destinations_page(prefs.get("destinations_csv") or "", page, 21, dests_all)
        if q:
            try: await q.answer()
            except Exception: pass
            try: await q.edit_message_text(header, reply_markup=kb, parse_mode=ParseMode.HTML); return
            except BadRequest: pass
        await context.bot.send_message(chat_id=chat_id, text=header, reply_markup=kb, parse_mode=ParseMode.HTML); return

    if key.startswith("DESTS_PAGE_"):
        dests_all = get_all_destinations(conn)
        try: page = int(key.split("_")[-1])
        except Exception: page = 1
        header = _center_title("בחר/י יעדים (בחירה מרובה) — ✅/⬜️")
        kb = destinations_page(prefs.get("destinations_csv") or "", page, 21, dests_all)
        await q.edit_message_text(header, reply_markup=kb, parse_mode=ParseMode.HTML); return

    if key == "DEST_ALL_TOGGLE":
        all_dests = get_all_destinations(conn)
        cur = (prefs.get("destinations_csv") or "").strip()
        selected = [d for d in cur.split(",") if d.strip()]
        if len(selected) >= len(all_dests):
            from telegram_view import main_menu_kb
            update_prefs(conn, chat_id, destinations_csv="")
            await q.answer("נוקה")
            await q.edit_message_text("🏠 תפריט ראשי", reply_markup=main_menu_kb()); return
        update_prefs(conn, chat_id, destinations_csv=",".join(all_dests))
        await q.answer("✅ כל היעדים סומנו")
        await q.edit_message_text("🏠 תפריט ראשי", reply_markup=main_menu_kb()); return

    if key.startswith("DEST_TOGGLE::"):
        dests_all = get_all_destinations(conn)
        item = data.split("::",1)[1].split("|")[0]
        current = [d for d in (prefs.get("destinations_csv") or "").split(",") if d.strip()]
        if item in current: current = [d for d in current if d != item]
        else: current.append(item)
        csv = ",".join(current)
        update_prefs(conn, chat_id, destinations_csv=csv)
        prefs = get_prefs(conn, chat_id)
        import re as _re
        m = _re.search(r"PAGE_(\d+)$", data or "")
        page = int(m.group(1)) if m else 1
        header = _center_title("בחר/י יעדים (בחירה מרובה) — ✅/⬜️")
        kb = destinations_page(prefs.get("destinations_csv") or "", page, 21, dests_all)
        await q.edit_message_text(header, reply_markup=kb, parse_mode=ParseMode.HTML); return

    if key == "DEST_SAVE":
        if q:
            try: await q.answer()
            except Exception: pass
            try: await q.edit_message_text("✅ נשמר. חוזר לתפריט.", reply_markup=main_menu_kb()); return
            except BadRequest: pass
        await context.bot.send_message(chat_id=chat_id, text="✅ נשמר.", reply_markup=main_menu_kb()); return

    if key in ("PRICE","מחיר"):
        kb = price_menu_kb(prefs, conn=conn)
        title = _center_title("מחיר מקסימלי 💸")
        if q:
            try: await q.answer()
            except Exception: pass
            try: await q.edit_message_text(title, reply_markup=kb, parse_mode=ParseMode.HTML); return
            except BadRequest: pass
        await context.bot.send_message(chat_id=chat_id, text=title, reply_markup=kb, parse_mode=ParseMode.HTML); return

    if (q and key.startswith("PRICE_SET_")) or (q and key == "PRICE_CLEAR"):
        if key == "PRICE_CLEAR":
            update_prefs(conn, chat_id, max_price=None)
        else:
            raw = key.split("PRICE_SET_",1)[1]
            digits = re.sub(r"[^0-9]", "", raw)
            val = int(digits) if digits else None
            update_prefs(conn, chat_id, max_price=val)
        await q.edit_message_text("✅ עודכן. חוזר לתפריט.", reply_markup=main_menu_kb()); return

    if key in ("SEATS","מושבים"):
        kb = seats_menu_kb(prefs)
        title = _center_title("מינימום מושבים 🪑")
        if q:
            try: await q.answer()
            except Exception: pass
            try: await q.edit_message_text(title, reply_markup=kb, parse_mode=ParseMode.HTML); return
            except BadRequest: pass
        await context.bot.send_message(chat_id=chat_id, text=title, reply_markup=kb, parse_mode=ParseMode.HTML); return

    if (q and key.startswith("SEATS_SET_")) or (q and key == "SEATS_CLEAR"):
        if key == "SEATS_CLEAR":
            update_prefs(conn, chat_id, min_seats=1)
        else:
            val = int(key.split("_")[-1]); update_prefs(conn, chat_id, min_seats=val)
        await q.edit_message_text("✅ עודכן. חוזר לתפריט.", reply_markup=main_menu_kb()); return

    if key in ("DATES","תאריכים"):
        kb = dates_menu_kb()
        title = _center_title("בחר/י טווח תאריכים 🗓")
        if q:
            try: await q.answer()
            except Exception: pass
            try: await q.edit_message_text(title, reply_markup=kb, parse_mode=ParseMode.HTML); return
            except BadRequest: pass
        await context.bot.send_message(chat_id=chat_id, text=title, reply_markup=kb, parse_mode=ParseMode.HTML); return

    if q and key in ("DATES_WEEK","DATES_MONTH","DATES_CLEAR"):
        today = datetime.utcnow().date()
        if key == "DATES_WEEK":
            ds, de = today.isoformat(), (today + timedelta(days=7)).isoformat()
            update_prefs(conn, chat_id, date_start=ds, date_end=de)
        elif key == "DATES_MONTH":
            ds = today.isoformat()
            nm = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
            de = (nm - timedelta(days=1)).isoformat()
            update_prefs(conn, chat_id, date_start=ds, date_end=de)
        else:
            update_prefs(conn, chat_id, date_start=None, date_end=None)
        await q.edit_message_text("✅ עודכן. חוזר לתפריט.", reply_markup=main_menu_kb()); return

    if (not q) and data and re.match(r"^\d{4}-\d{2}-\d{2},\d{4}-\d{2}-\d{2}$", data):
        ds, de = data.strip().split(",")
        update_prefs(conn, chat_id, date_start=ds, date_end=de)
        await context.bot.send_message(chat_id=chat_id, text="✅ טווח תאריכים נשמר.", reply_markup=main_menu_kb())
        return

    if key in ("TRIP","אורך טיול"):
        kb = trip_len_menu_kb()
        title = _center_title("אורך טיול 🧾")
        if q:
            try: await q.answer()
            except Exception: pass
            try: await q.edit_message_text(title, reply_markup=kb, parse_mode=ParseMode.HTML); return
            except BadRequest: pass
        await context.bot.send_message(chat_id=chat_id, text=title, reply_markup=kb, parse_mode=ParseMode.HTML); return

    if q and (key.startswith("TRIP_SET_") or key == "TRIP_CLEAR"):
        if key == "TRIP_CLEAR":
            update_prefs(conn, chat_id, min_days=None, max_days=None)
        else:
            part = key.split("_")[-1]; lo, hi = part.split("-")
            update_prefs(conn, chat_id, min_days=int(lo), max_days=int(hi))
        await q.edit_message_text("✅ עודכן. חוזר לתפריט.", reply_markup=main_menu_kb()); return

    if key in ("VIS","נראות"):
        kb = visibility_menu_kb(prefs)
        title = _center_title("נראות דילים 👀")
        if q:
            try: await q.answer()
            except Exception: pass
            try: await q.edit_message_text(title, reply_markup=kb, parse_mode=ParseMode.HTML); return
            except BadRequest: pass
        await context.bot.send_message(chat_id=chat_id, text=title, reply_markup=kb, parse_mode=ParseMode.HTML); return

    if q and key.startswith("VIS_TOGGLE_"):
        flag = key.split("_")[-1].lower()
        cur = int(prefs.get(f"show_{flag}") or 0)
        update_prefs(conn, chat_id, **{f"show_{flag}": 0 if cur else 1})
        prefs = get_prefs(conn, chat_id)
        kb = visibility_menu_kb(prefs)
        await q.edit_message_text(_center_title("נראות דילים 👀"), reply_markup=kb, parse_mode=ParseMode.HTML); return

    if key in ("SAVED","שמורים"):
        flights = query_saved(conn, chat_id, limit=max_items)
        await _send_feed(update, context, flights, header="⭐ טיסות שמורות")
        return

    if q and key.startswith("SAVE::"):
        fkey = data.split("::",1)[1]
        conn.execute("INSERT OR IGNORE INTO saved_flights(chat_id, flight_key) VALUES(?,?)", (chat_id, fkey))
        conn.commit()
        await q.answer("⭐ נשמר")
        return

    if q and key.startswith("UNSAVE::"):
        fkey = data.split("::",1)[1]
        conn.execute("DELETE FROM saved_flights WHERE chat_id=? AND flight_key= ?", (chat_id, fkey))
        conn.commit()
        await q.answer("🗑 הוסר")
        return

    if q:
        try: await q.answer()
        except Exception: pass
    await context.bot.send_message(chat_id=chat_id, text="🏠 תפריט ראשי", reply_markup=main_menu_kb())
PY

_write notify.py <<'PY'
# @@file_version: v2.4.7
from __future__ import annotations
import sqlite3
from typing import Dict, Any, List
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram_view import format_flight_card

EVENTS = ("new","removed","price_down","price_up","seats_down")

def _row(r): return {k:r[k] for k in r.keys()}

def _eligible_users(conn: sqlite3.Connection) -> List[int]:
    cur = conn.execute("SELECT chat_id FROM users WHERE subscribed=1")
    return [r[0] for r in cur.fetchall()]

def _delta(conn: sqlite3.Connection) -> Dict[str, List[Dict[str,Any]]]:
    out = {e: [] for e in EVENTS}
    cur = conn.execute("""
      SELECT * FROM flights
      WHERE scraped_at=(SELECT MAX(scraped_at) FROM flights) AND COALESCE(status,'active')='active'
    """)
    latest = [_row(r) for r in cur.fetchall()]
    keys_latest = {r.get("flight_key") for r in latest if r.get("flight_key")}

    prev_ts_row = conn.execute("""
      SELECT MAX(scraped_at) FROM flights
      WHERE scraped_at < (SELECT MAX(scraped_at) FROM flights)
    """).fetchone()
    prev_ts = prev_ts_row[0] if prev_ts_row else None
    prev = []
    if prev_ts:
        cur = conn.execute("SELECT * FROM flights WHERE scraped_at=?", (prev_ts,))
        prev = [_row(r) for r in cur.fetchall()]
    prev_map = {r.get("flight_key"): r for r in prev if r.get("flight_key")}

    prev_keys = set(prev_map.keys())
    removed_keys = prev_keys - keys_latest
    for k in removed_keys:
        rec = prev_map[k].copy(); rec["status"]="removed"; out["removed"].append(rec)

    for r in latest:
        k = r.get("flight_key")
        if k not in prev_map:
            out["new"].append(r)
        else:
            p = prev_map[k]
            if (r.get("price") or 0) < (p.get("price") or 0):
                out["price_down"].append(r)
            elif (r.get("price") or 0) > (p.get("price") or 0):
                out["price_up"].append(r)
            if r.get("seats") and p.get("seats") and r["seats"] < p["seats"]:
                out["seats_down"].append(r)
    return out

async def notify_changes(conn: sqlite3.Connection, bot: Bot):
    deltas = _delta(conn)
    users = _eligible_users(conn)
    if not users: return

    for chat_id in users:
        prefs = conn.execute("SELECT * FROM user_prefs WHERE chat_id=?", (chat_id,)).fetchone()
        show_new = int((prefs and prefs["show_new"]) or 1)
        show_removed = int((prefs and prefs["show_removed"]) or 0)
        max_items = int((prefs and prefs["max_items"]) or 30)

        bundles = []
        if show_new and deltas["new"]:
            bundles.append(("✨ טיסות חדשות", deltas["new"]))
        if deltas["price_down"]:
            bundles.append(("⬇️ ירידת מחיר", deltas["price_down"]))
        if deltas["seats_down"]:
            bundles.append(("⚠️ פחות מושבים", deltas["seats_down"]))
        if show_removed and deltas["removed"]:
            bundles.append(("🚫 טיסות שהוסרו", deltas["removed"]))

        for title, items in bundles:
            cards = [format_flight_card(f, show_removed=(title.startswith("🚫"))) for f in items[:max_items]]
            if not cards: continue
            text = f"<b>{title}</b>\n\n" + "\n\n".join(cards)
            try:
                await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            except BadRequest:
                pass
PY

_write app.py <<'PY'
# @@file_version: v2.4.7
from __future__ import annotations
import logging, sqlite3
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
import config as cfg
from handlers import handle_start, handle_callback
from notify import notify_changes
from db import ensure_schema, ensure_price_catalog

logging.basicConfig(level=getattr(logging, cfg.LOG_LEVEL, "INFO"))
log = logging.getLogger("tusbot")

def _conn():
    conn = sqlite3.connect(cfg.DB_FILE)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    ensure_price_catalog(conn)
    return conn

async def _start_wrapper(update, context):
    conn = _conn()
    try:
        await handle_start(update, context, conn, cfg)
    finally:
        conn.close()

async def _cb_wrapper(update, context):
    conn = _conn()
    try:
        await handle_callback(update, context, conn, cfg)
    finally:
        conn.close()

async def _tick_notify(ctx):
    conn = _conn()
    try:
        await notify_changes(conn, ctx.application.bot)
    finally:
        conn.close()

def main():
    app = ApplicationBuilder().token(cfg.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", _start_wrapper))
    app.add_handler(CallbackQueryHandler(_cb_wrapper))
    app.job_queue.run_repeating(_tick_notify, interval=cfg.INTERVAL, first=30)
    log.info("🚀 tusbot v2.4.7 up. DB=%s, interval=%ss", cfg.DB_FILE, cfg.INTERVAL)
    app.run_polling()

if __name__ == "__main__":
    main()
PY

_write botctl.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
APP="app.py"
PID_FILE="${PROJECT_DIR}/tustus_bot.pid"
LOG_FILE="${PROJECT_DIR}/bot.log"
VENV_DIR="${PROJECT_DIR}/.venv"
VENV_PY="${VENV_DIR}/bin/python3"
if [[ -x "$VENV_PY" ]]; then
  PY="$VENV_PY"
else
  if command -v python3 >/dev/null 2>&1; then
    PY="$(command -v python3)"
    echo "⚠️  Using system python: ${PY} (no .venv found)"
  else
    echo "❌ python3 not found. Please install Python 3.10+."
    exit 1
  fi
fi
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
export PATH="$PROJECT_DIR/.venv/bin:$PATH"
is_running(){ if [[ -f "$PID_FILE" ]]; then pid="$(cat "$PID_FILE" 2>/dev/null || true)"; [[ -n "${pid}" ]] && kill -0 "$pid" 2>/dev/null && return 0; fi; return 1; }
start(){ if is_running; then echo "ℹ️  Already running (PID $(cat "$PID_FILE"))."; exit 0; fi
  echo "▶️  Starting bot..."; nohup "$PY" "$APP" >> "$LOG_FILE" 2>&1 & echo $! > "$PID_FILE"; sleep 0.5
  if is_running; then echo "✅ Started (PID $(cat "$PID_FILE")). Logs: $LOG_FILE"; else echo "❌ Failed to start. Check $LOG_FILE"; exit 1; fi; }
stop(){ if ! is_running; then echo "ℹ️  Not running."; exit 0; fi
  pid="$(cat "$PID_FILE")"; echo "⏹  Stopping (PID $pid)..."; kill "$pid" || true
  for i in {1..20}; do kill -0 "$pid" 2>/dev/null || break; sleep 0.2; done
  kill -0 "$pid" 2>/dev/null && { echo "⚠️  Force kill."; kill -9 "$pid" || true; }
  rm -f "$PID_FILE"; echo "✅ Stopped."; }
restart(){ stop || true; start; }
status(){ if is_running; then echo "🟢 Running (PID $(cat "$PID_FILE"))."; else echo "🔴 Not running."; fi }
case "${1:-}" in start) start ;; stop) stop ;; restart) restart ;; status) status ;; *) echo "Usage: $0 {start|stop|restart|status}"; exit 2 ;; esac
SH
chmod +x "$STAGE/botctl.sh"

_write requirements.txt <<'TXT'
python-telegram-bot==20.7
TXT

# release notes
RN="$STAGE/release_notes.txt"
if [[ -f "$RN" ]]; then echo >> "$RN"; fi
cat >> "$RN" <<'RN'
v2.4.7
- פונקציית פוש אוטומטי על בסיס ניטור (JobQueue) — הודעות NEW/REMOVED/PRICE DOWN/SEATS DOWN לפי העדפות.
- תפריט: "תראה עכשיו" הוחלף ל-"כל הטיסות".
- מחירים: נשלפים מה-DB כמו שהם + קטלוג מחירים דינמי שנשמר לאורך זמן; כותרות ממורכזות.
- יעדים: "בחר הכל", גריד 3 עמודות לדסקטופ, מציגים כל יעד שקיים ב-DB גם בלי טיסה פעילה.
- כרטיס טיסה: חץ לפי כיוון הזמן, איקון מושבים כשלא ידוע, היפרלינק לטוסטוס, סימון 🚫 להסרות.
- "סיכום לפי יעד": עם דגלי מדינות ו-Top 3 במדליות.
- botctl.sh: יצוא PATH/PYTHONPATH ל-venv.
RN

# pack
OUT="$(pwd)/tusbot_v2.4.7.zip"
rm -f "$OUT"
( cd "$WORK" && zip -qr "$OUT" "$STAGE_NAME" )
echo "$OUT"
