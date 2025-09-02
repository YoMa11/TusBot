from __future__ import annotations
__file_version__ = "handlers.py@tustus_v2.5.5"  # updated 2025-08-30 18:58  # added 2025-08-30 18:21

import re
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from db import toggle_saved, get_saved_flights

from telegram_view import (
    main_menu_kb,
    destinations_page,
    price_menu_kb,
    seats_menu_kb,
    dates_menu_kb,
    trip_len_menu_kb,
    visibility_menu_kb,
    feed_nav_kb,
    format_flight_card,
    chunk_messages,
    paginate_cards,
)

# ===== Utilities =====
def _row_to_dict(r: sqlite3.Row) -> Dict[str, Any]:
    return {k: r[k] for k in r.keys()}

def ensure_user(conn: sqlite3.Connection, chat_id: int):
    conn.execute(
        "INSERT OR IGNORE INTO users(chat_id, created_at, last_seen_at, subscribed) "
        "VALUES(?, datetime('now'), datetime('now'), 1)",
        (chat_id,)
    )
    conn.execute('''
    INSERT OR IGNORE INTO user_prefs(
      chat_id, destinations_csv, max_price, min_seats, min_days, max_days,
      date_start, date_end, show_new, show_active, show_removed, quiet_mode,
      max_items, show_active_time, updated_at
    ) VALUES(?, '', NULL, 1, NULL, NULL, NULL, NULL, 1, 1, 0, 0, 30, 1, datetime('now'))
    ''', (chat_id,))
    conn.execute('''
    CREATE TABLE IF NOT EXISTS saved_flights(
      chat_id INTEGER NOT NULL,
      flight_key TEXT NOT NULL,
      saved_at TEXT DEFAULT (datetime('now')),
      PRIMARY KEY(chat_id, flight_key)
    )
    ''')
    conn.commit()

def get_prefs(conn: sqlite3.Connection, chat_id: int) -> Dict[str, Any]:
    r = conn.execute("SELECT * FROM user_prefs WHERE chat_id=?", (chat_id,)).fetchone()
    return _row_to_dict(r) if r else {}

def update_prefs(conn: sqlite3.Connection, chat_id: int, **fields):
    if not fields:
        return
    sets = ", ".join([f"{k}=?" for k in fields])
    params = list(fields.values()) + [chat_id]
    conn.execute(f"UPDATE user_prefs SET {sets}, updated_at=datetime('now') WHERE chat_id=?", params)
    conn.commit()

def reset_prefs(conn: sqlite3.Connection, chat_id: int):
    conn.execute('''
      UPDATE user_prefs SET
        destinations_csv='',
        max_price=NULL,
        min_seats=1,
        min_days=NULL,
        max_days=NULL,
        date_start=NULL,
        date_end=NULL,
        show_new=1,
        show_active=1,
        show_removed=0,
        quiet_mode=0,
        max_items=30,
        show_active_time=1,
        updated_at=datetime('now')
      WHERE chat_id=?
    ''', (chat_id,))
    conn.commit()

# ===== Destinations source =====
def get_all_destinations(conn: sqlite3.Connection) -> List[str]:
    last = conn.execute("SELECT MAX(scraped_at) FROM flights").fetchone()[0]
    q = '''
    SELECT DISTINCT destination
    FROM flights
    WHERE destination IS NOT NULL AND destination <> ''
      AND (? IS NULL OR scraped_at = ?)
      AND price IS NOT NULL AND price > 0
      AND go_date IS NOT NULL AND back_date IS NOT NULL
    ORDER BY destination COLLATE NOCASE
    '''
    rows = [r[0] for r in conn.execute(q, (last, last)).fetchall()]
    BAD = {"arr","cmbMonth","cmbWP","else","txtWebName","מחיר"}
    clean = []
    for d in rows:
        s = (d or "").strip()
        if not s or s in BAD:
            continue
        if re.search(r"[A-Za-z]{2,}", s):
            continue
        clean.append(s)
    return clean

