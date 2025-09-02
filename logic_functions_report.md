### _clean(s)
**Calls:** replace, strip, sub
**Preview:**
```python
def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()

```

### _join_url(base, cand)
**Calls:** match, startswith, strip, urljoin, urlparse
**Preview:**
```python
def _join_url(base: str, cand: str) -> str:
    if not cand: return ""
    cand = cand.strip()
    if cand.startswith("//"):
        return (urllib.parse.urlparse(base).scheme or "https") + ":" + cand
    if re.match(r"^https?://", cand, re.I):
        return cand
    return urllib.parse.urljoin(base, cand)

```

### _int(x)
**Calls:** float, int, replace, str
**Preview:**
```python
def _int(x) -> Optional[int]:
    if x is None: return None
    try: return int(x)
    except Exception:
        try: return int(float(str(x).replace(",", "")))
        except Exception: return None

```

### _price_to_ils(amount, currency)
**Calls:** float, int, round, upper
**Preview:**
```python
def _price_to_ils(amount: Optional[int|float], currency: str) -> Optional[int]:
    if amount is None: return None
    c = (currency or "ILS").upper()
    if c in ("ILS", "₪", "NIS"): return int(round(float(amount)))
    if c in ("USD", "$"):        return int(round(float(amount) * USD_TO_ILS))
    # מטבע אחר? תשאירי כמו שהוא (או הוסיפי מיפוי)
    return int(round(float(amount)))

```

### _parse_brand_datetimes(brand)
**Doc:** data_ga_item_brand נראה כמו:
'9/2/2025 6:00:00 PM-8/29/2025 7:30:00 AM'
נחזיר (min_dt, max_dt) — יציאה/חזרה לפי כרונולוגיה.
**Calls:** append, len, sort, split, str, strip, strptime
**Preview:**
```python
def _parse_brand_datetimes(brand: str) -> tuple[Optional[datetime], Optional[datetime]]:
    """
    data_ga_item_brand נראה כמו:
    '9/2/2025 6:00:00 PM-8/29/2025 7:30:00 AM'
    נחזיר (min_dt, max_dt) — יציאה/חזרה לפי כרונולוגיה.
    """
    if not brand: return (None, None)
    parts = [p.strip() for p in str(brand).split("-") if p.strip()]
    fmt = "%m/%d/%Y %I:%M:%S %p"
    dts: list[datetime] = []
    for p in parts:
        try:
            dts.append(datetime.strptime(p, fmt))
        except Exception:
            pass
    if not dts: return (None, None)
    dts.sort()
    go = dts[0]
    back = dts[1] if len(dts) > 1 else None
    return (go, back)

```

### _norm_ddmm(d, year_hint)
**Calls:** datetime, group, int, match, now, strftime
**Preview:**
```python
def _norm_ddmm(d: str, year_hint: int|None) -> Optional[str]:
    # "29/08" → YYYY-08-29 (עם year_hint אם ניתן, אחרת השנה הנוכחית/הבאה)
    m = re.match(r"^\s*(\d{2})/(\d{2})\s*$", d or "")
    if not m: return None
    day, month = int(m.group(1)), int(m.group(2))
    y = year_hint or datetime.now().year
    try:
        dt = datetime(y, month, day)
        # אם התאריך כבר “עבר” בחודשים אחורה וזה דיל עתידי, קפוץ לשנה הבאה
        if dt < datetime.now():
            dt2 = datetime(y + 1, month, day)
            # נעדיף שנה שבה זה תואם בין brand ל-DD/MM—מכיוון שיש לנו brand נשתמש בו בנפרד.
            return dt.strftime("%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None

```

### _extract_seats(txt)
**Calls:** _int, group, search
**Preview:**
```python
def _extract_seats(txt: str) -> Optional[int]:
    # "2 מקומות אחרונים" → 2
    m = re.search(r"(\d+)\s*(?:מקום|מקומות)", txt or "")
    return _int(m.group(1)) if m else None

```

