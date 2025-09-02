#!/usr/bin/env python3
import os, re, zipfile, shutil, time, glob, textwrap, hashlib, sys

VER = "2.4.7"

def readf(p): return open(p,"r",encoding="utf-8",errors="ignore").read()
def writef(p,s): open(p,"w",encoding="utf-8").write(s)

def stamp_module(text, ver=VER):
    """Insert __version__ safely after any __future__ imports; add build footer."""
    lines = text.splitlines(True)
    idx = -1
    for i, ln in enumerate(lines[:20]):
        if ln.strip().startswith("from __future__ import"):
            idx = i
    if "__version__" not in "".join(lines[:60]):
        insert_at = idx + 1 if idx >= 0 else 0
        lines.insert(insert_at, f'__version__ = "{ver}"\n')
    out = "".join(lines)
    if not out.endswith("\n"): out += "\n"
    out += f'# __build__: tusbot v{ver} @ {time.strftime("%Y-%m-%d %H:%M:%S")}\n'
    return out

def replace_show_all(text):
    return text.replace("תראה עכשיו","כל הטיסות")

HELPERS_BLOCK = textwrap.dedent(r"""
# ===== v2.4.7 helpers (UI/logic) =====
def _flag_for_destination(dest: str) -> str:
    d = (dest or "").strip()
    MAP = {
        "יוון":"🇬🇷","קורפו":"🇬🇷","אתונה":"🇬🇷",
        "איטליה":"🇮🇹","רומא":"🇮🇹","מילאנו":"🇮🇹",
        "קפריסין":"🇨🇾","לרנקה":"🇨🇾","פאפוס":"🇨🇾",
        "טורקיה":"🇹🇷","אנטליה":"🇹🇷","איסטנבול":"🇹🇷",
        "גאורגיה":"🇬🇪","בטומי":"🇬🇪","טביליסי":"🇬🇪",
        "ספרד":"🇪🇸","ברצלונה":"🇪🇸","מדריד":"🇪🇸",
        "צרפת":"🇫🇷","פריז":"🇫🇷",
        "ישראל":"🇮🇱","אילת":"🇮🇱","תל אביב":"🇮🇱",
    }
    for k,v in MAP.items():
        if k in d: return v
    return "🌍"

def _humanize_delta_sec(sec: int) -> str:
    m, s = divmod(max(0,int(sec)), 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    parts = []
    if d: parts.append(f"{d}י")
    if h: parts.append(f"{h}ש")
    if m: parts.append(f"{m}ד")
    if not parts: parts.append(f"{s}ש")
    return " ".join(parts)

def _price_display(f: dict) -> str:
    raw = f.get("raw_price") or f.get("price_raw") or ""
    if isinstance(raw,str) and raw.strip():
        return html.escape(raw.strip())
    price = f.get("price")
    cur = (f.get("currency") or "").upper()
    dest = f.get("destination") or f.get("name") or ""
    if price in (None,""): return "—"
    try: p = int(price)
    except Exception: return html.escape(str(price))
    return f"{p}₪" if (cur=="ILS" or "אילת" in dest) else f"${p}"

def _arrow(a: str, b: str) -> str:
    try:
        return "⟶" if (a or "") <= (b or "") else "⟵"
    except Exception:
        return "⟶"

def _format_card(f: dict) -> str:
    link = f.get("link") or f.get("url") or ""
    title = f.get("name") or f.get("destination") or "טיסה"
    flag = _flag_for_destination(f.get("destination") or f.get("name") or "")
    head = f'<b><a href="{html.escape(link)}">{html.escape(title)}</a></b> {flag}' if link else f"<b>{html.escape(title)}</b> {flag}"
    gd,ga = (f.get("go_depart") or ""), (f.get("go_arrive") or "")
    bd,ba = (f.get("back_depart") or ""), (f.get("back_arrive") or "")
    gdate = f.get("go_date") or ""
    bdate = f.get("back_date") or ""
    line_go   = f"🛫 {gdate} — {html.escape(gd)} {_arrow(gd,ga)} {html.escape(ga)}"
    line_back = f"🛬 {bdate} — {html.escape(bd)} {_arrow(bd,ba)} {html.escape(ba)}"
    price_txt = _price_display(f)
    seats     = f.get("seats")
    seats_txt = "🎟️ לא ידוע" if seats in (None,"","None") else f"🪑 {seats}"
    # uptime
    fs = f.get("first_seen"); uptime = ""
    if fs:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(str(fs).replace("Z","").replace(" ", "T"))
            delta = (datetime.utcnow() - dt).total_seconds()
            uptime = f"⏱ פעילה {_humanize_delta_sec(int(delta))}"
        except Exception:
            pass
    removed = ""
    if str(f.get("is_removed") or "").strip() in ("1","true","True") or f.get("removed_at"):
        removed = "  •  ❌ הוסר"
    lines = [head, f"💸 {price_txt}    {seats_txt}{removed}", line_go, line_back]
    if uptime: lines.append(uptime)
    return "\n".join(lines)

def _build_price_kb(conn, prefs) -> InlineKeyboardMarkup:
    def table_has(col):
        try:
            cur = conn.execute("PRAGMA table_info(flights)")
            cols = [r[1] for r in cur.fetchall()]
            return col in cols
        except Exception:
            return False
    rows = []
    try:
        if table_has("raw_price"):
            cur = conn.execute("SELECT DISTINCT raw_price FROM flights WHERE raw_price IS NOT NULL AND TRIM(raw_price)<>''")
            rows = [(r[0], r[0]) for r in cur.fetchall()]
        elif table_has("currency"):
            cur = conn.execute("SELECT DISTINCT price, UPPER(currency) FROM flights WHERE price IS NOT NULL ORDER BY price")
            rows = [((f"${p}" if (c or "")!="ILS" else f"{p}₪"), str(p)) for p,c in cur.fetchall()]
        else:
            cur = conn.execute("SELECT DISTINCT price, CASE WHEN destination LIKE '%אילת%' THEN 'ILS' ELSE 'USD' END AS cur FROM flights WHERE price IS NOT NULL ORDER BY price")
            rows = [((f"${p}" if c!='ILS' else f"{p}₪"), str(p)) for p,c in cur.fetchall()]
    except Exception:
        rows = []
    if not rows:
        rows = [("$100","100"),("$150","150"),("$300","300"),("₪200","200")]
    btns, row = [], []
    for i,(label,val) in enumerate(rows,1):
        row.append(InlineKeyboardButton(label, callback_data=f"PRICE_SET_{val}"))
        if i%3==0: btns.append(row); row=[]
    if row: btns.append(row)
    btns.append([InlineKeyboardButton("❌ ניקוי", callback_data="PRICE_CLEAR")])
    btns.append([InlineKeyboardButton("🏠 בית", callback_data="HOME")])
    return InlineKeyboardMarkup(btns)

def _build_destinations_kb(conn, selected_csv: str, page: int = 1, per_page: int = 20) -> InlineKeyboardMarkup:
    cur = conn.execute("SELECT DISTINCT destination FROM flights WHERE destination IS NOT NULL AND destination<>'' ORDER BY destination COLLATE NOCASE")
    all_d = [r[0] for r in cur.fetchall()]
    selected = [d.strip() for d in (selected_csv or "").split(",") if d.strip()]
    start = (page-1)*per_page
    chunk = all_d[start:start+per_page]
    kb = [[
        InlineKeyboardButton("✅ בחר הכל", callback_data="DESTS_SELECT_ALL"),
        InlineKeyboardButton("💾 שמירה", callback_data="DEST_SAVE"),
        InlineKeyboardButton("🏠 בית", callback_data="HOME"),
    ]]
    row = []
    for i, d in enumerate(chunk,1):
        checked = "✅" if d in selected else "⬜️"
        row.append(InlineKeyboardButton(f"{checked} {d}", callback_data=f"DEST_TOGGLE::{d}|PAGE_{page}"))
        if i%4==0: kb.append(row); row=[]
    if row: kb.append(row)
    total_pages = max(1, (len(all_d)+per_page-1)//per_page)
    if total_pages>1:
        nav = []
        if page>1: nav.append(InlineKeyboardButton("« הקודם", callback_data=f"DESTS_PAGE_{page-1}"))
        nav.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="DESTS"))
        if page<total_pages: nav.append(InlineKeyboardButton("הבא »", callback_data=f"DESTS_PAGE_{page+1}"))
        kb.append(nav)
    return InlineKeyboardMarkup(kb)
""")

