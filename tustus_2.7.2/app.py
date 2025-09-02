from __future__ import annotations
import asyncio, logging, importlib, pathlib, sqlite3, os
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from utils import setup_logging
import db as dbmod
import logic as lg

# --- לוגים
setup_logging()

# --- קונפיג (קריאה בלבד, ללא נגיעה בקובץ)
cfg = importlib.import_module("config")
BOT_TOKEN = getattr(cfg, "BOT_TOKEN", None)
DB_PATH   = getattr(cfg, "DB_PATH", "./flights.db")
INTERVAL  = int(getattr(cfg, "INTERVAL", 60))

# --- גרסה מקובץ VERSION
VERSION = pathlib.Path(__file__).with_name("VERSION").read_text(encoding="utf-8").strip()
logging.info("🚀 הפעלה (גרסה %s) | interval=%ss | DB=%s", VERSION, INTERVAL, DB_PATH)

if not BOT_TOKEN or BOT_TOKEN.strip().startswith("PUT-YOUR-TELEGRAM-BOT-TOKEN-HERE"):
    raise RuntimeError("BOT_TOKEN חסר או לא הוגדר בקובץ config.py")

# --- DB
conn = dbmod.connect(DB_PATH)
dbmod.ensure_schema(conn)
logging.info("📁 DB path: %s", pathlib.Path(DB_PATH).resolve())
logging.info("🔎 DB attached: %s", {"name":"main","file":str(pathlib.Path(DB_PATH).resolve())})

# --- Telegram
from handlers import handle_start, handle_callback

app = Application.builder().token(BOT_TOKEN).build()
app.bot_data["conn"] = conn

app.add_handler(CommandHandler("start", handle_start))
app.add_handler(CallbackQueryHandler(handle_callback))

# JobQueue: מריץ תמיד את run_monitor(conn, app)
async def _tick(_ctx):
    await lg.run_monitor(conn, app)

app.job_queue.run_repeating(lambda ctx: asyncio.create_task(_tick(ctx)), interval=INTERVAL, first=5)
logging.info("🗓️  JobQueue repeating task scheduled (interval=%ss)", INTERVAL)

async def main():
    await app.initialize()
    await app.start()
    logging.info("Application started")
    await app.updater.start_polling(allowed_updates=app.bot.allowed_updates)
    await app.updater.wait()

if __name__ == "__main__":
    asyncio.run(main())
