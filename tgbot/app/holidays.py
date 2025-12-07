# holidays.py
from datetime import date

# список праздничных дат (YYYY-MM-DD)
HOLIDAYS = {
    "2025-12-31","2026-01-01","2026-01-02","2026-01-03","2026-01-04",
    "2026-01-05","2026-01-06","2026-01-07","2026-01-08","2026-01-09",
    "2026-02-23","2026-03-08","2026-03-09","2026-05-01","2026-05-09",
    "2026-05-11","2026-06-12","2026-06-13","2026-06-14","2026-11-04",
    "2026-12-31"
}

def is_non_working(d: date) -> bool:
    # weekend
    if d.weekday() >= 5:
        return True
    # specific holidays
    return d.isoformat() in HOLIDAYS