def patch_handlers(code: str) -> str:
    out = replace_show_all(code)
    # inject helpers (once), before DB helpers section if exists
    if "_format_card(" not in out:
        anchor = out.find("# ===== DB helpers =====")
        insert_at = anchor if anchor != -1 else len(out)//3
        out = out[:insert_at] + "\n" + HELPERS_BLOCK + "\n" + out[insert_at:]
    # use our formatter in feed
    out = re.sub(r"cards\s*=\s*\[.*?format_flight_card.*?\]", "cards = [_format_card(f) for f in flights]", out, flags=re.DOTALL)
    # replace price menu to dynamic builder
    out = re.sub(r"kb\s*=\s*price_menu_kb\(.*?\)", "kb = _build_price_kb(conn, prefs)", out)
    # destinations page -> our builder (first page)
    out = re.sub(r"kb\s*=\s*destinations_page\([^\)]*\)", "kb = _build_destinations_kb(conn, prefs.get('destinations_csv') or '', page=1, per_page=20)", out)
    # dests paging
    out = re.sub(r"kb\s*=\s*destinations_page\([^\n]+", "kb = _build_destinations_kb(conn, prefs.get('destinations_csv') or '', page=page, per_page=20)", out)
    # add DESTS_SELECT_ALL branch if missing
    if "DESTS_SELECT_ALL" not in out:
        out = out.replace('if key == "DEST_SAVE":', textwrap.dedent(r'''
        if key == "DESTS_SELECT_ALL":
            dests_all = get_all_destinations(conn)
            csv = ",".join(dests_all)
            update_prefs(conn, chat_id, destinations_csv=csv)
            prefs = get_prefs(conn, chat_id)
            header = "🎯 בחר/י יעדים (בחירה מרובה) — ✅/⬜️"
            kb = _build_destinations_kb(conn, prefs.get("destinations_csv") or "", page=1, per_page=20)
            await update.callback_query.edit_message_text(header, reply_markup=kb)
            return

        if key == "DEST_SAVE":
        '''))
    # summary with flags + last crawl
    out = re.sub(r"if key.startswith\(\"SUMMARY\"\).*?return", textwrap.dedent(r'''
    if key.startswith("SUMMARY") or key == "סיכום לפי יעד":
        row = conn.execute("SELECT MAX(scraped_at) FROM flights").fetchone()
        last_ts = row[0] if row else None
        if last_ts:
            cur = conn.execute(
                "SELECT destination, COUNT(*) AS c FROM flights WHERE scraped_at=? AND destination IS NOT NULL AND destination<>'' GROUP BY destination ORDER BY c DESC, destination LIMIT 100",
                (last_ts,)
            )
        else:
            cur = conn.execute(
                "SELECT destination, COUNT(*) AS c FROM flights WHERE destination IS NOT NULL AND destination<>'' GROUP BY destination ORDER BY c DESC, destination LIMIT 100"
            )
        rows = cur.fetchall()
        if not rows:
            txt = "אין כרגע טיסות זמינות לריצה האחרונה."
        else:
            lines = ["📊 סיכום לפי יעד (זמין כרגע):", ""]
            for d,c in rows:
                lines.append(f"{_flag_for_destination(d)}  {d} — {c}")
            txt = "\n".join(lines)
        if q:
            try: await q.answer()
            except: pass
            try:
                await q.edit_message_text(txt, reply_markup=feed_nav_kb(), parse_mode=ParseMode.HTML)
                return
            except BadRequest:
                pass
        await context.bot.send_message(chat_id=chat_id, text=txt, reply_markup=feed_nav_kb(), parse_mode=ParseMode.HTML)
        return
    '''), out, flags=re.DOTALL)
    # accept "כל הטיסות" too
    out = out.replace('"כל הדילים"):', '"כל הדילים", "כל הטיסות"):')
    # “centered” headers
    out = out.replace('"💸 מחיר מקסימלי"', '"▫️▫️▫️  💸 מחירים  ▫️▫️▫️"')
    out = out.replace('"🪑 מינימום מושבים"', '"▫️▫️▫️  🪑 מינימום מושבים  ▫️▫️▫️"')
    out = out.replace('"🗓 בחר/י טווח תאריכים"', '"▫️▫️▫️  🗓 בחר/י טווח תאריכים  ▫️▫️▫️"')
    return out

