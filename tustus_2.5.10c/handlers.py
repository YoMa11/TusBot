# -*- coding: utf-8 -*-
from __future__ import annotations
import logging, sqlite3
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, CallbackQueryHandler
from telegram_view import build_home_kb, build_dests_kb
import logic

HOME_TEXT = (
    "ברוך הבא ל־Tustus 🛫\n"
    "בחר פעולה מהתפריט: הכל במקום אחד במסך הבית.\n"
)

async def show_home(update: Update, context: ContextTypes.DEFAULT_TYPE, *, edit: bool=False):
    kb = build_home_kb()
    if update.callback_query:
        await update.callback_query.answer()
        if edit and update.effective_message:
            await update.effective_message.edit_text(HOME_TEXT, reply_markup=kb)
            return
    await update.effective_chat.send_message(HOME_TEXT, reply_markup=kb)  # type: ignore

async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_home(update, context)

async def on_home_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data if q else ""
    await (q.answer() if q else None)

    # Special destination action
    if data == "DESTS_SELECT_ALL":
        txt = await logic.ui_dests_select_all(context.application)
        if update.effective_message:
            await update.effective_message.edit_text(txt, reply_markup=build_dests_kb())
        return

    if data == "HOME_REFRESH":
        await show_home(update, context, edit=True)
        return

    mapping = {
        "HOME_ALL": logic.ui_all_flights,
        "HOME_PRICES": logic.ui_prices,
        "HOME_DESTS": logic.ui_dests,
        "HOME_ALERTS": logic.ui_alerts,
        "HOME_SETTINGS": logic.ui_settings,
        "HOME_MORE": logic.ui_more,
    }
    fn = mapping.get(data)
    if fn is None:
        await show_home(update, context, edit=True)
        return
    txt = await fn(context.application)
    # On destinations, use dedicated keyboard with 'Select All'
    kb = build_dests_kb() if data == "HOME_DESTS" else build_home_kb()
    if update.effective_message:
        await update.effective_message.edit_text(txt, reply_markup=kb)

def register_home_handlers(app: Application, conn: sqlite3.Connection) -> None:
    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(CallbackQueryHandler(on_home_cb))
    logging.info("✅ register_home_handlers installed")
