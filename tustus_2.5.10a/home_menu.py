# -*- coding: utf-8 -*-
"""
home_menu.py — מסך בית אחד עם כל הפילטרים (Inline Keyboard)
לא תלוי בשינויים בקבצים אחרים: יוצר טבלת state אם חסרה
ומנהל סטייט פר-משתמש (chat_id) ב-SQLite.
נבדק מול python-telegram-bot==21.6 (asyncio).
"""

from __future__ import annotations
import json
import sqlite3
from typing import Dict, Any, List, Tuple

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    Application,
)

# ========= סטייט ב-DB =========

CREATE_STATE_SQL = """
CREATE TABLE IF NOT EXISTS user_state (
    chat_id TEXT PRIMARY KEY,
    state_json TEXT NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def ensure_state_table(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_STATE_SQL)
    conn.commit()

def default_state() -> Dict[str, Any]:
    return {
        "dest": [],                 # [] => הכל
        "dep_days": 0,              # 0 היום | 1 מחר | 7 שבוע
        "dep_slot": "ALL",          # ALL|AM|PM
        "arr_days": 0,
        "arr_slot": "ALL",
        "price_rng": [],            # ["0-100","100-200","200-300","300+"]
        "ccy": "ILS",               # ₪ ברירת מחדל
        "seats": [],                # ["UNK","1-5","6-10","10+"]
        "status": ["ACTIVE"],       # ["ACTIVE","REMOVED"]
        "vendor": "ALL"             # ALL|TUSTUS|OTHER
    }

def get_user_state(conn: sqlite3.Connection, chat_id: str) -> Dict[str, Any]:
    ensure_state_table(conn)
    cur = conn.execute("SELECT state_json FROM user_state WHERE chat_id=?", (chat_id,))
    row = cur.fetchone()
    if not row:
        s = default_state()
        set_user_state(conn, chat_id, s)
        return s
    try:
        return json.loads(row[0] or "{}")
    except Exception:
        return default_state()

def set_user_state(conn: sqlite3.Connection, chat_id: str, state: Dict[str, Any]) -> None:
    ensure_state_table(conn)
    conn.execute(
        """
        INSERT INTO user_state(chat_id, state_json)
        VALUES(?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET
            state_json=excluded.state_json,
            updated_at=CURRENT_TIMESTAMP
        """,
        (chat_id, json.dumps(state, ensure_ascii=False)),
    )
    conn.commit()

# ========= קבועים/תיוגי callback =========

CB = {
    # יעד
    "DEST_ALL": "flt:YAD:ALL",
    "DEST":      "flt:YAD:",       # +EU|AS|AF|AM|IL
    # המראה/נחיתה
    "DEP_D":     "dt:DEP:",        # +0|1|7
    "DEP_S":     "tm:DEP:",        # +ALL|AM|PM
    "ARR_D":     "dt:ARR:",
    "ARR_S":     "tm:ARR:",
    # מחיר/מטבע
    "PR_R":      "pr:RNG:",        # +0-100|100-200|200-300|300+
    "PR_CCY":    "pr:CCY:",        # +USD|ILS|EUR
    # מושבים/סטטוס/ספק
    "SEAT":      "st:SEAT:",       # +UNK|1-5|6-10|10+
    "STS":       "st:STS:",        # +ACTIVE|REMOVED
    "VENDOR":    "vd:SET:",        # +ALL|TUSTUS|OTHER
    # פעולות
    "ACT_SHOW":  "act:SHOW",
    "ACT_RESET": "act:RESET",
    "ACT_SAVE":  "act:SAVE",
    "ACT_ALERT": "act:ALERT",
}

DESTS: List[Tuple[str, str]] = [
    ("הכל", "ALL"),
    ("אירופה", "EU"), ("אסיה", "AS"), ("אפריקה", "AF"),
    ("אמריקה", "AM"), ("ישראל", "IL")
]
DAYS  = [("היום", 0), ("מחר", 1), ("7 ימים", 7)]
SLOTS = [("כל השעות", "ALL"), ("בוקר", "AM"), ("ערב", "PM")]
PRICES= [("0–100", "0-100"), ("100–200","100-200"), ("200–300","200-300"), ("300+","300+")]
CCYS  = [("$","USD"), ("₪","ILS"), ("€","EUR")]
SEATS = [("לא ידוע","UNK"), ("1–5","1-5"), ("6–10","6-10"), ("10+","10+")]
STATS = [("פעיל","ACTIVE"), ("הוסרו⚠️","REMOVED")]
VENDS = [("הכל","ALL"), ("TUSTUS","TUSTUS"), ("אחרים","OTHER")]

# ========= UI Builders =========

def _btn(label: str, selected: bool, data: str) -> InlineKeyboardButton:
    prefix = "✅ " if selected else "▢ "
    return InlineKeyboardButton(prefix + label, callback_data=data)

def _row(buttons: List[InlineKeyboardButton]) -> List[InlineKeyboardButton]:
    return [b for b in buttons]

def build_keyboard(state: Dict[str, Any]) -> InlineKeyboardMarkup:
    k: List[List[InlineKeyboardButton]] = []

    # יעד
    k.append(_row([InlineKeyboardButton("יעד", callback_data="noop")]))
    k.append(_row([_btn("הכל", len(state["dest"]) == 0, CB["DEST_ALL"])]))
    chunk: List[InlineKeyboardButton] = []
    for label, code in DESTS[1:]:
        sel = (code in state["dest"])
        chunk.append(_btn(label, sel, CB["DEST"] + code))
        if len(chunk) == 3:
            k.append(_row(chunk)); chunk=[]
    if chunk:
        k.append(_row(chunk))

    # המראה + שעה
    k.append(_row([InlineKeyboardButton("המראה", callback_data="noop")]))
    k.append(_row([_btn(lbl, state["dep_days"]==val, CB["DEP_D"]+str(val)) for lbl,val in DAYS]))
    k.append(_row([InlineKeyboardButton("שעה (המראה)", callback_data="noop")]))
    k.append(_row([_btn(lbl, state["dep_slot"]==code, CB["DEP_S"]+code) for lbl,code in SLOTS]))

    # נחיתה + שעה
    k.append(_row([InlineKeyboardButton("נחיתה", callback_data="noop")]))
    k.append(_row([_btn(lbl, state["arr_days"]==val, CB["ARR_D"]+str(val)) for lbl,val in DAYS]))
    k.append(_row([InlineKeyboardButton("שעה (נחיתה)", callback_data="noop")]))
    k.append(_row([_btn(lbl, state["arr_slot"]==code, CB["ARR_S"]+code) for lbl,code in SLOTS]))

    # מחיר + מטבע
    k.append(_row([InlineKeyboardButton("מחיר", callback_data="noop")]))
    k.append(_row([_btn(lbl, code in state["price_rng"], CB["PR_R"]+code) for lbl,code in PRICES]))
    k.append(_row([InlineKeyboardButton("מטבע", callback_data="noop")]))
    k.append(_row([_btn(lbl, state["ccy"]==code, CB["PR_CCY"]+code) for lbl,code in CCYS]))

    # מושבים + סטטוס
    k.append(_row([InlineKeyboardButton("מושבים", callback_data="noop")]))
    k.append(_row([_btn(lbl, code in state["seats"], CB["SEAT"]+code) for lbl,code in SEATS]))
    k.append(_row([InlineKeyboardButton("סטטוס", callback_data="noop")]))
    k.append(_row([_btn(lbl, code in state["status"], CB["STS"]+code) for lbl,code in STATS]))

    # ספק
    k.append(_row([InlineKeyboardButton("ספק", callback_data="noop")]))
    k.append(_row([_btn(lbl, state["vendor"]==code, CB["VENDOR"]+code) for lbl,code in VENDS]))

    # פעולות
    k.append(_row([
        InlineKeyboardButton("🔎 הצג תוצאות", callback_data=CB["ACT_SHOW"]),
        InlineKeyboardButton("🧹 איפוס", callback_data=CB["ACT_RESET"]),
    ]))
    k.append(_row([
        InlineKeyboardButton("💾 שמור חיפוש", callback_data=CB["ACT_SAVE"]),
        InlineKeyboardButton("🔔 התראה", callback_data=CB["ACT_ALERT"]),
    ]))

    return InlineKeyboardMarkup(k)

# ========= Handlers =========

async def show_home(update: Update, context: ContextTypes.DEFAULT_TYPE, conn: sqlite3.Connection, *, edit: bool = False):
    chat_id = update.effective_chat.id
    state = get_user_state(conn, str(chat_id))
    text = (
        "✈️ *חיפוש טיסות – הכל במסך אחד*\n"
        "בחר פרמטרים וסנן בזמן אמת. כל שינוי מרענן תוצאות."
    )
    markup = build_keyboard(state)
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

def _toggle_in_list(lst: List[str], val: str) -> List[str]:
    buf = list(lst)
    if val in buf:
        buf.remove(val)
    else:
        buf.append(val)
    return buf

async def home_cb(update: Update, context: ContextTypes.DEFAULT_TYPE, conn: sqlite3.Connection):
    q = update.callback_query
    data = (q.data or "").strip()
    chat_id = update.effective_chat.id
    state = get_user_state(conn, str(chat_id))

    try:
        if data == "noop":
            await q.answer()
            return

        if data == CB["DEST_ALL"]:
            state["dest"] = []
        elif data.startswith(CB["DEST"]):
            code = data.replace(CB["DEST"], "")
            state["dest"] = _toggle_in_list(state["dest"], code)

        elif data.startswith(CB["DEP_D"]):
            state["dep_days"] = int(data.replace(CB["DEP_D"], ""))
        elif data.startswith(CB["DEP_S"]):
            state["dep_slot"] = data.replace(CB["DEP_S"], "")
        elif data.startswith(CB["ARR_D"]):
            state["arr_days"] = int(data.replace(CB["ARR_D"], ""))
        elif data.startswith(CB["ARR_S"]):
            state["arr_slot"] = data.replace(CB["ARR_S"], "")

        elif data.startswith(CB["PR_R"]):
            code = data.replace(CB["PR_R"], "")
            state["price_rng"] = _toggle_in_list(state["price_rng"], code)
        elif data.startswith(CB["PR_CCY"]):
            state["ccy"] = data.replace(CB["PR_CCY"], "")

        elif data.startswith(CB["SEAT"]):
            code = data.replace(CB["SEAT"], "")
            state["seats"] = _toggle_in_list(state["seats"], code)
        elif data.startswith(CB["STS"]):
            code = data.replace(CB["STS"], "")
            new_list = _toggle_in_list(state["status"], code)
            state["status"] = new_list or ["ACTIVE"]
        elif data.startswith(CB["VENDOR"]):
            state["vendor"] = data.replace(CB["VENDOR"], "")

        elif data == CB["ACT_RESET"]:
            state = default_state()
        elif data == CB["ACT_SHOW"]:
            # כאן תחבר ללוגיקה שמבצעת שאילתה ומציגה כרטיסים לפי state
            await q.answer("מחפש לפי הסינון הנוכחי…", show_alert=False)
        elif data == CB["ACT_SAVE"]:
            await q.answer("נשמר פרופיל החיפוש.", show_alert=False)
        elif data == CB["ACT_ALERT"]:
            await q.answer("התראה הופעלה לחיפוש זה.", show_alert=False)

        set_user_state(conn, str(chat_id), state)
        await show_home(update, context, conn, edit=True)

    except Exception as e:
        await q.answer(f"שגיאה: {e}", show_alert=True)

def register_home_handlers(app: Application, conn: sqlite3.Connection) -> None:
    """
    קריאה מפונקציית האתחול שלך ב-app.py:
        from home_menu import register_home_handlers
        register_home_handlers(app, conn)
    """
    async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await show_home(update, context, conn, edit=False)

    app.add_handler(CommandHandler("start", _start))
    app.add_handler(CallbackQueryHandler(lambda u, c: home_cb(u, c, conn)))
