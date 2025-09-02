from __future__ import annotations
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def chunk(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def build_main_menu_from_db(conn) -> InlineKeyboardMarkup:
    # יוצר תפריט מלא מה-DB
    from db import get_distinct, get_price_ranges
    dests = get_distinct(conn, "destination")
    airlines = get_distinct(conn, "airline")
    dates = get_distinct(conn, "depart_date")
    prices = get_price_ranges(conn)

    rows = []

    # כפתורי יעדים
    if dests:
        rows.append([InlineKeyboardButton("🗺️ יעדים (בחר)", callback_data="noop")])
        for row in chunk([InlineKeyboardButton(d, callback_data=f"dest:{d}") for d in dests], 3):
            rows.append(row)

    # כפתורי חברות
    if airlines:
        rows.append([InlineKeyboardButton("✈️ חברות תעופה", callback_data="noop")])
        for row in chunk([InlineKeyboardButton(a, callback_data=f"air:{a}") for a in airlines], 3):
            rows.append(row)

    # כפתורי תאריכים
    if dates:
        rows.append([InlineKeyboardButton("📅 תאריכים", callback_data="noop")])
        for row in chunk([InlineKeyboardButton(dt, callback_data=f"date:{dt}") for dt in dates], 3):
            rows.append(row)

    # מחירים
    if prices:
        rows.append([InlineKeyboardButton("💲 מחירים", callback_data="noop")])
        for row in chunk([InlineKeyboardButton(p, callback_data=f"price:{p}") for p in prices], 3):
            rows.append(row)

    # שורה תחתונה
    rows.append([
        InlineKeyboardButton("🔄 רענון", callback_data="refresh"),
        InlineKeyboardButton("ℹ️ עזרה", callback_data="help")
    ])

    return InlineKeyboardMarkup(rows)
