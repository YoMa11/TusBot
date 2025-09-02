from __future__ import annotations
import asyncio, logging, sqlite3, os
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
import config
import logic as lg
from handlers import handle_start, handle_callback  # keep public API
from db import ensure_schema, open_db

logging.basicConfig(level=getattr(config, "LOG_LEVEL", logging.INFO), format=getattr(config, "LOG_FORMAT", "%(asctime)s - %(levelname)s - %(message)s"))
log = logging.getLogger("tustus")

def _log_startup_info():
    try:
        log.info("🚀 הפעלה (גרסה %s) | interval=%ss | DB=%s", getattr(config, "SCRIPT_VERSION", "?"), config.INTERVAL, os.path.abspath(config.DB_PATH))
        log.info("🛰️ ניטור URL = %s", getattr(config, "URL", "<missing>"))
    except Exception as e:
        log.warning("Startup info failed: %s", e)

async def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CallbackQueryHandler(handle_callback))

    conn = open_db(config.DB_PATH)
    ensure_schema(conn)
    _log_startup_info()

    # PTB JobQueue (every INTERVAL)
    async def _tick(_):
        try:
            await lg.run_monitor(conn, app)
        except Exception as e:
            log.exception("run_monitor tick failed")
    app.job_queue.run_repeating(_tick, interval=config.INTERVAL, first=1, name="monitor")

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    log.info("Application started")
    try:
        await asyncio.Event().wait()
    finally:
        await app.stop()
        log.info("Application.stop() complete")

if __name__ == "__main__":
    asyncio.run(main())
