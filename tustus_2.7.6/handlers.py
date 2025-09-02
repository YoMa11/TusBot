
from __future__ import annotations
from typing import Tuple, Optional
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import db
import logic
import config
from utils_summary import render_dest_summary_leaderboard
from telegram_view import build_destinations_keyboard

# ===== Greeting (header) =====
def _greeting_line(version: str) -> str:
    return f"🚀☕️ תפסנו עוד דיל שממריא מהר יותר מהקפה של הבוקר.\nvtustus_{version}\u2063"

# ===== Build main screen (text + keyboard) =====
def _build_main_screen(selected: Optional[str] = None) -> Tuple[str, InlineKeyboardMarkup]:
    conn = db.get_conn()
    text = _greeting_line(getattr(config, "SCRIPT_VERSION", "V2.x"))
    rows = logic.get_dest_rows_for_keyboard(conn)  # [(city, country, cnt)]
    km = build_destinations_keyboard(rows, selected or "*")
    return text, km

# ===== Handlers =====
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text, km = _build_main_screen(selected="*")
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=km)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    await q.answer()
    data = q.data or ""
    selected = "*"

    # Summary (Leaderboard)
    if data == "sum":
        conn = db.get_conn()
        rows, total = logic.get_dest_summary(conn, limit=50)  # [(destination, cnt)]
        try:
            html_text = render_dest_summary_leaderboard(rows, total_count=total, top_n=10, bar_len=12)
        except Exception as e:
            html_text = f"<pre>שגיאה בבניית סיכום: {e}</pre>"
        old_text = q.message.text or ""
        if old_text == html_text:
            html_text += "\u2063"
        await q.edit_message_text(html_text, parse_mode="HTML")
        return

    # Toggle filter: 'tog:city|country'
    if data.startswith("tog:"):
        selected = data.split(":",1)[1]

    # Refresh / default
    text, km = _build_main_screen(selected)
    old_text = q.message.text or ""
    old_km = q.message.reply_markup
    if old_text == text and str(old_km) == str(km):
        text += "\u2063"
    await q.edit_message_text(text, reply_markup=km)
    return

