from __future__ import annotations
from typing import List, Dict, Iterable, Tuple, Optional
import re
import requests
from bs4 import BeautifulSoup, ResultSet
import config
import db

# ---------- Public API used by handlers ----------

def get_version() -> str:
    # נשען על config.SCRIPT_VERSION שקיים אצלך, לא משנה אותו
    return getattr(config, "SCRIPT_VERSION", "V2.x")

def list_all_destinations_with_country(conn) -> Iterable[Tuple[str, str, object]]:
    """
    מחזיר רשימת (city, country, None) לכל היעדים. בלי מחירים.
    נשען ישירות על ה-DB (שכבר הותאם לחוזה ה-HTML).
    """
    rows = db.list_distinct_city_country(conn)
    for r in rows:
        yield (r["city"], r["country"], None)

# ניקוי בחירה: “*” = כל היעדים
def normalize_selected_cities(raw: List[str]) -> List[Tuple[str,str]]:
    if not raw:
        return []
    if "*" in raw:
        return [("*","*")]
    out: List[Tuple[str,str]] = []
    for token in raw:
        # token בפורמט "עיר|מדינה" או "עיר|"
        parts = token.split("|")
        city = parts[0].strip()
        country = parts[1].strip() if len(parts) > 1 else ""
        if city:
            out.append((city, country))
    return out

# ---------- Scraper & Monitor (contract-aligned) ----------

def _text(n) -> str:
    return re.sub(r"\s+", " ", (n.get_text(strip=True) if n else "")).strip()

def _parse_item(div) -> Dict[str, Optional[str]]:
    # על פי חוזה ה-HTML (ראה המסמך המצורף)
    # מזהים ושדות כלליים
    item_id = div.get("data_ga_item_id") or div.get("ite_item") or ""
    selapp_item = div.get("ite_selappitem") or ""
    category = div.get("category") or ""
    provider = div.get("data_ga_item_category4") or ""
    affiliation = div.get("data_ga_affiliation") or ""
    promo_category = div.get("data_ga_item_category") or ""
    destination = div.get("data_ga_item_name") or div.get("con_desc") or ""
    dest_city, dest_country = "", ""
    if destination and "-" in destination:
        parts = [p.strip() for p in destination.split("-", 1)]
        if len(parts) == 2:
            dest_city, dest_country = parts[0], parts[1]

    trip_title = _text(div.select_one(".show_item_name"))
    price_text = _text(div.select_one(".show_item_total_price"))
    # מחיר ומטבע
    price_attr = div.get("data_number_ga_price")
    price_val = None
    if price_attr and re.match(r"^\d+(\.\d+)?$", price_attr):
        price_val = float(price_attr)
    else:
        m = re.search(r"(\d+(?:\.\d+)?)", price_text.replace(",", ""))
        price_val = float(m.group(1)) if m else None
    currency = div.get("data_ga_currency") or ( "$" if "$" in price_text else "₪" if "₪" in price_text or "שח" in price_text or "ש\"ח" in price_text else "" )

    img = div.select_one(".show_item_img img")
    img_url = img.get("src") if img else None

    badge_text = _text(div.select_one(".spcial_message_bottom"))

    # פרטי הלוך
    go = div.select_one(".flight_go")
    out_from_city  = _text(go.select_one(".from .text-gray")) if go else None
    out_from_time  = _text(go.select_one(".from .flight_hourTime")) if go else None
    out_from_date  = _text(go.select_one(".from .text-gray"))[1:] if go else None  # אם יש פעמיים text-gray
    out_to_city    = _text(go.select_one(".to .text-gray")) if go else None
    out_to_time    = _text(go.select_one(".to .flight_hourTime")) if go else None
    out_to_date    = _text(go.select_one(".to .text-gray"))[1:] if go else None
    out_duration   = _text(go.select_one(".fligth .text-gray")) if go else None

    # פרטי חזור
    bk = div.select_one(".flight_back")
    back_from_city = _text(bk.select_one(".from .text-gray")) if bk else None
    back_from_time = _text(bk.select_one(".from .flight_hourTime")) if bk else None
    back_from_date = _text(bk.select(".from .text-gray"))[1:] if bk else None
    back_to_city   = _text(bk.select_one(".to .text-gray")) if bk else None
    back_to_time   = _text(bk.select_one(".to .flight_hourTime")) if bk else None
    back_to_date   = _text(bk.select(".to .text-gray"))[1:] if bk else None
    back_duration  = _text(bk.select_one(".fligth .text-gray")) if bk else None

    note = _text(div.select_one(".flight_note"))
    more_like = _text(div.select_one(".more_like_this"))

    return {
        "item_id": item_id,
        "selapp_item": selapp_item,
        "category": category,
        "provider": provider,
        "affiliation": affiliation,
        "promo_category": promo_category,
        "destination": destination,
        "dest_city": dest_city,
        "dest_country": dest_country,
        "trip_title": trip_title,
        "price": price_val,
        "currency": currency,
        "price_text": price_text,
        "img_url": img_url,
        "badge_text": badge_text,
        "out_from_city": out_from_city,
        "out_from_date": out_from_date if isinstance(out_from_date, str) else None,
        "out_from_time": out_from_time,
        "out_to_city": out_to_city,
        "out_to_date": out_to_date if isinstance(out_to_date, str) else None,
        "out_to_time": out_to_time,
        "out_duration": out_duration,
        "back_from_city": back_from_city,
        "back_from_date": back_from_date if isinstance(back_from_date, str) else None,
        "back_from_time": back_from_time,
        "back_to_city": back_to_city,
        "back_to_date": back_to_date if isinstance(back_to_date, str) else None,
        "back_to_time": back_to_time,
        "back_duration": back_duration,
        "note": note,
        "more_like": more_like,
        "url": config.URL,
    }

