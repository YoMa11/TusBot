# Tustus Bot — v1.0.32

גרסת ZIP שמסתמכת אך ורק על `config.py`:
- `BOT_TOKEN` ו-`URL` נקראים מ־`config.py` בלבד (אין תלות ב-ENV).
- תפריט מלא, שמירה/הסרה, תקציר לפי יעד.
- מקלדת יעדים 5 בשורה, קיצור תוויות, מחיר תמיד ב-₪.
- ניטור: אם אין JobQueue → fallback לולאתי.

## התקנה והרצה
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install python-telegram-bot "python-telegram-bot[job-queue]" requests beautifulsoup4 lxml
python3 app.py
