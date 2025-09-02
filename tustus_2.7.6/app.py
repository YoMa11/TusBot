from __future__ import annotations
import asyncio, logging, os, sys, sqlite3
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from config import BOT_TOKEN, INTERVAL, DB_PATH, LOG_LEVEL, LOG_FORMAT, LOG_TO_FILE, LOG_FILE
import db
import logic as lg
from handlers import handle_start, handle_callback  # type: ignore

# logging
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
log = logging.getLogger("tustus")

if LOG_TO_FILE:
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger().addHandler(fh)

def _ensure_db():
    conn = db.get_conn(DB_PATH)
    conn.close()
    log.info("✅ DB schema ensured")
    log.info("📁 DB path: %s", os.path.abspath(DB_PATH))

async def _job_monitor(context):
    # open a process-wide connection for read-only ops
    conn = db.get_conn(DB_PATH)
    try:
        await lg.run_monitor(conn, context.application)
    except Exception as e:
        log.exception("run_monitor tick failed")
    finally:
        conn.close()

def main():
    _ensure_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    # job queue
    app.job_queue.run_repeating(_job_monitor, interval=INTERVAL, first=5, name="monitor")
    log.info("🚀 הפעלה | interval=%ss | DB=%s", INTERVAL, DB_PATH)
    app.run_polling(allowed_updates=["message","callback_query"])

if __name__ == "__main__":
    main()
