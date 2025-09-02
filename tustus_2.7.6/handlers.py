# handlers.py
from __future__ import annotations
from typing import Tuple, List
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import db
import logic
from telegram_view import build_destinations_keyboard

# ===== Greeting =====
def _greeting_line(version: str) -> str:
    # שורת פתיחה בלבד + גרסה (כפי שביקשת)
    # הומוריסטית/סארקאסטית – אפשר לגוון בהמשך ברנדומליות כל שעתיים
    return f"🚀☕️ תפסנו עוד דיל שממריא מהר יותר מהקפה של הבוקר.\nvtustus_{version}"

# ===== Main screen builders =====
def _build_dest_block(conn, selected: List[str]) -> InlineKeyboardMarkup:
    rows = logic.list_all_destinations_with_country(conn)  # (city, country, _)
    return build_destinations_keyboard(rows, selected)

def _build_main_screen(conn, selected: List[str]) -> Tuple[str, InlineKeyboardMarkup]:
    greet = _greeting_line(version=logic.get_version())
    km = _build_dest_block(conn, selected)
    return greet + "\u2063", km  # נון-פרינט למניעת "Message is not modified"

# ===== Public Handlers =====
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = db.get_conn()
    db.ensure_schema(conn)
    # ננהל בחירות בזיכרון (בעתיד נעביר ל־DB פר־משתמש)
    context.user_data.setdefault("selected", [])
    text, km = _build_main_screen(conn, context.user_data["selected"])
    await update.effective_message.reply_text(text, reply_markup=km)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()

    data = (q.data or "").strip()
    selected: List[str] = context.user_data.setdefault("selected", [])

    if data == "refresh":
        conn = db.get_conn()
        text, km = _build_main_screen(conn, selected)
        # מניעת BadRequest: Message is not modified
        old_text = q.message.text or ""
        old_km = q.message.reply_markup
        if old_text == text and str(old_km) == str(km):
            text += "\u2063"
        await q.edit_message_text(text, reply_markup=km)
        return

    if data.startswith("tog:"):
        token = data[4:]
        if token == "*":
            # בחירת “כל היעדים”
            selected.clear()
            selected.append("*")
        else:
            # טוגל ליעד בודד "עיר|מדינה"
            if token in selected:
                selected.remove(token)
            else:
                # אם נבחר קודם “*” – ננקה אותו
                if "*" in selected:
                    selected.clear()
                selected.append(token)

        conn = db.get_conn()
        text, km = _build_main_screen(conn, selected)
        old_text = q.message.text or ""
        old_km = q.message.reply_markup
        if old_text == text and str(old_km) == str(km):
            text += "\u2063"
        await q.edit_message_text(text, reply_markup=km)
        return

    # ברירת מחדל – רענון
    conn = db.get_conn()
    text, km = _build_main_screen(conn, selected)
    old_text = q.message.text or ""
    old_km = q.message.reply_markup
    if old_text == text and str(old_km) == str(km):
        text += "\u2063"
    await q.edit_message_text(text, reply_markup=km)