# ===== Queries =====
def _last_scrape(conn: sqlite3.Connection):
    row = conn.execute("SELECT MAX(scraped_at) FROM flights").fetchone()
    return row[0] if row else None

def query_flights_all(conn: sqlite3.Connection, limit: int = 30) -> List[Dict[str, Any]]:
    last = _last_scrape(conn)
    q = '''
    SELECT *
    FROM flights
    WHERE (? IS NULL OR scraped_at = ?)
      AND destination IS NOT NULL AND destination <> ''
      AND price IS NOT NULL AND price > 0
      AND go_date IS NOT NULL AND back_date IS NOT NULL
    GROUP BY flight_key
    ORDER BY datetime(COALESCE(scraped_at, first_seen, '1970-01-01T00:00:00')) DESC
    LIMIT ?
    '''
    cur = conn.execute(q, (last, last, limit))
    return [_row_to_dict(r) for r in cur.fetchall()]

def query_flights_by_prefs(conn: sqlite3.Connection, prefs: Dict[str, Any], limit: int = 30) -> List[Dict[str, Any]]:
    where, params = [], []
    last = _last_scrape(conn)
    where.append("(? IS NULL OR scraped_at = ?)")
    params.extend([last, last])

    dests_csv = (prefs.get("destinations_csv") or "").strip()
    if dests_csv:
        dests = [d.strip() for d in dests_csv.split(",") if d.strip()]
        if dests:
            where.append("(" + " OR ".join(["destination = ?" for _ in dests]) + ")")
            params.extend(dests)

    max_price = prefs.get("max_price")
    if max_price not in (None, "", 0, "0"):
        where.append("price IS NOT NULL AND price <= ?")
        params.append(int(max_price))

    min_seats = prefs.get("min_seats")
    if min_seats not in (None, "", 0, "0"):
        where.append("(seats IS NULL OR seats >= ?)")
        params.append(int(min_seats))

    date_start = prefs.get("date_start")
    date_end = prefs.get("date_end")
    if date_start:
        where.append("(go_date IS NOT NULL AND go_date >= ?)")
        params.append(date_start)
    if date_end:
        where.append("(go_date IS NOT NULL AND go_date <= ?)")
        params.append(date_end)

    min_days = prefs.get("min_days")
    max_days = prefs.get("max_days")
    if min_days or max_days:
        where.append("(go_date IS NOT NULL AND back_date IS NOT NULL)")
        if min_days:
            where.append("(julianday(back_date) - julianday(go_date) + 1) >= ?")
            params.append(int(min_days))
        if max_days:
            where.append("(julianday(back_date) - julianday(go_date) + 1) <= ?")
            params.append(int(max_days))

    where_sql = "WHERE " + " AND ".join(where) if where else ""
    sql = f'''
    SELECT *
    FROM flights
    {where_sql}
    GROUP BY flight_key
    ORDER BY datetime(COALESCE(scraped_at, first_seen, '1970-01-01T00:00:00')) DESC
    LIMIT ?
    '''
    params.append(limit)
    cur = conn.execute(sql, tuple(params))
    return [_row_to_dict(r) for r in cur.fetchall()]

def query_saved(conn: sqlite3.Connection, chat_id: int, limit: int = 30) -> List[Dict[str, Any]]:
    cur = conn.execute('''
    SELECT f.*
    FROM saved_flights s
    JOIN flights f ON f.flight_key = s.flight_key
    WHERE s.chat_id=?
    GROUP BY f.flight_key
    ORDER BY datetime(COALESCE(f.scraped_at, f.first_seen, '1970-01-01T00:00:00')) DESC
    LIMIT ?
    ''', (chat_id, limit))
    return [_row_to_dict(r) for r in cur.fetchall()]

