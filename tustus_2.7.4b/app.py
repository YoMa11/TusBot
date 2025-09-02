# app.py
from __future__ import annotations
import asyncio, logging, sqlite3, os
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

import config
import logic as lg
from handlers import handle_start, handle_callback

# ---------- logging ----------
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8") if config.LOG_TO_FILE else logging.NullHandler(),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("tustus")

# ---------- helpers ----------
def open_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    return conn

async def _job_monitor(app: Application):
    conn = open_conn()
    try:
        await lg.run_monitor(conn, app)
    finally:
        conn.close()

def main():
    application = Application.builder().token(config.BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(CallbackQueryHandler(handle_callback))

    # schedule repeating job
    job_queue = application.job_queue
    job_queue.run_repeating(lambda _: asyncio.create_task(_job_monitor(application)),
                            interval=config.INTERVAL, first=2, name="monitor")
    log.info("🚀 הפעלה (גרסה V? / ?) | interval=%ss | DB=%s", config.INTERVAL, config.DB_PATH)
    application.run_polling(allowed_updates=None)

if __name__ == "__main__":
    main()
