# -*- coding: utf-8 -*-
from __future__ import annotations
import logging, os, sys, asyncio, sqlite3
from telegram.ext import Application, ApplicationBuilder
from telegram.request import HTTPXRequest

import config
from db import connect
import logic as lg
from handlers import register_home_handlers

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def _verify_env_and_paths() -> None:
    config.enforce_local_imports()
    logging.info(f"🚀 הפעלה (גרסה V5.1.0 / v{config.PACKAGE_VERSION}) | interval={config.INTERVAL}s | DB=./flights.db")
    logging.info("✅ DB schema ensured")

async def _tick(app: Application, conn: sqlite3.Connection):
    try:
        await lg.run_monitor(conn, app)
    except Exception:
        logging.exception("run_monitor tick failed")

async def _setup_scheduler(app: Application, conn: sqlite3.Connection):
    jq = app.job_queue
    if jq:
        logging.info("Adding job tentatively -- it will be properly scheduled when the scheduler starts")
        jq.run_repeating(lambda *_: asyncio.create_task(_tick(app, conn)), interval=config.INTERVAL, name="monitor")
        logging.info("🗓️  JobQueue repeating task scheduled (interval=%ss)", config.INTERVAL)
    else:
        logging.warning("⚠️ JobQueue לא זמין — ניטור ירוץ בלולאת fallback")
        async def fallback():
            while True:
                await _tick(app, conn)
                await asyncio.sleep(config.INTERVAL)
        app.create_task(fallback())

def main() -> None:
    _verify_env_and_paths()
    conn = connect(config.DB_PATH)
    logging.info("📁 DB path: %s", config.DB_PATH)
    logging.info("🔎 DB attached: %s", {'seq': 0, 'name': 'main', 'file': config.DB_PATH})

    if not config.TELEGRAM_TOKEN:
        logging.warning("⚠️ TELEGRAM_TOKEN is empty. Set it in environment or .env")
    request = HTTPXRequest()
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).request(request).build()

    register_home_handlers(app, conn)

    async def runner():
        await app.bot.delete_webhook(drop_pending_updates=False)
        await _setup_scheduler(app, conn)
        await app.initialize()
        await app.start()
        logging.info("Application started")
        await app.updater.start_polling(drop_pending_updates=False)
        try:
            await asyncio.Event().wait()
        finally:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()
            logging.info("Application.stop() complete")

    asyncio.run(runner())

if __name__ == "__main__":
    main()