def scrape_items(html: str) -> List[dict]:
    soup = BeautifulSoup(html, "lxml")
    items = []
    for div in soup.select(".show_item"):
        items.append(_parse_item(div))
    return items

def monitor_job(conn, app=None) -> Tuple[int, int]:
    """
    מושך את הדף, מפרש לפי חוזה ה-HTML, ומעדכן/מכניס שורות.
    מחזיר (inserted, updated).
    """
    resp = requests.get(config.URL, timeout=getattr(config, "REQUEST_TIMEOUT", 15), headers={"User-Agent": getattr(config, "USER_AGENT", "Mozilla/5.0")})
    resp.raise_for_status()
    items = scrape_items(resp.text)

    ins = upd = 0
    with conn:
        for row in items:
            # נסיון ראשוני לבדוק אם קיים
            exists = conn.execute(
                "SELECT 1 FROM flights WHERE item_id=? AND selapp_item=?",
                (row["item_id"], row["selapp_item"])
            ).fetchone()
            db.upsert_flight(conn, row)
            if exists:
                upd += 1
            else:
                ins += 1
    return ins, upd

# נוח לאפליקציה שקוראת Async
async def run_monitor(conn, app=None):
    # כדי להימנע מבעיות thread, כאן מריצים סינכרוני; הקריאה מה־app צריכה להזרים conn מאותו thread.
    return monitor_job(conn, app)


def _text(n):
    """Accept element OR list/ResultSet; return normalized text."""
    import re
    try:
        from bs4.element import ResultSet as _RS
    except Exception:
        _RS = tuple()
    if not n:
        return ""
    if isinstance(n, (list, _RS)):
        parts = [el.get_text(strip=True) for el in n if getattr(el, 'get_text', None)]
        return re.sub(r"\s+", " ", " ".join(parts)).strip()
    return re.sub(r"\s+", " ", n.get_text(strip=True)).strip()


def get_dest_summary(conn, limit=50):
    """Return [(destination, count)], total_count for current flights."""
    cur = conn.cursor()
    cur.execute("""        SELECT destination, COUNT(*) AS cnt
        FROM flights
        GROUP BY destination
        ORDER BY cnt DESC, destination ASC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM flights")
    total = cur.fetchone()[0]
    return rows, total


def get_dest_rows_for_keyboard(conn):
    """
    החזרת נתונים למקלדת היעדים בפורמט:
        [(city:str, country:str, count:int), ...]
    משתמש בעמודות flights.dest_city ו-flights.dest_country אם קיימות; אחרת נופל ל-destination.
    """
    cur = conn.cursor()
    # נעדיף עיר/מדינה אם יש, אחרת נתרגם מ-destination לשדה city (ונשאיר country ריק)
    try:
        cur.execute("""
            SELECT
                COALESCE(NULLIF(TRIM(dest_city), ''), COALESCE(NULLIF(TRIM(destination), ''), 'יעד לא ידוע')) AS city,
                COALESCE(NULLIF(TRIM(dest_country), ''), '') AS country,
                COUNT(*) AS cnt
            FROM flights
            GROUP BY city, country
            ORDER BY country ASC, city ASC
        """)
    except Exception:
        # Fallback לגירסאות ישנות
        cur.execute("""
            SELECT
                COALESCE(NULLIF(TRIM(destination), ''), 'יעד לא ידוע') AS city,
                '' AS country,
                COUNT(*) AS cnt
            FROM flights
            GROUP BY city
            ORDER BY city ASC
        """)
    return cur.fetchall()

