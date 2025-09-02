# -*- coding: utf-8 -*-
from __future__ import annotations
import logging, sqlite3, datetime as dt, asyncio
from typing import Optional, Any

log = logging.getLogger("tustus.logic")

async def monitor_job(conn: sqlite3.Connection, app: Any) -> None:
    """משימת הניטור המרכזית – ניתנת להרחבה.
    כאן אמורים לקרוא נתונים מהאתר/מקור ולסנכרן ל-DB.
    כרגע: מדמה פעולה קצרה ולוג.
    """
    log.info("monitor_job: tick start")
    await asyncio.sleep(0.01)
    # TODO: integrate scraper/upsert
    log.info("monitor_job: tick end")

async def run_monitor(conn: sqlite3.Connection, app: Any) -> None:
    """עטיפה יציבה ל-monitor_job עם תאימות לאחור."""
    try:
        return await monitor_job(conn, app)
    except TypeError:
        # תאימות לפונקציה ישנה שאולי מקבלת פרמטר יחיד
        try:
            res = monitor_job(conn)  # ייתכן סינכרוני ישן
            if asyncio.iscoroutine(res):
                await res
            return None
        except Exception as e:
            log.error("legacy monitor_job failed: %r", e)
            raise