# ===== Sender =====
async def _send_feed(update: Update, context: ContextTypes.DEFAULT_TYPE, flights: List[Dict[str, Any]], header: str):
    if not flights:
        text = header + "\n\nלא נמצאו טיסות מתאימות כרגע."
        q = update.callback_query
        if q:
            try:
                await q.answer()
            except Exception:
                pass
            try:
                await q.edit_message_text(
                    text, reply_markup=feed_nav_kb(), parse_mode=ParseMode.HTML, disable_web_page_preview=True
                )
                return
            except BadRequest:
                pass
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text, reply_markup=feed_nav_kb(), parse_mode=ParseMode.HTML, disable_web_page_preview=True
        )
        return

    cards = [format_flight_card(f) for f in flights]
    chunks = chunk_messages(cards, header=header)

    q = update.callback_query
    if q:
        try:
            await q.answer()
        except Exception:
            pass

    first = True
    for ch in chunks:
        if q and first:
            try:
                await q.edit_message_text(ch, reply_markup=feed_nav_kb(), parse_mode=ParseMode.HTML, disable_web_page_preview=True)
                first = False
                continue
            except BadRequest:
                pass
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=ch, reply_markup=feed_nav_kb(), parse_mode=ParseMode.HTML, disable_web_page_preview=True
        )
        first = False

