# -*- coding: utf-8 -*-
from __future__ import annotations
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def build_home_kb() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("כל הטיסות ✈️", callback_data="HOME_ALL"),
            InlineKeyboardButton("מחירים 💵", callback_data="HOME_PRICES"),
            InlineKeyboardButton("יעדים 🗺️", callback_data="HOME_DESTS"),
        ],
        [
            InlineKeyboardButton("התראות 🔔", callback_data="HOME_ALERTS"),
            InlineKeyboardButton("הגדרות ⚙️", callback_data="HOME_SETTINGS"),
            InlineKeyboardButton("עוד… ➕", callback_data="HOME_MORE"),
        ],
        [InlineKeyboardButton("רענון ♻️", callback_data="HOME_REFRESH")],
    ]
    return InlineKeyboardMarkup(rows)

def build_dests_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("בחר הכל ✅", callback_data="DESTS_SELECT_ALL")],
        [InlineKeyboardButton("↩️ חזרה למסך הבית", callback_data="HOME_REFRESH")],
    ]
    return InlineKeyboardMarkup(rows)
