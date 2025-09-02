from __future__ import annotations
__version__ = "2.4.7"

import math
from datetime import datetime
from typing import List, Tuple
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

# Special markers to keep Hebrew (RTL) stable with numbers/ASCII
RLM = "\u200F"
LRM = "\u200E"

# ---------- Helpers ----------
def _rtl(line: str) -> str:
    return RLM + line

def _short(txt: str, n: int = 14) -> str:
    return txt if len(txt) <= n else txt[: n - 1] + "…"

def _commas(s: str) -> str:
    # helps prevent direction flipping around commas
    return s.replace(",", LRM + ",")

def fmt_date(iso_date: str) -> str:
    """Input 'YYYY-MM-DD' -> 'DD/MM · יום <letter>'"""
    try:
        dt = datetime.fromisoformat(iso_date)
    except Exception:
        return iso_date or ""
    wd = ["ב׳", "ג׳", "ד׳", "ה׳", "ו׳", "ש׳", "א׳"][dt.weekday()]
    return f"{dt.strftime('%d/%m')} · יום {wd}"

def format_price(f: dict) -> str:
    p = int(f.get("price") or 0)
    dest = (f.get("destination") or "")
    cur = "₪" if "אילת" in dest else "$"
    # format with thousands and keep stable direction
    return _commas(f"{cur}{p:,}")

# ---------- Cards & Pagination ----------
def format_flight_card(f: dict) -> str:
    price = format_price(f)
    seats = f.get("seats")
    seats_txt = str(seats) if seats not in (None, "", 0) else "—"

    # Build full datetimes if possible to ensure correct arrow direction
    def _combine(dt_str, tm_str):
        try:
            if not dt_str or not tm_str:
                return None
            return datetime.strptime(dt_str.strip() + " " + tm_str.strip(), "%Y-%m-%d %H:%M")
        except Exception:
            return None

    go_dt = _combine(f.get("go_date"), f.get("go_depart"))
    go_arr = _combine(f.get("go_date"), f.get("go_arrive"))
    back_dt = _combine(f.get("back_date"), f.get("back_depart"))
    back_arr = _combine(f.get("back_date"), f.get("back_arrive"))

    def _leg_line(label, d, t1, t2):
        t1s = (f.get(t1) or "")
        t2s = (f.get(t2) or "")
        arrow = "→"
        if d[0] and d[1]:
            # if first is after second, flip arrow to visually show later time
            if d[0] and d[1] and d[0] > d[1]:
                arrow = "↦"  # still right-pointing but distinct
        return _rtl(f"{label} {fmt_date(f.get(d[2]) or '')}   {t1s} {arrow} {t2s}")

    go_line = _rtl(f"🛫 {fmt_date(f.get('go_date') or '')}   {(f.get('go_depart') or '')} → {(f.get('go_arrive') or '')}")
    back_line = _rtl(f"🛬 {fmt_date(f.get('back_date') or '')}   {(f.get('back_depart') or '')} → {(f.get('back_arrive') or '')}")

    # Flight age
    first_seen = f.get("first_seen")
    age_txt = ""
    try:
        if first_seen:
            dt = datetime.strptime(first_seen[:19], "%Y-%m-%d %H:%M:%S")
            delta = datetime.utcnow() - dt
            mins = int(delta.total_seconds()//60)
            if mins < 60:
                age_txt = f"{mins} דק׳"
            elif mins < 24*60:
                age_txt = f"{mins//60} שע׳ {mins%60} דק׳"
            else:
                days = mins//(24*60)
                age_txt = f"{days} ימ׳"
    except Exception:
        pass
    age_line = _rtl(f"⏱ פעילה: {age_txt}") if age_txt else ""

    lines = [
        _rtl(f"🌍 <b>{(f.get('destination') or '').strip()}</b>"),
        go_line,
        back_line,
        _rtl(f"💰 מחיר: {price}    🪑 מושבים: {seats_txt}"),
    ]
    if age_line:
        lines.append(age_line)

    link = (f.get("link") or "").strip()
    key = (f.get("flight_key") or "")[:12]
    if link:
        lines.append(_rtl(f"<a href=\"{link}\">לרכישה</a> · <code>{key}</code>"))
    else:
        lines.append(_rtl(f"<code>{key}</code>"))
    return "\n".join(lines)

def chunk_messages(cards: List[str], header: str = "", max_chars: int = 3500) -> List[str]:
    chunks = []
    cur = (header + "\n\n").strip() if header else ""
    for c in cards:
        # add separator between cards
        card = c + "\n" + _rtl("—" * 20) + "\n"
        if len(cur) + len(card) > max_chars and cur:
            chunks.append(cur.rstrip())
            cur = header + "\n\n" if header else ""
        cur += card
    if cur.strip():
        chunks.append(cur.rstrip())
    return chunks

def paginate_cards(items: list[dict], prefs: dict | None, page: int = 1, page_size: int = 10, show_active_time: bool = True):
    # Build formatted text cards and a simple prev/next nav
    total = len(items)
    pages = max(1, math.ceil(total / page_size))
    page = max(1, min(page, pages))
    start = (page - 1) * page_size
    subset = items[start : start + page_size]
    cards = [format_flight_card(f) for f in subset]

    # nav kb
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton("◀︎", callback_data=f"PAGE::{page-1}"))
    buttons.append(InlineKeyboardButton(f"{page}/{pages}", callback_data="NOP"))
    if page < pages:
        buttons.append(InlineKeyboardButton("▶︎", callback_data=f"PAGE::{page+1}"))

    kb_rows = [buttons] if buttons else []
    kb_rows.append([InlineKeyboardButton("בית 🏠", callback_data="HOME")])
    return cards, InlineKeyboardMarkup(kb_rows), page, pages

