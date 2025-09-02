from __future__ import annotations
import asyncio
import logging
import os
import sqlite3
from datetime import timedelta

import config
import db as dbmod
import logic as lg

from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from handlers import handle_start, handle_callback

# ---- logging ----
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT,
    handlers=[logging.StreamHandler()]
)
if config.LOG_TO_FILE:
    try:
        fh = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
        fh.setFormatter(logging.Formatter(config.LOG_FORMAT))
        logging.getLogger().addHandler(fh)
    except Exception as e:
        logging.getLogger().warning("Could not add file handler: %s", e)

log = logging.getLogger("tustus")

def _connect_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

async def _job_monitor(context: ContextTypes.DEFAULT_TYPE) -> None:
    app = context.application
    conn = app.bot_data.get("conn")
    if conn is None:
        # Safety: reconnect if needed
        conn = _connect_db(config.DB_PATH)
        dbmod.ensure_schema(conn)
        app.bot_data["conn"] = conn
    try:
        await lg.run_monitor(conn, app)
    except Exception as e:
        logging.exception("run_monitor tick failed")

def main() -> None:
    # DB
    conn = _connect_db(config.DB_PATH)
    dbmod.ensure_schema(conn)

    # Bot
    app = Application.builder().token(config.BOT_TOKEN).build()

    # Save DB/app for handlers & jobs
    app.bot_data["conn"] = conn
    app.bot_data["db_path"] = config.DB_PATH

    # Handlers
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CallbackQueryHandler(handle_callback))

    # JobQueue
    app.job_queue.run_repeating(
        _job_monitor,
        interval=timedelta(seconds=config.INTERVAL),
        first=1.0,
        name="monitor"
    )
    log.info("🚀 הפעלה (גרסה V2.7.4a clean full / %s) | interval=%ss | DB=%s", config.SCRIPT_VERSION, config.INTERVAL, os.path.abspath(config.DB_PATH))

    # Polling
    app.run_polling(allowed_updates=None)

if __name__ == "__main__":
    main()
