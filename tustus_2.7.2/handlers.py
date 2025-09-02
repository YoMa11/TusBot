from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import sqlite3

from telegram_view import build_main_menu_from_db

async def safe_edit(message, text: str, reply_markup=None, parse_mode=None):
    try:
        current_text = message.text or ""
        current_markup = getattr(message, "reply_markup", None)
        if current_text == text and str(current_markup) == str(reply_markup):
            return  # אין שינוי — לא נשלח edit למנוע BadRequest
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        # אם אין הרשאה לערוך (למשל הודעה ישנה) — נשלח חדשה
        await message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn: sqlite3.Connection = context.application.bot_data["conn"]
    kb = build_main_menu_from_db(conn)
    await update.effective_chat.send_message(
        "ברוך הבא! תפריט ראשי (מתוך ה־DB):",
        reply_markup=kb,
        parse_mode=ParseMode.HTML,
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn: sqlite3.Connection = context.application.bot_data["conn"]
    q = update.callback_query
    await q.answer()
    data = q.data or ""

    if data == "refresh":
        kb = build_main_menu_from_db(conn)
        await safe_edit(q.message, "תפריט מעודכן מה־DB:", reply_markup=kb)
        return
    if data == "help" or data == "noop":
        await q.edit_message_text("בחר ערך מתוך התפריט למעלה.", reply_markup=q.message.reply_markup)
        return

    # פילטרים בסיסיים (דמו)
    prefix, _, value = data.partition(":")
    title = {"dest":"יעד", "air":"חברה", "date":"תאריך", "price":"מחיר"}.get(prefix, "בחירה")
    await safe_edit(q.message, f"נבחר {title}: <b>{value}</b>", parse_mode=ParseMode.HTML)