# ---------- Keyboards ----------
def main_menu_kb() -> InlineKeyboardMarkup:
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
         InlineKeyboardButton("איפוס ♻️", callback_data="RESET"),
         InlineKeyboardButton("בית 🏠", callback_data="HOME")],
    ]
    return InlineKeyboardMarkup(rows)

def price_menu_kb(conn: sqlite3.Connection, prefs: dict, page: int = 1, page_size: int = 12) -> InlineKeyboardMarkup:
    """
    Builds price buttons dynamically from distinct price values present in DB (USD for most, ₪ for אילת).
    Pagination supported via PRICE_PAGE_{n}.
    """
    # Collect distinct prices
    cur = conn.execute("SELECT DISTINCT price FROM flights WHERE price IS NOT NULL ORDER BY price")
    prices = [int(r[0]) for r in cur.fetchall() if r[0] is not None]
    if not prices:
        prices = [100,150,200,250,300,350,400,500]
    # Paginate
    total = len(prices)
    pages = max(1, (total + page_size - 1)//page_size)
    page = max(1, min(page, pages))
    start = (page-1)*page_size
    page_slice = prices[start:start+page_size]

    # Determine currency marker for label only (actual filter number is bare)
    cur_sym = "$"  # label only
    # Build buttons (2 columns)
    kb_rows = []
    row = []
    for i, val in enumerate(page_slice, 1):
        row.append(InlineKeyboardButton(f"{val}{cur_sym}", callback_data=f"PRICE_SET_{val}"))
        if i % 4 == 0:
            kb_rows.append(row); row = []
    if row: kb_rows.append(row)
    # Nav row
    nav = []
    if page > 1: nav.append(InlineKeyboardButton("◀︎", callback_data=f"PRICE_PAGE_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page}/{pages}", callback_data="PRICE_NOP"))
    if page < pages: nav.append(InlineKeyboardButton("▶︎", callback_data=f"PRICE_PAGE_{page+1}"))
    if nav: kb_rows.append(nav)
    # Clear / Home
    kb_rows.append([InlineKeyboardButton("נקה", callback_data="PRICE_CLEAR"), InlineKeyboardButton("🏠 בית", callback_data="HOME")])
    return InlineKeyboardMarkup(kb_rows)

def seats_menu_kb(prefs: dict) -> InlineKeyboardMarkup:
    cur = int(prefs.get("min_seats") or 1)
    row = []
    for v in [1,2,3,4,5]:
        mark = "✅" if v == cur else "⬜️"
        row.append(InlineKeyboardButton(f"{mark} {v}", callback_data=f"SEATS_SET_{v}"))
    return InlineKeyboardMarkup([row, [InlineKeyboardButton("נקה", callback_data="SEATS_CLEAR"),
                                       InlineKeyboardButton("בית 🏠", callback_data="HOME")]])

def dates_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("שבוע קדימה", callback_data="DATES_WEEK"),
         InlineKeyboardButton("חודש קדימה", callback_data="DATES_MONTH")],
        [InlineKeyboardButton("הזנה ידנית", callback_data="DATES_MANUAL"),
         InlineKeyboardButton("נקה", callback_data="DATES_CLEAR")],
        [InlineKeyboardButton("בית 🏠", callback_data="HOME")]
    ])

