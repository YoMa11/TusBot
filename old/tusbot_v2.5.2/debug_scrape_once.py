from __future__ import annotations
__file_version__ = "debug_scrape_once.py@1"  # added 2025-08-30 00:15
import sqlite3, logging, types, pathlib, re, json, urllib.parse
import requests
import config as cfg
from logic import monitor_job

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("debug")

EP_PATTERNS = [
    r'["\'](\/[^"\']*(?:Get|Offers|Flights|Deals|Ajax|API|api|Search|Results|LastMinute|Arkia|Home|Content)[^"\']*)["\']',
    r'["\'](https?:\/\/[^"\']*(?:Get|Offers|Flights|Deals|Ajax|API|api|Search|Results|LastMinute|Arkia|Home|Content)[^"\']*)["\']',
    r'fetch\(\s*["\']([^"\']+)["\']',
    r'url\s*:\s*["\']([^"\']+)["\']',
    r'xhr\.open\(\s*["\'](?:GET|POST)["\']\s*,\s*["\']([^"\']+)["\']',
]

def _join_url(base: str, cand: str) -> str:
    cand = cand.strip()
    if not cand: return cand
    if re.match(r"^https?://", cand, re.I): return cand
    if cand.startswith("//"):
        scheme = urllib.parse.urlparse(base).scheme or "https"
        return f"{scheme}:{cand}"
    return urllib.parse.urljoin(base, cand)

def _discovered_from_text(text: str, base_url: str, cross_host: bool=False):
    base_host = urllib.parse.urlparse(base_url).netloc
    urls = []
    for pat in EP_PATTERNS:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            u = _join_url(base_url, m.group(1))
            if not cross_host and urllib.parse.urlparse(u).netloc not in ("", base_host):
                continue
            urls.append(u)
    return list(dict.fromkeys(urls))

def _scan_scripts_for_endpoints(html: str, base_url: str, ses: requests.Session, limit=25, cross_host=False):
    from bs4 import BeautifulSoup as BS
    scripts_out = pathlib.Path("./_debug_endpoints"); scripts_out.mkdir(exist_ok=True)
    s = BS(html, "lxml")
    srcs = [x.get("src") for x in s.find_all("script") if x.get("src")]
    srcs = [_join_url(base_url, u) for u in srcs]
    srcs = list(dict.fromkeys(srcs))[:limit]
    eps = []
    for i, src in enumerate(srcs, 1):
        try:
            r = ses.get(src, timeout=20)
            (scripts_out / f"script_{i:02d}.js").write_text(r.text, encoding="utf-8")
            eps.extend(_discovered_from_text(r.text, base_url, cross_host=cross_host))
        except Exception as e:
            log.info("script fetch fail %s: %s", src, e)
    return list(dict.fromkeys(eps))

def main():
    url = cfg.URL.strip()
    db_path = getattr(cfg, "DB_PATH", "./flights.db")

    # context ל-monitor_job
    class DummyApp(types.SimpleNamespace): ...
    class DummyCtx(types.SimpleNamespace): ...
    conn = sqlite3.connect(db_path, check_same_thread=False); conn.row_factory = sqlite3.Row
    ctx = DummyCtx(application=DummyApp(bot_data={"conn": conn}))

    ses = requests.Session()
    ses.headers.update({"User-Agent": getattr(cfg, "USER_AGENT", "Mozilla/5.0"),
                        "Accept-Language":"he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7"})
    r = ses.get(url, timeout=getattr(cfg, "REQUEST_TIMEOUT", 20))
    r.raise_for_status()
    pathlib.Path("./_debug_tustus.html").write_text(r.text, encoding="utf-8")
    log.info("saved HTML snapshot to %s", pathlib.Path("./_debug_tustus.html").resolve())

    base_host = urllib.parse.urlparse(url).netloc
    eps = _discovered_from_text(r.text, url, cross_host=False)
    eps_js = _scan_scripts_for_endpoints(r.text, url, ses, limit=25, cross_host=False)
    eps = list(dict.fromkeys(eps + eps_js))
    log.info("ENDPOINTS TOTAL (%d):", len(eps))
    outdir = pathlib.Path("./_debug_endpoints"); outdir.mkdir(exist_ok=True)

    found_total = 0
    for i, ep in enumerate(eps, 1):
        try:
            rr = ses.get(ep, timeout=20, headers={"Referer": url, **ses.headers})
            ctype = rr.headers.get("Content-Type","")
            fn = outdir / f"ep_{i:02d}_{urllib.parse.quote(ep, safe='')[:80]}.txt"
            fn.write_text(rr.text, encoding="utf-8")
            text_preview = rr.text[:200].replace("\n"," ")
            log.info("  %2d) %s -> %s | %d bytes | preview: %s", i, ep, ctype, len(rr.text), text_preview)
            if "application/json" in ctype or rr.text.strip().startswith(("{","[")):
                try:
                    data = json.loads(rr.text)
                    from logic import _walk_json as WALK  # type: ignore
                    items = WALK(data)
                    # **סינון וולידי** כמו בלוגיק
                    from logic import _valid_item as VLD  # type: ignore
                    items = [it for it in items if VLD(it)]
                    found_total += len(items)
                    log.info("      JSON items (valid): %d", len(items))
                except Exception as e:
                    log.info("      JSON parse failed: %s", e)
        except Exception as e:
            log.info("  %2d) %s -> ERROR: %s", i, ep, e)

    log.info("JSON-like items found across endpoints: %d", found_total)

    # הרצת monitor_job שתכניס ל-DB אם נמצא משהו
    res = monitor_job(ctx)
    log.info("monitor_job returned: %r", res)

    n = conn.execute("SELECT COUNT(*) FROM flights").fetchone()[0]
    log.info("✅ flights in DB: %d", n)
    for row in conn.execute("""SELECT destination, COALESCE(price,''), go_date, back_date, scraped_at
                               FROM flights ORDER BY scraped_at DESC LIMIT 10"""):
        log.info("• %s | %s₪ | %s→%s | %s", row[0], row[1], row[2], row[3], row[4])

if __name__ == "__main__":
    main()
