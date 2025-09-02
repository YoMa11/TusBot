# -*- coding: utf-8 -*-
from __future__ import annotations
import logging, sqlite3, asyncio
from typing import Dict, Tuple, List
from telegram.ext import Application

CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "ILS": "₪",
    "NIS": "₪",
    "CAD": "C$",
    "AUD": "A$",
}

def _conn_from_app(app: Application) -> sqlite3.Connection:
    conn = app.bot_data.get("conn")
    if not isinstance(conn, sqlite3.Connection):
        raise RuntimeError("DB connection is missing in Application.bot_data['conn']")
    return conn

def _fmt_price(amount: float, currency: str) -> str:
    cur = (currency or "").upper().strip() or "USD"
    sym = CURRENCY_SYMBOLS.get(cur, cur + " ")
    # ללא המרות! תצוגה בלבד
    # התאמה לרמות מחיר של האתר (100/150/200₪/300) תוצג כפי שב־DB
    if sym in {"USD","EUR","GBP","ILS","NIS","CAD","AUD"}:
        # If symbol wasn't found, it would be code; this branch not taken normally
        pass
    if sym and sym[-1].isdigit():
        # unlikely, but protect concat
        return f"{amount:.0f} {sym}"
    if sym in {"₪"}:
        return f"{sym}{int(amount) if amount.is_integer() else amount:.0f}"
    return f"{sym}{amount:.0f}"

async def ui_all_flights(app: Application) -> str:
    conn = _conn_from_app(app)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, origin, dest, depart_ts, arrive_ts, price_amount, price_currency, seats, status
        FROM flights
        ORDER BY depart_ts ASC
        LIMIT 20
    """)
    rows = cur.fetchall()
    if not rows:
        return "אין טיסות להצגה כרגע."
    lines = ["✈️ *כל הטיסות (עד 20 הקרובות)*", ""]
    for (fid, origin, dest, dep, arr, amt, curc, seats, status) in rows:
        price_txt = _fmt_price(float(amt or 0), curc or "USD") if amt is not None else "—"
        seat_txt = "❓" if seats is None else (f"{seats} מושבים" if seats >= 0 else "❓")
        if status and str(status).lower() in {"removed","cancelled","deleted"}:
            status_txt = "— הוסרה 🚫"
        else:
            status_txt = ""
        lines.append(f"• {origin or '??'} → {dest or '??'} | 🕒 יציאה {dep} → נחיתה {arr} | 💵 {price_txt} | 💺 {seat_txt} {status_txt}")
    return "\n".join(lines)

async def ui_prices(app: Application) -> str:
    conn = _conn_from_app(app)
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT price_currency, price_amount
        FROM flights
        WHERE price_amount IS NOT NULL
    """)
    items = cur.fetchall()
    if not items:
        return "אין מחירים להצגה כרגע."
    # מיון לפי מטבע ואז סכום
    items.sort(key=lambda x: ((x[0] or "").upper(), float(x[1])))
    lines = ["💵 *טאב מחירים* — מוצג בדיוק כפי שב־DB (ללא המרה):", ""]
    for curc, amt in items:
        lines.append(f"• {_fmt_price(float(amt), curc or 'USD')}")
    return "\n".join(lines)

async def ui_dests(app: Application) -> str:
    conn = _conn_from_app(app)
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT dest
        FROM flights
        WHERE dest IS NOT NULL AND TRIM(dest) <> ''
        ORDER BY dest COLLATE NOCASE
    """)
    dests = [r[0] for r in cur.fetchall()]
    if not dests:
        return "אין יעדים ב־DB כרגע."
    lines = ["🗺️ *יעדים* — כל יעדי ה־DB מוצגים (גם אם אין כרגע טיסה פעילה).", "", "בחר 'בחר הכל' כדי לסמן את כל היעדים בבת אחת."]
    for d in dests:
        lines.append(f"• {d}")
    return "\n".join(lines)

async def ui_dests_select_all(app: Application) -> str:
    # כרגע פעולה לוגית בלבד (ללא שמירה למשתמש); ניתן להרחיב לסטטוס פר־משתמש
    conn = _conn_from_app(app)
    cur = conn.cursor()
    cur.execute("""SELECT COUNT(DISTINCT dest) FROM flights WHERE dest IS NOT NULL AND TRIM(dest) <> ''""")
    n = cur.fetchone()[0] or 0
    return f"נבחרו כל ה{n} היעדים ✔️\n(בעתיד: נשמור בחירת משתמש/פילטרים אישיים)."

async def ui_alerts(app: Application) -> str:
    return "התראות — ניהול סבסקריפשנים והתראות אוטומטיות. (לביצוע בהמשך)"

async def ui_settings(app: Application) -> str:
    return "הגדרות — פרופיל/מטבע/שפה. (לביצוע בהמשך)"

async def ui_more(app: Application) -> str:
    return "עוד… — עזרה/אודות/פידבק. (לביצוע בהמשך)"

async def monitor_job(conn: sqlite3.Connection, app: Application) -> None:
    logging.info("💓 monitor_job heartbeat")
    await asyncio.sleep(0.01)

async def run_monitor(conn: sqlite3.Connection, app: Application) -> None:
    try:
        await monitor_job(conn, app)
    except Exception:
        logging.exception("run_monitor: monitor_job raised")
        raise
