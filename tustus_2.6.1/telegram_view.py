# -*- coding: utf-8 -*-
from __future__ import annotations
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def build_main_menu(filters: dict | None = None) -> InlineKeyboardMarkup:
    # אופציה 1: הכל על המסך הראשון
    rows = [
        [
            InlineKeyboardButton("✈️ טיסות חדשות", callback_data="FILTER_NEW"),
            InlineKeyboardButton("🌍 יעדים", callback_data="DESTS")
        ],
        [
            InlineKeyboardButton("💲 מחירים", callback_data="PRICES"),
            InlineKeyboardButton("📅 תאריכים", callback_data="DATES")
        ],
        [
            InlineKeyboardButton("🔁 רענן", callback_data="REFRESH"),
            InlineKeyboardButton("ℹ️ עזרה", callback_data="HELP")
        ]
    ]
    return InlineKeyboardMarkup(rows)
