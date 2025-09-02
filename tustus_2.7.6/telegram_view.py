# telegram_view.py
from __future__ import annotations
from typing import List, Tuple, Iterable
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

# מפה ממדינה לדגל (נוסיף עוד בהדרגה; ברירת מחדל בלי דגל)
FLAG_BY_COUNTRY = {
    "יוון": "🇬🇷",
    "קפריסין": "🇨🇾",
    "הונגריה": "🇭🇺",
    "צ'כיה": "🇨🇿",
    "מונטנגרו": "🇲🇪",
    "טנזניה": "🇹🇿",  # זנזיבר (טנזניה)
    "ישראל": "🇮🇱",
    "אלבניה": "🇦🇱",
}

def flag_for(country: str) -> str:
    return FLAG_BY_COUNTRY.get((country or "").strip(), "")

def group_by_country(rows: Iterable[Tuple[str, str, object]]) -> List[Tuple[str, List[Tuple[str,str]]]]:
    # rows: (city, country, None)
    grouped = {}
    for city, country, _ in rows:
        grouped.setdefault(country or "", []).append((city, country))
    # סדר מדינות ואז ערים
    return sorted(
        [(country, sorted(cities, key=lambda c: c[0])) for country, cities in grouped.items()],
        key=lambda t: t[0]
    )

def build_destinations_keyboard(rows: Iterable[Tuple[str, str, object]], selected: List[str]) -> InlineKeyboardMarkup:
    """
    בונה מקלדת: כפתור “כל היעדים 🌍” ואז כל הערים בקיבוץ לפי מדינה.
    טקסט הכפתור: "<עיר> <דגל>" בלבד (בלי שם מדינה ובלי מחיר).
    callback_data בפורמט: "tog:<עיר>|<מדינה>"
    """
    keyboard: List[List[InlineKeyboardButton]] = []
    # כפתור הכל
    keyboard.append([InlineKeyboardButton("כל היעדים 🌍", callback_data="tog:*")])

    grouped = group_by_country(rows)
    row_buf: List[InlineKeyboardButton] = []
    for country, cities in grouped:
        for city, _country in cities:
            flag = flag_for(_country)
            text = f"{city} {flag}".strip()
            data = f"tog:{city}|{_country or ''}"
            row_buf.append(InlineKeyboardButton(text, callback_data=data))
            if len(row_buf) == 2:  # שתי עמודות
                keyboard.append(row_buf)
                row_buf = []
    if row_buf:
        keyboard.append(row_buf)

    # שורת פעולה תחתונה
    keyboard.append([
        InlineKeyboardButton("רענון 🔄", callback_data="refresh"),
        InlineKeyboardButton("סיכום יעדים 📊", callback_data="sum"),
    ])
    return InlineKeyboardMarkup(keyboard)
