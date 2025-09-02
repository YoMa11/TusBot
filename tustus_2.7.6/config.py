# config.py
from __future__ import annotations

import os
import logging
from pathlib import Path

# ===== Meta =====
__file_version__ = "tustus_2.5.10a"  # updated 2025-08-30 18:58  # added 2025-08-30 18:21
SCRIPT_VERSION = "V2.5.10a"

# ===== Paths =====
ROOT = Path(__file__).resolve().parent

# תיקיות נתונים וגיבויים (יבָּּנו אוטומטית אם חסרות)
DATA_DIR = ROOT / "data"
BACKUPS_DIR = ROOT / "backups"
DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

# קובץ ה-SQLite (עובד באופן יחסי לפרויקט)
DB_PATH = DATA_DIR / "flights.db"

# ===== Bot / Secrets =====
# מומלץ לשמור את הטוקן במשתנה סביבה BOT_TOKEN (בטוח יותר):
# export BOT_TOKEN="xxxxx:yyyyy"
# אם אין—ייפול חזרה לערך שלמטה (אפשר להשאיר/להחליף בפלֵיסְהוֹלְדֶר).
BOT_TOKEN = os.getenv("BOT_TOKEN", "8355167350:AAFHXoKgOR7Ja0NOncn2_9PY0hp3Kn4tNBo").strip()

# ===== Scraper Source =====
URL = "https://www.tustus.co.il/Arkia/Home"

# ===== Scraper Tuning =====
REQUEST_TIMEOUT = 15  # שניות
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# "חלון חדש" לטיסות — כמה שעות אחורה נחשבות "חדשות"
NEW_WINDOW_HOURS = 24

# ===== Monitor / Scheduler =====
# מרווח בין סריקות (שניות)
INTERVAL = 60
# אם True, תצוגת המוניטור תראה "⏱  פעילה" כברירת מחדל
MONITOR_QUIET_ACTIVE_TIME = True

# ===== Logging =====
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_LEVEL = logging.DEBUG

# רישום לקובץ לוג מקומי (ניתן לבטל ע"י False)
LOG_TO_FILE = True
LOG_DIR = ROOT  # אפשר לשנות ל- ROOT / "logs"
LOG_FILE = str(LOG_DIR / "bot.log")
ERROR_LOG_FILE = str(LOG_DIR / "bot.err.log")

# הפעלת לוג בסיסי (חד-פעמי בעת ייבוא הקונפיג)
logging.getLogger().setLevel(LOG_LEVEL)
if LOG_TO_FILE:
    # אל תדפיס סיסמאות/טוקנים ללוג
    # נוודא שה-logger מוגדר פעם אחת בלבד
    _root_logger = logging.getLogger()
    if not _root_logger.handlers:
        _root_logger.setLevel(LOG_LEVEL)
        fmt = logging.Formatter(LOG_FORMAT)

        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setLevel(LOG_LEVEL)
        fh.setFormatter(fmt)
        _root_logger.addHandler(fh)

        eh = logging.FileHandler(ERROR_LOG_FILE, encoding="utf-8")
        eh.setLevel(logging.ERROR)
        eh.setFormatter(fmt)
        _root_logger.addHandler(eh)
else:
    # לוג למסך (stdout)
    logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)

# הדפסה חד-פעמית של נתיב ה-DB לשקיפות (ללא הדפסת טוקן)
logging.info(f"DB_PATH in use: {DB_PATH.resolve()}")
logging.info(f"Data dir: {DATA_DIR.resolve()} | Backups dir: {BACKUPS_DIR.resolve()}")
