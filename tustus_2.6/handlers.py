# -*- coding: utf-8 -*-
from __future__ import annotations
import logging, asyncio
from typing import Any
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from telegram_view import build_main_menu

log = logging.getLogger("tustus.handlers")

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    txt = (
        "ברוך הבא ל־Tustus ✈️\n"
        "בחר אחת מהאפשרויות להלן (תפריט מלא במסך הראשי):"
    )
    await update.effective_chat.send_message(
        txt,
        reply_markup=build_main_menu({}),
        parse_mode=ParseMode.HTML
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q:
        await q.answer()
        data = q.data or ""
        # דוגמאות לטיפול בסיסי
        if data == "REFRESH":
            await q.edit_message_text("מרענן נתונים…", reply_markup=build_main_menu({}))
        elif data == "PRICES":
            await q.edit_message_text("תצוגת מחירים (כפי שב־DB).", reply_markup=build_main_menu({}))
        elif data == "DESTS":
            await q.edit_message_text("רשימת יעדים מה־DB.", reply_markup=build_main_menu({}))
        elif data == "FILTER_NEW":
            await q.edit_message_text("מציג טיסות חדשות.", reply_markup=build_main_menu({"new": True}))
        elif data == "DATES":
            await q.edit_message_text("בחירת תאריכים.", reply_markup=build_main_menu({}))
        elif data == "HELP":
            await q.edit_message_text("עזרה ומידע.", reply_markup=build_main_menu({}))
        else:
            await q.edit_message_text("עודכן.", reply_markup=build_main_menu({}))
