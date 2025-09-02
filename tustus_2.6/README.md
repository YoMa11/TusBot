# Tustus 2.6

- תפריט ראשי מלא (אופציה 1) כבר במסך ההתחלתי.
- JobQueue יחיד בשם `monitor`.
- monitor_job חתימה: `async def monitor_job(conn, app)`.
- ללא המרות מחירים.
- flights.db נשמר בתיקיה.
- הרשאות 777 לכל הקבצים.

## הפעלה
```bash
./botctl.sh setup
export TELEGRAM_BOT_TOKEN_RUNTIME=XXXXX:YYYY
./botctl.sh start
./botctl.sh status
tail -f bot.log
```
