"""Working days: weekdays other than the usual company holidays.

The holidays are the observed dates of New Year's Day, Memorial Day,
Independence Day, Labor Day, Thanksgiving and the day after, and Christmas
Day, 1999 to 2002. Enron's own holiday calendar is not in the corpus; this
is the common US company set.
"""

from __future__ import annotations

from datetime import date

import numpy as np

HOLIDAYS = [
    "1999-01-01", "1999-05-31", "1999-07-05", "1999-09-06", "1999-11-25", "1999-11-26", "1999-12-24", "1999-12-31",
    "2000-05-29", "2000-07-04", "2000-09-04", "2000-11-23", "2000-11-24", "2000-12-25",
    "2001-01-01", "2001-05-28", "2001-07-04", "2001-09-03", "2001-11-22", "2001-11-23", "2001-12-25",
    "2002-01-01", "2002-05-27", "2002-07-04", "2002-09-02", "2002-11-28", "2002-11-29", "2002-12-25",
]
_CALENDAR = np.busdaycalendar(holidays=HOLIDAYS)


def working_days(start: date, back: date) -> list[date]:
    """Working days in [start, back)."""
    days = np.arange(np.datetime64(start, "D"), np.datetime64(back, "D"))
    return [d.astype(object) for d in days[np.is_busday(days, busdaycal=_CALENDAR)]]


def working_days_apart(a: date, b: date) -> int:
    """How many working days lie between two working days (0 when they are the same day)."""
    first, last = sorted((a, b))
    return int(np.busday_count(np.datetime64(first, "D"), np.datetime64(last, "D"), busdaycal=_CALENDAR))
