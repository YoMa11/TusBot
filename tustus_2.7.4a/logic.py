# logic.py — tustus_2.7.4a-compatible (no schema changes)
from __future__ import annotations

import logging
import re
import sqlite3
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

import config

log = logging.getLogger("tustus.logic")

# ---------- Public API (app.py calls this) ----------

def monitor_job(conn: sqlite3.Connection, app=None) -> tuple[int, int]:
    """
    Pull site -> parse -> upsert into show_item.
    Returns: (inserted_count, updated_count)
    Notes:
      * Uses ONLY existing columns: destination, price, currency, url, last_seen
      * No schema changes. No to_thread (runs on caller thread).
    """
    html = _fetch_html(config.URL, timeout=getattr(config, "REQUEST_TIMEOUT", 15))
    items = _parse_cards(html)
    ins, upd = _db_upsert(conn, items)
    log.info("monitor_job: parsed=%d inserted=%d updated=%d", len(items), ins, upd)
    return ins, upd


async def run_monitor(conn: sqlite3.Connection, app=None) -> None:
    """
    Async wrapper that runs monitor_job on the SAME thread/loop (no to_thread),
    so the sqlite3 connection remains valid.
    """
    try:
        monitor_job(conn, app)
    except Exception:
        log.exception("run_monitor: monitor_job raised")


# ---------- Internal helpers ----------

def _fetch_html(url: str, timeout: int = 15) -> str:
    headers = {
        "User-Agent": getattr(
            config,
            "USER_AGENT",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        )
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.text


def _parse_cards(html: str) -> list[dict]:
    """
    Parse flights list from the homepage HTML.
    We keep it tolerant: look for elements that contain a destination and a price.
    Result item keys match the DB schema: destination, price (float), currency, url, last_seen
    """
    soup = BeautifulSoup(html, "lxml")

    # נסיון ראשון: כרטיסים/לינקים עם יעד ומחיר
    cards = []

    # חיפוש כל הלינקים/כרטיסים האפשריים
    candidates = soup.select("a, div, li, article, section")

    for el in candidates:
        text = _s(el)
        if not text:
            continue

        # יעד (he/en) – די סלחני: מילה/שתיים/שלוש עם אותיות, לעיתים כוללת מקף/רווח
        dest = _extract_destination(text)
        if not dest:
            continue

        # מחיר
        price_val, currency = _extract_price(text)
        if price_val is None or not currency:
            # לפעמים המחיר נמצא בצאצא, ננסה לאתר ספאן/דיב עם מחיר
            sub = el.find(string=_price_regex_search)
            if sub:
                price_val, currency = _extract_price(str(sub))

        if price_val is None or not currency:
            continue

        # URL אם קיים
        href = el.get("href") or el.get("data-href")
        url = href if (href and href.startswith("http")) else config.URL

        cards.append(
            {
                "destination": dest.strip(),
                "price": float(price_val),
                "currency": currency,
                "url": url,
                "last_seen": _now_utc_iso(),
            }
        )

    return _dedupe(cards)


def _db_upsert(conn: sqlite3.Connection, items: list[dict]) -> tuple[int, int]:
    """
    Upsert to table show_item using existing columns ONLY.
    Key = (destination, url). If exists -> UPDATE price,currency,last_seen. Else -> INSERT.
    """
    ins = upd = 0
    cur = conn.cursor()

    for it in items:
        dest = it["destination"]
        url = it["url"]
        price = it["price"]
        currency = it["currency"]
        last_seen = it["last_seen"]

        cur.execute(
            "SELECT id, price, currency FROM show_item WHERE destination=? AND url=? LIMIT 1",
            (dest, url),
        )
        row = cur.fetchone()
        if row:
            # עדכון רק אם יש שינוי במחיר/מטבע או תמיד לעדכן last_seen
            cur.execute(
                "UPDATE show_item SET price=?, currency=?, last_seen=? WHERE id=?",
                (price, currency, last_seen, row[0]),
            )
            upd += 1
        else:
            cur.execute(
                "INSERT INTO show_item (destination, price, currency, url, last_seen) "
                "VALUES (?, ?, ?, ?, ?)",
                (dest, price, currency, url, last_seen),
            )
            ins += 1

    conn.commit()
    return ins, upd


# ---------- Parsing utilities ----------

_price_pat = re.compile(
    r"(₪|ש\"ח|ש׳ח|ש״ח|\$|USD)\s*([0-9]+(?:[.,][0-9]{1,2})?)", re.UNICODE
)
_alt_price_pat = re.compile(
    r"([0-9]+(?:[.,][0-9]{1,2})?)\s*(₪|ש\"ח|ש׳ח|ש״ח|\$|USD)", re.UNICODE
)

def _price_regex_search(s: str):
    return _price_pat.search(s) or _alt_price_pat.search(s)

def _extract_price(text: str) -> tuple[float | None, str]:
    """
    Return (price_float, currency_symbol) with currency in {'₪','$'}.
    Respect source currency (no conversion).
    """
    m = _price_pat.search(text) or _alt_price_pat.search(text)
    if not m:
        return None, ""
    if m.re is _price_pat:
        cur, num = m.group(1), m.group(2)
    else:
        num, cur = m.group(1), m.group(2)

    cur_norm = "$" if cur in ("$", "USD") else "₪"
    try:
        # החלפת פסיק לנקודה אם צריך
        val = float(num.replace(",", "."))
    except Exception:
        return None, ""
    return val, cur_norm


def _extract_destination(text: str) -> str | None:
    """
    ניסיון פשוט להוציא יעד מתוך טקסט הכרטיס. אפשר לחדד בהמשך מול ה-DOM האמיתי.
    """
    # לעיתים היעד נמצא לפני המילה "ל" או כולל אותיות לטיניות (e.g., "Rome", "Paris")
    # ננסה לזהות מחרוזת סבירה באותיות (he/en) באורך 3–25 תווים
    cand = re.findall(r"[A-Za-z\u0590-\u05FF][A-Za-z\u0590-\u05FF\s\-]{2,25}", text)
    if not cand:
        return None
    # בוחרים את המועמד הראשון “הסביר”
    return cand[0].strip()


def _dedupe(items: list[dict]) -> list[dict]:
    """ Deduplicate by (destination,url), keep last occurrence """
    seen = {}
    for it in items:
        seen[(it["destination"], it["url"])] = it
    return list(seen.values())


def _s(el) -> str:
    return " ".join(el.stripped_strings) if el else ""


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