def main():
    if len(sys.argv) < 2:
        print("usage: python3 patch_zip_to_2_4_7.py /path/to/tusbot_v2.4.6.zip")
        sys.exit(2)
    in_zip = sys.argv[1]
    if not os.path.exists(in_zip):
        print("input ZIP not found:", in_zip); sys.exit(2)
    work = os.path.abspath("_patch_work_2_4_7")
    if os.path.exists(work): shutil.rmtree(work)
    os.makedirs(work, exist_ok=True)

    # extract
    with zipfile.ZipFile(in_zip,"r") as z: z.extractall(work)

    # find roots containing app.py
    roots = [r for r,_,f in os.walk(work) if "app.py" in f]
    if not roots:
        print("app.py not found inside ZIP"); sys.exit(2)

    modified = []
    for root in roots:
        # telegram_view.py
        tv = os.path.join(root,"telegram_view.py")
        if os.path.exists(tv):
            t = stamp_module(replace_show_all(readf(tv)))
            writef(tv,t); modified.append(tv)
        # handlers.py
        hp = os.path.join(root,"handlers.py")
        if os.path.exists(hp):
            h = readf(hp)
            h = stamp_module(patch_handlers(h))
            writef(h,h); modified.append(hp)
        # app.py
        ap = os.path.join(root,"app.py")
        if os.path.exists(ap):
            a = stamp_module(replace_show_all(readf(ap)))
            writef(ap,a); modified.append(ap)
        # stamp all other py
        for py in glob.glob(os.path.join(root,"**","*.py"), recursive=True):
            if py in modified: continue
            try:
                s = readf(py)
                s2 = stamp_module(s)
                if s2 != s:
                    writef(py,s2); modified.append(py)
            except Exception:
                pass
        # release notes
        rn = os.path.join(root,"release_notes.txt")
        now = time.strftime("%Y-%m-%d %H:%M")
        entry = (f"v{VER} ({now})\n"
                 "- UI: \"כל הטיסות\" במקום \"תראה עכשיו\".\n"
                 "- מחיר: תפריט דינמי לפי מחירים מה-DB עם סימן מטבע מקורי.\n"
                 "- יעדים: כפתור \"בחר הכל\" + פריסה נוחה.\n"
                 "- כרטיסי טיסה: קישור על היעד, חצים לשעה המאוחרת, מושבים לא ידוע = 🎟️, \"⏱ פעילה\".\n"
                 "- סיכום לפי יעד: דגלים ולפי הריצה האחרונה.\n"
                 "- חותמות גרסה לכל קבצי .py.\n")
        if os.path.exists(rn):
            writef(rn, entry + "\n" + readf(rn))
        else:
            writef(rn, entry)

    # rezip
    out_zip = os.path.abspath(os.path.join(os.path.dirname(in_zip), "tusbot_v2.4.7.zip"))
    with zipfile.ZipFile(out_zip,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for root in roots:
            for r,_,fs in os.walk(root):
                for fn in fs:
                    fp = os.path.join(r,fn)
                    z.write(fp, arcname=os.path.relpath(fp, root))
    print("✅ built:", out_zip)
    print("🔐 sha256:", hashlib.sha256(open(out_zip,"rb").read()).hexdigest())
    print("✏️ modified files:", len(modified))

if __name__ == "__main__":
    main()