### _parse_show_item(div, base_url)
**Calls:** _clean, _extract_seats, _int, _join_url, _norm_ddmm, _parse_brand_datetimes, _price_to_ils, findall, get, get_text, len, select_one, strftime, strip, sub
**Preview:**
```python
def _parse_show_item(div, base_url: str) -> Optional[Dict[str, Any]]:
    # --- מזהים וכותרות ---
    item_id   = (div.get("ite_item") or "").strip()
    sel_id    = (div.get("ite_selappitem") or "").strip()
    con_desc  = _clean(div.get("con_desc") or div.get("data_ga_item_name") or "")
    title_el  = div.select_one(".show_item_name")
    title_txt = _clean(title_el.get_text(" ", strip=True)) if title_el else ""
    # יעד: עדיף con_desc. אם ריק, נחלץ מהכותרת "טיסה ל..."
    dest = con_desc or re.sub(r"^טיסה ל", "", title_txt).strip()
    if not dest:
        return None

    # --- מחיר ומטבע ---
    price_num = _int(div.get("data_number_ga_price") or "")
    currency  = (div.get("data_ga_currency") or "ILS").strip()
    price_ils = _price_to_ils(price_num, currency)

    # --- מושבים ---
    seats_block = div.select_one(".spcial_message_bottom")
    seats_txt   = _clean(seats_block.get_text(" ", strip=True)) if seats_block else ""
    seats       = _extract_seats(seats_txt)

    # --- תאריכים (שורת הסיכום + brand עם שנה ושעה) ---
    brand = div.get("data_ga_item_brand") or ""
    go_dt_brand, back_dt_brand = _parse_brand_datetimes(brand)

    # דוגמא: "יום ו' 29/08 -  יום ג' 02/09"
    summary_line = ""
    details = div.select_one(".show_item_details")
    if details:
        # קח את הטקסט הרציף
        summary_line = _clean(details.get_text(" ", strip=True))
    ddmm = re.findall(r"\b(\d{2}/\d{2})\b", summary_line)
    go_date = _norm_ddmm(ddmm[0], go_dt_brand.year if go_dt_brand else None) if ddmm else None
    back_date = _norm_ddmm(ddmm[1], back_dt_brand.year if back_dt_brand else None) if len(ddmm) > 1 else None

    # אם יש brand מלאים — נעדיף אותם לקביעת יום/חודש/שנה, ונשמור גם שעות הדיוק
    go_depart = go_arrive = back_depart = back_arrive = None

    go_from_t  = div.select_one(".flight_go .from .flight_hourTime")
    go_to_t    = div.select_one(".flight_go .to .flight_hourTime")
    back_from_t= div.select_one(".flight_back .from .flight_hourTime")
    back_to_t  = div.select_one(".flight_back .to .flight_hourTime")

    go_depart  = _clean(go_from_t.get_text(strip=True)) if go_from_t else None
    go_arrive  = _clean(go_to_t.get_text(strip=True)) if go_to_t else None
    back_depart= _clean(back_from_t.get_text(strip=True)) if back_from_t else None
    back_arrive= _clean(back_to_t.get_text(strip=True)) if back_to_t else None

    # אם אין go_date/back_date – נשתמש ב-brand בלבד
```

### _parse_show_items_from_html(html, base_url)
**Calls:** BeautifulSoup, _parse_show_item, append, get, info, len, list, select, setdefault, values
**Preview:**
```python
def _parse_show_items_from_html(html: str, base_url: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select("div.show_item")
    items: List[Dict[str, Any]] = []
    for div in cards:
        it = _parse_show_item(div, base_url)
        if it:
            items.append(it)
    # דה-דופ
    uniq = {}
    for it in items:
        k = (it["destination"], it["go_date"], it.get("back_date") or "", it.get("price") or 0)
        uniq.setdefault(k, it)
    out = list(uniq.values())
    logger.info(f"show_item cards parsed: {len(out)}")
    return out

```

