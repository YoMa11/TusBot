# config.py
from __future__ import annotations
import os
import logging

# ===== Core =====
# Put your real token here. (If you prefer env, replace the next line with: os.getenv("BOT_TOKEN","").strip())
BOT_TOKEN = "8355167350:AAFHXoKgOR7Ja0NOncn2_9PY0hp3Kn4tNBo"

# The source page to scrape
URL = "https://www.tustus.co.il/Arkia/Home"

# SQLite path used by the app/logic
DB_PATH = "./flights.db"

# Monitoring interval (seconds)
INTERVAL = 180  # choose 60/180 as you like; the app reads this value

# ===== Logging =====
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_LEVEL = logging.DEBUG
LOG_TO_FILE = True
LOG_DIR = "."
LOG_FILE = os.path.join(LOG_DIR, "bot.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "bot.err.log")

SCRIPT_VERSION = "V2.4.1"

# ===== Scraper (optional tuning) =====
REQUEST_TIMEOUT = 15
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Show “⏱ פעילה” by default
MONITOR_QUIET_ACTIVE_TIME = True
