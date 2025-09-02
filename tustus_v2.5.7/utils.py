__file_version__ = "tustus_v2.5.7"  # updated 2025-08-30 18:58  # added 2025-08-30 18:21
from datetime import datetime
from html import escape as h

def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")

def safe(val) -> str:
    return h(str(val or "")).replace("\n", " ").strip()

def human_active_delta(first_seen_iso: str) -> str:
    try:
        dt = datetime.fromisoformat(first_seen_iso)
        delta = datetime.now() - dt
        m = int(delta.total_seconds() // 60)
        h_ = m // 60
        m_ = m % 60
        if h_ > 0:
            return f"{h_} ש׳ ו{m_} ד׳"
        return f"{m_} ד׳"
    except Exception:
        return ""

def clamp_int(value, default=None, min_v=None, max_v=None):
    try:
        x = int(value)
        if min_v is not None and x < min_v: x = min_v
        if max_v is not None and x > max_v: x = max_v
        return x
    except Exception:
        return default



# ==== Date helpers ====
from datetime import date, timedelta, datetime

def date_range_from_preset(preset: str) -> tuple[str,str]:
    """Return (start,end) ISO dates for common presets: week, month, weekend, range(not here)."""
    today = date.today()
    if preset == "week":
        start = today
        end = today + timedelta(days=7)
    elif preset == "month":
        # until end of current month
        if today.month == 12:
            end = date(today.year, 12, 31)
        else:
            first_next = date(today.year, today.month+1, 1)
            end = first_next - timedelta(days=1)
        start = today
    elif preset == "weekend":
        # next Fri-Sat (IL style) -> Fri as start, Sun as end (return by Sunday)
        # find next Friday
        days_ahead = (4 - today.weekday()) % 7  # Monday=0 ... Sunday=6 ; Friday=4
        fri = today + timedelta(days=days_ahead)
        sun = fri + timedelta(days=2)  # Sunday
        start, end = fri, sun
    else:
        start = today
        end = today + timedelta(days=120)
    return (start.isoformat(), end.isoformat())

def human_duration_since(iso: str) -> str:
    """Return compact Hebrew 'Xש׳ Yד׳' since the given ISO datetime/date string."""
    if not iso:
        return ""
    try:
        # accept date or datetime
        try:
            dt = datetime.fromisoformat(iso)
        except ValueError:
            dt = datetime.fromisoformat(iso + "T00:00:00")
        delta = datetime.now() - dt
        s = int(delta.total_seconds())
        if s < 0: s = 0
        h, r = divmod(s, 3600)
        m, _ = divmod(r, 60)
        if h >= 24:
            d, h = divmod(h, 24)
            return f"{d}יום {h}ש׳"
        if h > 0:
            return f"{h}ש׳ {m}ד׳"
        return f"{m}ד׳"
    except Exception:
        return ""
