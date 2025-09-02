tustus_2.7.4a clean full

חשוב:
- לא נגעתי ב-config.py. הוא זהה למה שנתת. לכן גרסת SCRIPT_VERSION בלוג עשויה להציג V2.5.10a – זה מכוון לפי בקשתך.
- אל תדרוס flights.db שלך. החבילה לא כוללת DB כדי לשמור היסטוריה.
- כדי להריץ:
  ./botctl.sh setup
  ./botctl.sh start
  tail -f bot.log

הקוד כבר מחבר את ה-DB להנדלרים וה-JobQueue.
