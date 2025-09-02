from __future__ import annotations
import logging
from typing import Optional

import config
import db as DB

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest

__file_version__ = "tustus_2.7.4a"
log = logging.getLogger("tustus.handlers")

def build_main_menu(data: dict) -> InlineKeyboardMarkup:
    rows = []
    # First row: quick filters
    rows.append([
        InlineKeyboardButton("כל הטיסות", callback_data="menu"),
        InlineKeyboardButton("יעדים", callback_data="destinations"),
        InlineKeyboardButton("מחירים", callback_data="prices")
    ])
    # Second row: stats if available
    stats = data.get("stats", {})
    if stats:
        rows.append([InlineKeyboardButton(f"סה\"כ: {stats.get('total',0)} | 24ש׳: {stats.get('fresh_24h',0)}", callback_data="noop")])
    # Price buckets
    pb = data.get("price_buckets", {})
    if pb:
        label = " | ".join(f"{k}:{v}" for k,v in pb.items())
        rows.append([InlineKeyboardButton(label or "מחירים", callback_data="prices")])
    # Footer
    rows.append([InlineKeyboardButton("רענון ↻", callback_data="menu")])
    return InlineKeyboardMarkup(rows)

async def _render_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    app = context.application
    conn = app.bot_data.get("conn")
    if conn is None:
        await update.effective_message.reply_text("DB לא מחובר עדיין.")
        return
    stats = DB.get_counts(conn)
    prices = DB.get_price_buckets(conn)
    markup = build_main_menu({"stats": stats, "price_buckets": prices})
    msg = update.effective_message
    if msg:
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text("תפריט ראשי", reply_markup=markup)
            else:
                await msg.reply_text("תפריט ראשי", reply_markup=markup)
        except BadRequest as e:
            if "Message is not modified" in str(e):
                log.debug("Ignored tg BadRequest: message is not modified")
            else:
                log.exception("Telegram BadRequest")

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_menu(update, context)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    data = q.data if q else ""
    if data in ("menu", "prices", "destinations", "noop"):
        await _render_menu(update, context)
    else:
        await _render_menu(update, context)
