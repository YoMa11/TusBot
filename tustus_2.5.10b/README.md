# Tustus 2.5.10b

- תפריט בית במסך אחד (Option 1) עם כפתורים: כל הטיסות, מחירים, יעדים, התראות, הגדרות, עוד…, ורענון.
- JobQueue מריץ `run_monitor` → `monitor_job(conn, app)` כל {config.INTERVAL} שניות (ברירת־מחדל 60).
- אימות שייבוא המודולים מתבצע מהתיקייה הנוכחית בלבד (העדפת גרסת הריצה).
- `flights.db` תמיד נשאר בתיקייה (לא נמחק).
- `botctl.sh` מכסה setup/start/stop/restart/status/atop/doctor ומגדיר PERMS 777 על התיקייה.
