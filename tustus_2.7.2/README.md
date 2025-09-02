# tustus 2.7.2

## הפעלה מהירה
```sh
./botctl.sh setup
./botctl.sh start
./botctl.sh logs
```

ערוך את `config.py` ושם את ה־`BOT_TOKEN` שלך. הקוד **לא משנה** את הקובץ הזה לעולם.

## מה בפנים
- `app.py` — נקודת כניסה, JobQueue ל-`run_monitor`.
- `handlers.py` — `/start`, תפריט DB, ו-`safe_edit` למניעת BadRequest.
- `telegram_view.py` — בניית מקלדת מלאה מתוך ה-DB.
- `db.py` + `schema.sql` — חיבור וסכמה.
- `logic.py` — `run_monitor`/`monitor_job` אסינכרוני.
- `utils.py` — לוגים וחריגים.
- `botctl.sh` — סקריפט שליטה.
- `requirements.txt`, `VERSION`, `README.md`.
```

