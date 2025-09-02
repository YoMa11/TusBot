from __future__ import annotations
import re, json, time, hashlib, sqlite3, typing as t
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict

import config  # do not touch user's config
import db

UA = getattr(config, "USER_AGENT", None) or (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

currency_map = {"USD":"$", "ILS":"₪", "NIS":"₪"}

def _clean_text(s: str | None) -> str:
    if not s: return ""
    return re.sub(r"\s+", " ", s).strip()

def _num(s: str) -> float | None:
    if not s: return None
    m = re.search(r"(\d+(?:[.,]\d+)?)", s.replace(",", ""))
    return float(m.group(1)) if m else None

def _hash(d: dict) -> str:
    data = json.dumps(d, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.md5(data).hexdigest()

def _split_dest(s: str) -> tuple[str,str]:
    # "אתונה - יוון" -> ("אתונה","יוון")
    if not s: return "", ""
    parts = [p.strip() for p in s.split("-")]
    if len(parts) >= 2:
        return parts[0], parts[-1]
    return s, ""

def parse_cards(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    out: list[dict] = []
    for card in soup.select("div.show_item"):
        a = card.attrs
        item_id = a.get("data_ga_item_id") or a.get("ite_item") or ""
        selapp_item = a.get("ite_selappitem") or ""
        category = a.get("category") or ""
        provider = a.get("data_ga_item_category4") or ""
        affiliation = a.get("data_ga_affiliation") or ""
        promo_category = a.get("data_ga_item_category") or ""
        destination = a.get("data_ga_item_name") or a.get("con_desc") or ""

        dest_city, dest_country = _split_dest(destination)

        trip_title = _clean_text((card.select_one(".show_item_name") or {}).get_text() if card.select_one(".show_item_name") else "")
        price_text = _clean_text((card.select_one(".show_item_total_price") or {}).get_text() if card.select_one(".show_item_total_price") else "")
        currency = a.get("data_ga_currency") or ("USD" if "$" in price_text else "ILS" if "₪" in price_text else "")
        price = a.get("data_number_ga_price")
        price = float(price) if price else _num(price_text)
        img_url = (card.select_one(".show_item_img img") or {}).get("src", "") if card.select_one(".show_item_img img") else ""
        badge_el = card.select_one(".spcial_message_bottom")
        badge_text = _clean_text(badge_el.get_text()) if badge_el else ""

        # outbound
        go = card.select_one(".flight_go")
        def parse_leg(leg):
            if not leg: return ("","","")
            grays = leg.select(".from .text-gray")
            from_city = _clean_text(grays[0].get_text()) if grays else ""
            from_date = _clean_text(grays[-1].get_text()) if len(grays)>1 else ""
            from_time = _clean_text((leg.select_one(".from .flight_hourTime") or {}).get_text() if leg.select_one(".from .flight_hourTime") else "")
            tg = leg.select(".to .text-gray")
            to_city = _clean_text(tg[0].get_text()) if tg else ""
            to_date = _clean_text(tg[-1].get_text()) if len(tg)>1 else ""
            to_time = _clean_text((leg.select_one(".to .flight_hourTime") or {}).get_text() if leg.select_one(".to .flight_hourTime") else "")
            dur   = _clean_text((leg.select_one(".fligth .text-gray") or {}).get_text() if leg.select_one(".fligth .text-gray") else "")
            return (from_city, from_time, from_date, to_city, to_time, to_date, dur)

        g = parse_leg(go)
        out_from_city, out_from_time, out_from_date, out_to_city, out_to_time, out_to_date, out_duration = g if g else ("","","","","","","")

        back = card.select_one(".flight_back")
        b = parse_leg(back)
        back_from_city, back_from_time, back_from_date, back_to_city, back_to_time, back_to_date, back_duration = b if b else ("","","","","","","")

        note = _clean_text((card.select_one(".flight_note") or {}).get_text() if card.select_one(".flight_note") else "")
        more_like = _clean_text((card.select_one(".more_like_this") or {}).get_text() if card.select_one(".more_like_this") else "")

        row = dict(
            item_id=str(item_id),
            selapp_item=str(selapp_item),
            category=str(category),
            provider=provider, affiliation=affiliation, promo_category=promo_category,
            destination=destination, dest_city=dest_city, dest_country=dest_country,
            trip_title=trip_title,
            price=price, currency=currency, price_text=price_text,
            img_url=img_url, badge_text=badge_text,
            out_from_city=out_from_city, out_from_time=out_from_time, out_from_date=out_from_date,
            out_to_city=out_to_city,   out_to_time=out_to_time,   out_to_date=out_to_date,
            out_duration=out_duration,
            back_from_city=back_from_city, back_from_time=back_from_time, back_from_date=back_from_date,
            back_to_city=back_to_city,   back_to_time=back_to_time,   back_to_date=back_to_date,
            back_duration=back_duration,
            note=note, more_like=more_like
        )
        row["uniq_hash"] = _hash({k:row[k] for k in ["item_id","price","currency","out_from_date","back_from_date"]})
        out.append(row)
    return out

def monitor_job(conn: sqlite3.Connection, app=None) -> tuple[int,int,int]:
    """
    Scrape config.URL and upsert into DB. Returns (found, inserted, updated)
    """
    headers = {"User-Agent": UA}
    r = requests.get(config.URL, headers=headers, timeout=getattr(config,"REQUEST_TIMEOUT", 15))
    r.raise_for_status()
    items = parse_cards(r.text)
    # write a raw snapshot for debug if needed
    snap = f"snapshot_{int(time.time())}.html"
    try:
        open("last_snapshot.html","w",encoding="utf-8").write(r.text)
    except Exception:
        pass
    ins, upd = db.upsert_items(conn, items)
    return (len(items), ins, upd)

async def run_monitor(parent_conn: sqlite3.Connection, app=None):
    """
    Async wrapper that creates a NEW connection in this thread to avoid cross-thread SQLite errors.
    """
    path = parent_conn.execute("PRAGMA database_list").fetchone()["file"] if parent_conn else "./flights.db"
    with db.get_conn(path) as conn:
        return monitor_job(conn, app)
