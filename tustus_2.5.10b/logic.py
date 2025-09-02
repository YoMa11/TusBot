# -*- coding: utf-8 -*-
from __future__ import annotations
import logging, sqlite3, asyncio
from telegram.ext import Application

async def ui_all_flights(app: Application) -> str:
    return "כל הטיסות — תצוגה מרוכזת (WIP)."

async def ui_prices(app: Application) -> str:
    return "טאב מחירים — מוצגים בדיוק כפי שב־DB (ללא המרה)."

async def ui_dests(app: Application) -> str:
    return "טאב יעדים — כולל חיפוש, 'בחר הכל', ותצוגת דסקטופ משופרת."

async def ui_alerts(app: Application) -> str:
    return "התראות — ניהול סבסקריפשנים והתראות אוטומטיות."

async def ui_settings(app: Application) -> str:
    return "הגדרות — פרופיל/מטבע/שפה."

async def ui_more(app: Application) -> str:
    return "עוד… — עזרה/אודות/פידבק."

async def monitor_job(conn: sqlite3.Connection, app: Application) -> None:
    logging.info("💓 monitor_job heartbeat")
    await asyncio.sleep(0.01)

async def run_monitor(conn: sqlite3.Connection, app: Application) -> None:
    try:
        await monitor_job(conn, app)
    except Exception:
        logging.exception("run_monitor: monitor_job raised")
        raise