# ===== Public handlers =====
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

    if q:
        data = (q.data or "").strip()
    else:
        data = (msg.text or "").strip() if msg and msg.text else ""

    key = data.upper()

    # ----- quick raw actions -----
    if q and data.startswith("SAVE|"):
        _, flight_key = data.split("|", 1)
        saved_now = toggle_saved(conn, update.effective_user.id, flight_key)
        await q.answer("✅ נשמר" if saved_now else "❎ הוסר", show_alert=False)
        return

    if q and data.startswith("SAVED"):
        flights = get_saved_flights(conn, update.effective_user.id)
        if not flights:
            try:
                await q.edit_message_text("אין טיסות שמורות עדיין.", parse_mode=ParseMode.HTML)
            except BadRequest:
                await context.bot.send_message(chat_id=chat_id, text="אין טיסות שמורות עדיין.", parse_mode=ParseMode.HTML)
            return
        cards, nav_kb, page, total = paginate_cards(flights, {"show_active_time": 1}, page=1, page_size=10, show_active_time=True)
        try:
            await q.edit_message_text("\n\n".join(cards), reply_markup=nav_kb, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        except BadRequest:
            await context.bot.send_message(chat_id=chat_id, text="\n\n".join(cards), reply_markup=nav_kb, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        return

    if q and data.startswith("SEATS|"):
        _, value = data.split("|", 1)
        sel = set(context.user_data.get("seats_sel", []))
        if value.isdigit():
            v = int(value)
            if v in sel:
                sel.remove(v)
            else:
                sel.add(v)
            context.user_data["seats_sel"] = sorted(sel)
            await q.answer(f"בחירה: {sorted(sel)}")
            return
        if value == "CONFIRM":
            if sel:
                min_seats = min(sel)
                conn.execute(
                    "UPDATE user_prefs SET min_seats=?, updated_at=datetime('now') WHERE chat_id=?",
                    (min_seats, update.effective_user.id),
                )
                conn.commit()
                await q.answer(f"✅ נשמר מינימום מושבים: {min_seats}")
            else:
                await q.answer("לא נבחרו מושבים")
            return

    # ----- main menu routing -----
    if key in ("HOME", "START", "/START", "בית", "תפריט"):
        if q:
            try:
                await q.answer()
            except Exception:
                pass
            try:
                await q.edit_message_text("🏠 תפריט ראשי", reply_markup=main_menu_kb())
                return
            except BadRequest:
                pass
        await context.bot.send_message(chat_id=chat_id, text="🏠 תפריט ראשי", reply_markup=main_menu_kb())
        return

    if key in ("SHOW_ALL", "SEND_NOW", "ALL", "תראה עכשיו", "כל הדילים"):
        flights = query_flights_all(conn, limit=max_items)
        await _send_feed(update, context, flights, header="👀 כל הדילים (זמינים כעת)")
        return

    if key in ("BY_PREFS", "APPLY_PREFS", "SHOW_PREFS"):
        flights = query_flights_by_prefs(conn, prefs, limit=max_items)
        await _send_feed(update, context, flights, header="🎯 דילים לפי העדפות")
        return

    # SUMMARY (only last scrape)
    if key.startswith("SUMMARY") or key == "סיכום לפי יעד":
        row = conn.execute("SELECT MAX(scraped_at) FROM flights").fetchone()
        last_ts = row[0] if row else None
        if last_ts:
            cur = conn.execute(
                "SELECT destination, COUNT(*) AS c FROM flights WHERE scraped_at=? AND destination IS NOT NULL AND destination<>'' GROUP BY destination ORDER BY c DESC, destination LIMIT 50",
                (last_ts,)
            )
        else:
            cur = conn.execute(
                "SELECT destination, COUNT(*) AS c FROM flights WHERE destination IS NOT NULL AND destination<>'' GROUP BY destination ORDER BY c DESC, destination LIMIT 50"
            )
        rows = cur.fetchall()
        if not rows:
            txt = "אין כרגע טיסות זמינות לריצה האחרונה."
        else:
            lines = ["📊 סיכום לפי יעד (זמין כרגע):", ""]
            for d, c in rows:
                lines.append(f"• {d} — {c}")
            txt = "\n".join(lines)
        if q:
            try:
                await q.answer()
            except Exception:
                pass
            try:
                await q.edit_message_text(txt, reply_markup=feed_nav_kb(), parse_mode=ParseMode.HTML)
                return
            except BadRequest:
                pass
        await context.bot.send_message(chat_id=chat_id, text=txt, reply_markup=feed_nav_kb(), parse_mode=ParseMode.HTML)
        return

    # filter destination from summary
    if q and key.startswith("FILTER_DEST::"):
        d = data.split("::",1)[1]
        flights = query_flights_by_prefs(conn, {**prefs, "destinations_csv": d}, limit=max_items)
        await _send_feed(update, context, flights, header=f"🎯 טיסות ל–{d}")
        return

    if key in ("RESET", "איפוס"):
        reset_prefs(conn, chat_id)
        if q:
            try:
                await q.answer()
            except Exception:
                pass
            try:
                await q.edit_message_text("♻️ ההגדרות אופסו. חזרה לתפריט.", reply_markup=main_menu_kb())
                return
            except BadRequest:
                pass
        await context.bot.send_message(chat_id=chat_id, text="♻️ ההגדרות אופסו.", reply_markup=main_menu_kb())
        return

    if key in ("QUIET", "QUIET_TOGGLE", "מצב שקט"):
        new_val = 0 if int(prefs.get("quiet_mode") or 0) else 1
        update_prefs(conn, chat_id, quiet_mode=new_val)
        msg_txt = "🔕 מצב שקט הופעל — תקבל רק התראות קריטיות" if new_val else "🔔 מצב שקט בוטל — תחזור לקבל הכל"
        if q:
            try:
                await q.answer()
            except Exception:
                pass
            try:
                await q.edit_message_text(msg_txt, reply_markup=main_menu_kb())
                return
            except BadRequest:
                pass
        await context.bot.send_message(chat_id=chat_id, text=msg_txt, reply_markup=main_menu_kb())
        return

    # Destinations
    if key in ("DESTS", "יעדים"):
        dests_all = get_all_destinations(conn)
        page = 1
        header = "🎯 בחר/י יעדים (בחירה מרובה) — ✅/⬜️"
        kb = destinations_page(prefs.get("destinations_csv") or "", page, 18, dests_all)
        if q:
            try:
                await q.answer()
            except Exception:
                pass
            try:
                await q.edit_message_text(header, reply_markup=kb)
                return
            except BadRequest:
                pass
        await context.bot.send_message(chat_id=chat_id, text=header, reply_markup=kb)
        return

    if key.startswith("DESTS_PAGE_"):
        dests_all = get_all_destinations(conn)
        try:
            page = int(key.split("_")[-1])
        except Exception:
            page = 1
        header = "🎯 בחר/י יעדים (בחירה מרובה) — ✅/⬜️"
        kb = destinations_page(prefs.get("destinations_csv") or "", page, 18, dests_all)
        if q:
            await q.edit_message_text(header, reply_markup=kb)
        else:
            await context.bot.send_message(chat_id=chat_id, text=header, reply_markup=kb)
        return

    if key.startswith("DEST_TOGGLE::"):
        dests_all = get_all_destinations(conn)
        item = data.split("::", 1)[1].split("|")[0]
        current = [d for d in (prefs.get("destinations_csv") or "").split(",") if d.strip()]
        if item in current:
            current = [d for d in current if d != item]
        else:
            current.append(item)
        csv = ",".join(current)
        update_prefs(conn, chat_id, destinations_csv=csv)
        prefs = get_prefs(conn, chat_id)
        m = re.search(r"PAGE_(\d+)$", data or "")
        page = int(m.group(1)) if m else 1
        header = "🎯 בחר/י יעדים (בחירה מרובה) — ✅/⬜️"
        kb = destinations_page(prefs.get("destinations_csv") or "", page, 18, dests_all)
        if q:
            await q.edit_message_text(header, reply_markup=kb)
        else:
            await context.bot.send_message(chat_id=chat_id, text=header, reply_markup=kb)
        return

    if key == "DEST_SAVE":
        if q:
            try:
                await q.answer()
            except Exception:
                pass
            try:
                await q.edit_message_text("✅ נשמר. חוזר לתפריט.", reply_markup=main_menu_kb())
                return
            except BadRequest:
                pass
        await context.bot.send_message(chat_id=chat_id, text="✅ נשמר.", reply_markup=main_menu_kb())
        return

    if key == "DEST_SELECT_ALL":
        dests_all = get_all_destinations(conn)
        csv = ",".join(dests_all)
        update_prefs(conn, chat_id, destinations_csv=csv)
        prefs = get_prefs(conn, chat_id)
        kb = destinations_page(prefs.get("destinations_csv") or "", 1, 20, dests_all)
        if q:
            await q.edit_message_text("🎯 בחר/י יעדים (כולם מסומנים) — ✅/⬜️", reply_markup=kb)
        else:
            await context.bot.send_message(chat_id=chat_id, text="🎯 כולם סומנו", reply_markup=kb)
        return
    if key == "DEST_CLEAR_ALL":
        update_prefs(conn, chat_id, destinations_csv="")
        dests_all = get_all_destinations(conn)
        prefs = get_prefs(conn, chat_id)
        kb = destinations_page(prefs.get("destinations_csv") or "", 1, 20, dests_all)
        if q:
            await q.edit_message_text("🎯 סומן נקה הכל — ✅/⬜️", reply_markup=kb)
        else:
            await context.bot.send_message(chat_id=chat_id, text="🎯 סומן נקה הכל", reply_markup=kb)
        return

    # Price
    if key in ("PRICE", "מחיר"):
        kb = price_menu_kb(conn, prefs)
        if q:
            try:
                await q.answer()
            except Exception:
                pass
            try:
                await q.edit_message_text("💸 מחיר מקסימלי", reply_markup=kb)
                return
            except BadRequest:
                pass
        await context.bot.send_message(chat_id=chat_id, text="💸 מחיר מקסימלי", reply_markup=kb)
        return

    if q and key.startswith("PRICE_PAGE_"):
        try:
            pg = int(key.split("_")[-1])
        except Exception:
            pg = 1
        kb = price_menu_kb(conn, prefs, page=pg)
        try:
            await q.edit_message_text("💸 מחיר מקסימלי", reply_markup=kb)
        except BadRequest:
            await context.bot.send_message(chat_id=chat_id, text="💸 מחיר מקסימלי", reply_markup=kb)
        return

    if (q and key.startswith("PRICE_SET_")) or (q and key == "PRICE_CLEAR"):
        if key == "PRICE_CLEAR":
            update_prefs(conn, chat_id, max_price=None)
        else:
            val = int(key.split("_")[-1])
            update_prefs(conn, chat_id, max_price=val)
        # Stay on dates menu and show confirmation
        try:
            await q.answer("✅ עודכן")
        except Exception:
            pass
        kb = dates_menu_kb()
        try:
            await q.edit_message_text("🗓 בחר/י טווח תאריכים", reply_markup=kb, parse_mode=ParseMode.HTML)
        except BadRequest:
            await context.bot.send_message(chat_id=chat_id, text="🗓 בחר/י טווח תאריכים", reply_markup=kb, parse_mode=ParseMode.HTML)
        return

    # Seats
    if key in ("SEATS", "מושבים"):
        kb = seats_menu_kb(prefs)
        if q:
            try:
                await q.answer()
            except Exception:
                pass
            try:
                await q.edit_message_text("🪑 מינימום מושבים", reply_markup=kb)
                return
            except BadRequest:
                pass
        await context.bot.send_message(chat_id=chat_id, text="🪑 מינימום מושבים", reply_markup=kb)
        return

    if (q and key.startswith("SEATS_SET_")) or (q and key == "SEATS_CLEAR"):
        if key == "SEATS_CLEAR":
            update_prefs(conn, chat_id, min_seats=1)
        else:
            val = int(key.split("_")[-1])
            update_prefs(conn, chat_id, min_seats=val)
        await q.edit_message_text("✅ עודכן. חוזר לתפריט.", reply_markup=main_menu_kb())
        return

    # Dates
    if key in ("DATES", "תאריכים"):
        kb = dates_menu_kb()
        if q:
            try:
                await q.answer()
            except Exception:
                pass
            try:
                await q.edit_message_text("🗓 בחר/י טווח תאריכים", reply_markup=kb, parse_mode=ParseMode.HTML)
                return
            except BadRequest:
                pass
        await context.bot.send_message(chat_id=chat_id, text="🗓 בחר/י טווח תאריכים", reply_markup=kb, parse_mode=ParseMode.HTML)
        return

    if q and key in ("DATES_WEEK", "DATES_MONTH", "DATES_CLEAR"):
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
        try:
            await q.answer("✅ עודכן")
        except Exception:
            pass
        kb = dates_menu_kb()
        try:
            await q.edit_message_text("🗓 בחר/י טווח תאריכים", reply_markup=kb, parse_mode=ParseMode.HTML)
        except BadRequest:
            await context.bot.send_message(chat_id=chat_id, text="🗓 בחר/י טווח תאריכים", reply_markup=kb, parse_mode=ParseMode.HTML)
        return

    if (not q) and data and re.match(r"^\d{4}-\d{2}-\d{2},\d{4}-\d{2}-\d{2}$", data):
        ds, de = data.strip().split(",")
        update_prefs(conn, chat_id, date_start=ds, date_end=de)
        await context.bot.send_message(chat_id=chat_id, text="✅ טווח תאריכים נשמר.")
        await context.bot.send_message(chat_id=chat_id, text="🗓 בחר/י טווח תאריכים", reply_markup=dates_menu_kb(), parse_mode=ParseMode.HTML)
        return

    # Trip length
    if key in ("TRIP", "אורך טיול"):
        kb = trip_len_menu_kb()
        if q:
            try:
                await q.answer()
            except Exception:
                pass
            try:
                await q.edit_message_text("🧾 אורך טיול", reply_markup=kb)
                return
            except BadRequest:
                pass
        await context.bot.send_message(chat_id=chat_id, text="🧾 אורך טיול", reply_markup=kb)
        return

    if q and (key.startswith("TRIP_SET_") or key == "TRIP_CLEAR"):
        if key == "TRIP_CLEAR":
            update_prefs(conn, chat_id, min_days=None, max_days=None)
        else:
            part = key.split("_")[-1]
            lo, hi = part.split("-")
            update_prefs(conn, chat_id, min_days=int(lo), max_days=int(hi))
        # Stay on dates menu and show confirmation
        try:
            await q.answer("✅ עודכן")
        except Exception:
            pass
        kb = dates_menu_kb()
        try:
            await q.edit_message_text("🗓 בחר/י טווח תאריכים", reply_markup=kb, parse_mode=ParseMode.HTML)
        except BadRequest:
            await context.bot.send_message(chat_id=chat_id, text="🗓 בחר/י טווח תאריכים", reply_markup=kb, parse_mode=ParseMode.HTML)
        return

    # Visibility
    if key in ("VIS", "נראות"):
        kb = visibility_menu_kb(prefs)
        if q:
            try:
                await q.answer()
            except Exception:
                pass
            try:
                await q.edit_message_text("👀 נראות דילים", reply_markup=kb)
                return
            except BadRequest:
                pass
        await context.bot.send_message(chat_id=chat_id, text="👀 נראות דילים", reply_markup=kb)
        return

    if q and key.startswith("VIS_TOGGLE_"):
        flag = key.split("_")[-1].lower()
        cur = int(prefs.get(f"show_{flag}") or 0)
        update_prefs(conn, chat_id, **{f"show_{flag}": 0 if cur else 1})
        prefs = get_prefs(conn, chat_id)
        kb = visibility_menu_kb(prefs)
        await q.edit_message_text("👀 נראות דילים", reply_markup=kb)
        return

    # Saved list view
    if key in ("SAVED", "שמורים"):
        flights = query_saved(conn, chat_id, limit=max_items)
        await _send_feed(update, context, flights, header="⭐ טיסות שמורות")
        return

    if q and key.startswith("SAVE::"):
        fkey = data.split("::", 1)[1]
        conn.execute("INSERT OR IGNORE INTO saved_flights(chat_id, flight_key) VALUES(?,?)", (chat_id, fkey))
        conn.commit()
        await q.answer("⭐ נשמר")
        return

    if q and key.startswith("UNSAVE::"):
        fkey = data.split("::", 1)[1]
        conn.execute("DELETE FROM saved_flights WHERE chat_id=? AND flight_key=?", (chat_id, fkey))
        conn.commit()
        await q.answer("🗑 הוסר")
        return

    # default
    if q:
        try:
            await q.answer()
        except Exception:
            pass
    await context.bot.send_message(chat_id=chat_id, text="🏠 תפריט ראשי", reply_markup=main_menu_kb())


from telegram.ext import CommandHandler
import sqlite3, sys, importlib, pathlib

async def cmd_diag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    import config as cfg
    import db as dbm, logic as lg, telegram_view as tv, handlers as hd, utils as ut
    mods = [cfg, dbm, lg, tv, hd, ut]
    lines = []
    for m in mods:
        p = getattr(m, "__file__", "?")
        fv = getattr(m, "__file_version__", "")
        lines.append(f"{m.__name__}: {p} {fv}")
    try:
        conn = sqlite3.connect(getattr(cfg, "DB_PATH", "flights.db"))
        cur = conn.execute("SELECT DISTINCT price FROM flights WHERE price IS NOT NULL ORDER BY price")
        prices = [str(r[0]) for r in cur.fetchall()]
    except Exception as e:
        prices = [f"err: {e}"]
    txt = "🧪 DIAG\n" + "\n".join(lines) + "\nprices: " + ", ".join(prices[:20])
    try:
        await update.message.reply_text(txt)
    except Exception:
        await context.bot.send_message(chat_id=chat_id, text=txt)

def register_diag_handler(app):
    try:
        app.add_handler(CommandHandler("diag", cmd_diag))
    except Exception:
        pass
