# logic.py
from __future__ import annotations
import logging, sqlite3, time, re, datetime as dt
from typing import List, Dict, Tuple, Optional
import requests
from bs4 import BeautifulSoup

import config

log = logging.getLogger(__name__)

HEADERS = {"User-Agent": config.USER_AGENT}

def db_init(conn: sqlite3.Connection) -> None:
    """Ensure schema exists from schema.sql"""
    with open("schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()

def _parse_price(text: str) -> Tuple[Optional[float], Optional[str]]:
    """Extract numeric price and currency symbol from text."""
    t = text.replace("\xa0"," ").strip()
    # currencies: ₪, ש"ח/ש״ח/שח -> treat as ILS; $/USD -> USD
    cur = None
    if "₪" in t or "ש\"ח" in t or "ש״ח" in t or "שח" in t:
        cur = "₪"
    elif "$" in t or "USD" in t:
        cur = "$"
    # number like 555 or 1,234 or 1 234
    m = re.search(r"([0-9][0-9\.,\s]*)", t)
    value = None
    if m:
        nums = m.group(1).replace(",", "").replace(" ", "").replace("\u202f","")
        try:
            value = float(nums)
        except ValueError:
            value = None
    return value, cur

def fetch_html(url: str, timeout: int = config.REQUEST_TIMEOUT) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.text

def parse_items(html: str) -> List[Dict]:
    """Very tolerant parser. Looks for blocks that resemble cards with destination+price."""
    soup = BeautifulSoup(html, "lxml")
    items: List[Dict] = []
    # Heuristics: any element having a price-like number and a destination-like label
    candidates = soup.find_all(text=re.compile(r"\d"))
    seen = set()
    for node in candidates:
        text = " ".join(node.get_text(strip=True).split()) if hasattr(node, "get_text") else str(node).strip()
        price_val, currency = _parse_price(text)
        if price_val is None and currency is None:
            continue
        # destination nearby: look at parent/previous siblings
        dest = None
        url = None
        el = node.parent if hasattr(node, "parent") else None
        if el:
            # find nearest text node that looks like destination (non-numeric words, possibly with dash)
            context = " ".join(el.get_text(" ", strip=True).split())
            # crude split around price to get candidate destination part
            parts = re.split(r"\d[\d\.,\s]*", context, maxsplit=1)
            if parts:
                # keep non-empty words that contain letters
                for p in parts:
                    if re.search(r"[A-Za-zא-ת]", p):
                        dest = " ".join(p.split())[:64]
                        break
            # link
            a = el.find("a", href=True)
            if a:
                url = a["href"]
        if not dest:
            continue
        key = (dest, price_val, currency, url or "")
        if key in seen:
            continue
        seen.add(key)
        items.append({"destination": dest, "price": price_val, "currency": currency, "url": url})
    return items

def _db_upsert(conn: sqlite3.Connection, items: List[Dict]) -> Tuple[int,int]:
    """Insert new rows or update last_seen for existing (destination,url,price,currency)."""
    ins = upd = 0
    cur = conn.cursor()
    for it in items:
        dest = it.get("destination") or ""
        price = it.get("price")
        curr = it.get("currency")
        url  = it.get("url")
        cur.execute(
            "SELECT id FROM show_item WHERE destination=? AND IFNULL(url,'')=IFNULL(?, '') "
            "AND IFNULL(price,-1)=IFNULL(?, -1) AND IFNULL(currency,'')=IFNULL(?, '')",
            (dest, url, price, curr),
        )
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE show_item SET last_seen=CURRENT_TIMESTAMP WHERE id=?", (row[0],))
            upd += 1
        else:
            cur.execute(
                "INSERT INTO show_item(destination,price,currency,url) VALUES (?,?,?,?)",
                (dest, price, curr, url),
            )
            ins += 1
    conn.commit()
    return ins, upd

def monitor_job(conn: sqlite3.Connection, app=None) -> Tuple[int,int,int]:
    """Fetch -> parse -> upsert. Returns (found, inserted, updated)."""
    db_init(conn)
    html = fetch_html(config.URL)
    items = parse_items(html)
    ins, upd = _db_upsert(conn, items)
    log.info("monitor_job: parsed=%s, inserted=%s, updated=%s", len(items), ins, upd)
    return len(items), ins, upd

async def run_monitor(conn: sqlite3.Connection, app=None):
    """Awaitable wrapper used by the job scheduler. Runs synchronously to avoid threading issues."""
    return monitor_job(conn, app)