### monitor_job(context)
**Calls:** Path, Session, _clean, _parse_show_items_from_html, commit, encode, execute, fetchone, get, getattr, hexdigest, info, raise_for_status, sha1, strip, update, warning, write_text
**Preview:**
```python
def monitor_job(context):
    app = context.application
    conn = app.bot_data.get("conn")
    base_url = (getattr(cfg, "URL", "") or "").strip()
    if not base_url:
        logger.warning("URL missing in config.py; skipping")
        return

    ses = requests.Session()
    ses.headers.update({"User-Agent": UA, "Accept-Language": "he-IL,he;q=0.9,en;q=0.7"})
    try:
        r = ses.get(base_url, timeout=TIMEOUT)
        r.raise_for_status()
        pathlib.Path("./_debug_tustus.html").write_text(r.text, encoding="utf-8")
    except Exception as e:
        logger.warning(f"scrape_fail: {e}")
        return

    # 1) קודם כל — הפרסר הייעודי ל-show_item
    items = _parse_show_items_from_html(r.text, base_url)

    # 2) אם לא מצא כלום, נוותר — לא נכניס “זבל” ממקורות אחרים
    if not items:
        snippet = _clean(r.text[:600])
        logger.warning(f"scrape_ok but no items parsed (show_item only) | snippet='{snippet}'")
        return

    # 3) upsert ל-DB
    ins = upd = 0
    for it in items:
        dest = it["destination"]
        go   = it["go_date"]
        back = it.get("back_date") or ""
        key  = hashlib.sha1(f"{dest}|{go}|{back}|{it.get('price') or ''}".encode("utf-8")).hexdigest()[:16]

        row = conn.execute("""
            SELECT flight_key FROM flights
            WHERE destination=? AND COALESCE(go_date,'')=? AND COALESCE(back_date,'')=?
            LIMIT 1
        """, (dest, go, back)).fetchone()

        if row:
            conn.execute("""
                UPDATE flights
                SET name=?, link=?, price=?, go_depart=?, go_arrive=?, back_depart=?, back_arrive=?, seats=?, scraped_at=datetime('now')
                WHERE flight_key=?
            """, (it["name"], it["link"], it["price"], it.get("go_depart"), it.get("go_arrive"),
                  it.get("back_depart"), it.get("back_arrive"), it.get("seats"), key))
            upd += 1
        else:
```

### enrich_active_time(row)
**Calls:** get, human_duration_since
**Preview:**
```python
def enrich_active_time(row: dict):
    from utils import human_duration_since
    if not row:
        return row
    if not row.get("first_seen"):
        row["first_seen"] = row.get("scraped_at")
    row["active_for"] = human_duration_since(row.get("first_seen") or "")
    return row

import inspect as _inspect

```

### async run_monitor(conn, app)
**Doc:** Official monitor entrypoint.
Performs one monitoring tick by delegating to existing logic helpers if present.
Tries (async preferred): monitor_job, monitor, run_monitor_once, scrape_and_upsert, update_all, tick, refresh_once.
**Calls:** _fn, exception, get, getLogger, globals, iscoroutinefunction, warning
**Preview:**
```python
async def run_monitor(conn, app):
    """Official monitor entrypoint.
    Performs one monitoring tick by delegating to existing logic helpers if present.
    Tries (async preferred): monitor_job, monitor, run_monitor_once, scrape_and_upsert, update_all, tick, refresh_once.
    """
    # Candidate names ordered by likelihood
    _cands = [
        "monitor_job",
        "monitor",
        "run_monitor_once",
        "scrape_and_upsert",
        "update_all",
        "tick",
        "refresh_once",
    ]
    for _name in _cands:
        _fn = globals().get(_name)
        if _fn:
            try:
                if _inspect.iscoroutinefunction(_fn):
                    return await _fn(conn, app)
                # try common signatures
                try:
                    return _fn(conn, app)
                except TypeError:
                    try:
                        return _fn(app, conn)
                    except TypeError:
                        return _fn(conn)
            except Exception as _e:
                import logging as _log
                _log.getLogger("tustus.logic").exception("run_monitor: candidate %s failed", _name)
                raise
    # Fallback: no-op with log so the scheduler won't crash
    import logging as _log
    _log.getLogger("tustus.logic").warning("run_monitor: no candidate function found; tick skipped")
    return None

```
