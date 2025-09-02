from __future__ import annotations
import logging, sqlite3
from typing import Any

async def monitor_job(conn: sqlite3.Connection, app) -> None:
    # ניטור פשוט: סופר רשומות ומדפיס סטטוס
    cur = conn.execute("SELECT COUNT(*) AS n FROM flights")
    n = cur.fetchone()["n"]
    logging.info("🔍 monitor_job: flights in DB = %s", n)

async def run_monitor(conn: sqlite3.Connection, app) -> None:
    try:
        await monitor_job(conn, app)
    except Exception as e:
        import utils
        logging.error("run_monitor: exception: %s", utils.exc_str(e))
