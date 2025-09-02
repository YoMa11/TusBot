from __future__ import annotations
import logging, httpx, sqlite3, datetime as dt
from bs4 import BeautifulSoup  # type: ignore
import config

log = logging.getLogger("tustus.logic")

def _get_source_url() -> str:
    return config.URL

def _http_get(url: str) -> str:
    r = httpx.get(
        url,
        timeout=getattr(config, "REQUEST_TIMEOUT", 15),
        headers={"User-Agent": getattr(config, "USER_AGENT", "Mozilla/5.0")},
    )
    r.raise_for_status()
    return r.text

def fetch_flights_html() -> str:
    url = _get_source_url()
    log.info("📡 Fetching from URL=%s", url)
    return _http_get(url)

def parse_show_items(html: str) -> list[dict]:
    # dummy parser placeholder to keep interface; real project overrides this
    return []

async def run_monitor(conn: sqlite3.Connection, app) -> None:
    """Called every INTERVAL by app.py; fetches & updates DB; notifies via app as needed."""
    html = fetch_flights_html()
    items = parse_show_items(html)
    log.info("show_item cards parsed: %d", len(items))
    # upsert stub
    conn.execute("CREATE TABLE IF NOT EXISTS show_item(id INTEGER PRIMARY KEY, title TEXT)")
    conn.commit()