def trip_len_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("2–3", callback_data="TRIP_SET_2-3"),
         InlineKeyboardButton("4–6", callback_data="TRIP_SET_4-6"),
         InlineKeyboardButton("7–10", callback_data="TRIP_SET_7-10")],
        [InlineKeyboardButton("נקה", callback_data="TRIP_CLEAR"),
         InlineKeyboardButton("בית 🏠", callback_data="HOME")]
    ])

def visibility_menu_kb(prefs: dict) -> InlineKeyboardMarkup:
    def mark(flag: str) -> str:
        return "✅" if int(prefs.get(flag) or 0) else "⬜️"
    rows = [
        [InlineKeyboardButton(f"חדשים {mark('show_new')}", callback_data="VIS_TOGGLE_new"),
         InlineKeyboardButton(f"פעילים {mark('show_active')}", callback_data="VIS_TOGGLE_active")],
        [InlineKeyboardButton(f"הוסרו {mark('show_removed')}", callback_data="VIS_TOGGLE_removed"),
         InlineKeyboardButton("בית 🏠", callback_data="HOME")]
    ]
    return InlineKeyboardMarkup(rows)

def feed_nav_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("בית 🏠", callback_data="HOME"),
         InlineKeyboardButton("לפי העדפות 🎯", callback_data="BY_PREFS"),
         InlineKeyboardButton("שמורים ⭐", callback_data="SAVED")]
    ])

def destinations_page(selected_csv: str, page: int, page_size: int, dests_all: list[str]) -> InlineKeyboardMarkup:
    selected = set([d.strip() for d in (selected_csv or "").split(",") if d.strip()])
    start = max(0, (page - 1) * page_size)
    items = dests_all[start:start + page_size]

    rows, row = [], []
    for d in items:
        mark = "✅ " if d in selected else "⬜️ "
        row.append(InlineKeyboardButton(mark + _short(d, 14), callback_data=f"DEST_TOGGLE::{d}|PAGE_{page}"))
        if len(row) == 3:
            rows.append(row); row = []
    if row: rows.append(row)

    total_pages = max(1, math.ceil(len(dests_all) / page_size))
    nav = []
    if page > 1: nav.append(InlineKeyboardButton("◀︎", callback_data=f"DESTS_PAGE_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="NOP"))
    if page < total_pages: nav.append(InlineKeyboardButton("▶︎", callback_data=f"DESTS_PAGE_{page+1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton("שמור וחזור ✅", callback_data="DEST_SAVE")])
    rows.append([InlineKeyboardButton("בית 🏠", callback_data="HOME")])
    return InlineKeyboardMarkup(rows)
# __build__: tusbot v2.4.7 @ 2025-08-29 23:51:11
