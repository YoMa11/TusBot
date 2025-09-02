from __future__ import annotations

import os
import sys
import asyncio
import logging
import sqlite3
import inspect
from types import SimpleNamespace

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# ---- Project config (REQUIRED) ----
try:
    import config as cfg  # must provide: BOT_TOKEN, optionally DB_PATH, INTERVAL
except Exception as e:
    raise RuntimeError("config.py is required and must define BOT_TOKEN") from e

# Optional DB bootstrap
try:
    from db import ensure_schema  # type: ignore
except Exception:
    ensure_schema = None  # fallback later

# Handlers (we inject conn/cfg at runtime)
from handlers import handle_start, handle_callback  # type: ignore

# ---- Logging ----
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("tustus")
fh = logging.FileHandler("./bot.log")
fh.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(fh)
logger.info("📝 logging to ./bot.log")

# ---- Config (from config.py only) ----
BOT_TOKEN = getattr(cfg, "BOT_TOKEN")  # required
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing in config.py")

DB_PATH = getattr(cfg, "DB_PATH", "./flights.db")
INTERVAL = int(getattr(cfg, "INTERVAL", 180))

logger.info(f"🚀 הפעלה (גרסה V5.1.0 / v1.0.32) | interval={INTERVAL}s | DB={DB_PATH}")

# ---- DB setup ----
os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
logger.info("✅ DB schema ensured")
logger.info("✅ DB schema ensured")
logger.info(f"📁 DB path: {os.path.abspath(DB_PATH)}")
logger.info(f"🔎 DB attached: {{'seq': 0, 'name': 'main', 'file': '{os.path.abspath(DB_PATH)}'}}")

# Ensure schema
if ensure_schema:
    try:
        ensure_schema(conn)  # type: ignore
    except Exception as e:
        logger.warning(f"ensure_schema failed: {e}")
else:
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    if os.path.exists(schema_path):
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
            conn.commit()
        except Exception as e:
            logger.warning(f"schema.sql apply failed: {e}")

# ---- Monitor wrapper ----
async def monitor_job_async(context):
    """
    Calls logic.monitor_job(context) if present; supports legacy (conn, bot) signature too.
    """
    try:
        from logic import monitor_job as _mon  # type: ignore
    except Exception as e:
        logger.warning(f"monitor_job import failed: {e}")
        return
    try:
        res = _mon(context)  # preferred: (context)
        if inspect.isawaitable(res):
            await res
    except TypeError:
        # legacy signature: (conn, bot)
        app = context.application
        res2 = _mon(app.bot_data.get('conn'), app.bot)
        if inspect.isawaitable(res2):
            await res2

async def _monitor_fallback_loop(application, interval: int):
    while True:
        try:
            ctx = SimpleNamespace(application=application)
            await monitor_job_async(ctx)
        except Exception as e:
            logger.warning(f"monitor fallback loop error: {e}")
        await asyncio.sleep(max(30, int(interval or 180)))

async def _startup(app):
    logger.info("Scheduler started")
    if app.job_queue is None:
        logger.warning("⚠️ JobQueue לא זמין — ניטור ירוץ בלולאת fallback")
        app.create_task(_monitor_fallback_loop(app, INTERVAL))
    else:
        app.job_queue.run_repeating(monitor_job_async, interval=INTERVAL, first=5)

# ---- Telegram app ----
application = (
    ApplicationBuilder()
    .token(BOT_TOKEN)
    .post_init(_startup)
    .build()
)
application.bot_data["conn"] = conn  # make DB available to jobs/handlers

# --- wrappers to inject conn/cfg ---
import inspect as _insp
async def _call_maybe_async(fn, *args, **kwargs):
    res = fn(*args, **kwargs)
    if _insp.isawaitable(res):
        return await res

def _bind_injected(fn, update, context):
    sig = _insp.signature(fn)
    params = list(sig.parameters.keys())
    args = [update, context]
    kwargs = {}
    if "conn" in params: kwargs["conn"] = conn
    if "cfg" in params: kwargs["cfg"] = cfg
    return args, kwargs

async def _start_wrapper(update, context):
    args, kwargs = _bind_injected(handle_start, update, context)
    return await _call_maybe_async(handle_start, *args, **kwargs)

async def _callback_wrapper(update, context):
    args, kwargs = _bind_injected(handle_callback, update, context)
    return await _call_maybe_async(handle_callback, *args, **kwargs)

application.add_handler(CommandHandler("start", _start_wrapper))
application.add_handler(CallbackQueryHandler(_callback_wrapper))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _callback_wrapper))

def main():
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
