# -*- coding: utf-8 -*-
from __future__ import annotations
import logging
from typing import Optional

log = logging.getLogger("tustus.utils")

def money_fmt(raw: str) -> str:
    """הצגת מחיר בדיוק כפי שמגיע מה-DB – ללא המרות/מכפלות."""
    if raw is None:
        return "-"
    return str(raw)

def arrow_dir(h1: str, h2: str) -> str:
    """בחר חץ לפי סדר כרונולוגי (→ לשעה מאוחרת יותר)."""
    try:
        return "→" if h1 and h2 and h2 > h1 else "←"
    except Exception:
        return "→"

