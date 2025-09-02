# -*- coding: utf-8 -*-
from __future__ import annotations

import os, sys, logging, importlib, sqlite3, pathlib, asyncio
from typing import Any
from datetime import timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

import config
import db
import logic as lg

# ניהול לוגים
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger("tustus")

ROOT = pathlib.Path(__file__).resolve().parent

def _verify_origin(mod_name: str) -> pathlib.Path:
    m = importlib.import_module(mod_name)
    p = pathlib.Path(getattr(m, "__file__", "")).resolve()
    if ROOT not in p.parents and p.parent != ROOT:
        raise ImportError(f"Module {mod_name} loaded from {p}, expected under {ROOT}")
    return p

async def _tick(context: ContextTypes.DEFAULT_TYPE) -> None:
    app = context.application
    conn = app.bot_data.get("conn")
    try:
        await lg.run_monitor(conn, app)
    except Exception as e:
        log.error("run_monitor tick failed: %s", e, exc_info=True)

def _get_token() -> str:
    # העדפה לקונפיג (לא לשבור תאימות), ניתן לדרוס עם משתנה סביבה TELEGRAM_BOT_TOKEN_RUNTIME
    return os.environ.get("TELEGRAM_BOT_TOKEN_RUNTIME", config.TELEGRAM_BOT_TOKEN)

async def main() -> None:
    # וידוא טעינת מודולים מהתיקייה הנוכחית
    loaded = {m: str(_verify_origin(m)) for m in ("config","db","handlers","logic","telegram_view","utils")}
    log.info("✅ Modules origin OK: %s", loaded)
    log.info("📦 VERSION: %s", getattr(config, "VERSION", "?"))

    # DB
    conn = db.connect_db(os.path.join(ROOT, config.DB_PATH))
    with open(os.path.join(ROOT, "schema.sql"), "r", encoding="utf-8") as f:
        schema = f.read()
    db.ensure_db(conn, schema)
    log.info("✅ DB schema ensured")
    log.info("📁 DB path: %s", os.path.join(ROOT, config.DB_PATH))

    # בוט
    token = _get_token()
    app: Application = ApplicationBuilder().token(token).build()
    app.bot_data["conn"] = conn

    # Handlers
    from handlers import handle_start, handle_callback
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CallbackQueryHandler(handle_callback))

    # תזמון יחיד
    for job in app.job_queue.get_jobs_by_name("monitor"):
        job.schedule_removal()
    app.job_queue.run_repeating(_tick, interval=timedelta(seconds=config.INTERVAL), first=3, name="monitor")
    log.info("🗓️  JobQueue repeating task scheduled (interval=%ss)", config.INTERVAL)

    # הפעלה
    await app.initialize()
    await app.start()
    try:
        await app.updater.start_polling()
        log.info("Application started")
        # ריצה עד עצירה
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        conn.close()
        log.info("Application.stop() complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted.")
