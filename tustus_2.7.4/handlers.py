from __future__ import annotations
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import config
import db

def build_main_menu(data: dict) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("✈️ כל הטיסות", callback_data="all_flights")],
        [InlineKeyboardButton("🎯 יעדים", callback_data="destinations"),
         InlineKeyboardButton("💸 מחירים", callback_data="prices")],
        [InlineKeyboardButton("🆕 טיסות חדשות", callback_data="new"),
         InlineKeyboardButton("❌ הוסרו", callback_data="removed")],
        [InlineKeyboardButton("🔄 רענן", callback_data="refresh")],
    ]
    return InlineKeyboardMarkup(rows)

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "ברוך הבא ל־Tustus!",
        reply_markup=build_main_menu({})
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("רשימת יעדים מה־DB.", reply_markup=build_main_menu({}))
