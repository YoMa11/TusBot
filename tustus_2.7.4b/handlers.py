# handlers.py
from __future__ import annotations
from typing import Dict, Any
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

import sqlite3
import config

MENU_TEXT = "תפריט ראשי"

def build_main_menu(stats: Dict[str, Any]) -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton("מחירים", callback_data="PRICES"),
            InlineKeyboardButton("יעדים", callback_data="DESTS"),
            InlineKeyboardButton("כל הטיסות", callback_data="ALL_FLIGHTS"),
        ],
    ]
    # Optional stats lines (will be rendered as separate rows)
    if stats:
        lines = [
            f"סה\"כ: {stats.get('count',0)}",
            f"₪:{stats.get('nis',0)} | $:{stats.get('usd',0)}",
        ]
        for line in lines:
            kb.append([InlineKeyboardButton(line, callback_data="NOP")])
    return InlineKeyboardMarkup(kb)

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MENU_TEXT, reply_markup=build_main_menu({}))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    if data == "NOP":
        return
    # compute simple stats from DB
    conn = sqlite3.connect(config.DB_PATH)
    try:
        cur = conn.execute("SELECT COUNT(*), SUM(price), currency FROM show_item GROUP BY currency")
        nis = usd = 0
        total_count = 0
        for row in cur.fetchall():
            # Here row is (count, sum, currency). We only show counts by currency
            c = row[0] or 0
            total_count += c
            if (row[2] or "").strip() == "₪":
                nis = c
            elif (row[2] or "").strip() == "$":
                usd = c
        stats = {"count": total_count, "nis": nis, "usd": usd}
    finally:
        conn.close()
    await q.edit_message_text(MENU_TEXT, reply_markup=build_main_menu(stats))
