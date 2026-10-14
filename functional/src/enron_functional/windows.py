"""Absence windows and their control windows (PLAN.md, "Absences" and "Control windows").

Every detected absence that starts from 2000-01-01 on and covers at least one
working day gets a row for itself ("away") and one for each control window:
the same length and starting weekday, 2, 3, 5 and 6 weeks before
("c2" ... "c6"), kept only when it overlaps none of the person's detected
absences, no company holiday and no day from December 24 to January 1.

Flags let the analysis select the main sample and the sensitivity runs:
  baseline_sent   person-text messages the person sent in the 56 days before
  main_period     starts 2000-01-01 to 2001-11-30 (False: after the filing)
  holiday_week    the absence itself includes a day from December 24 to January 1
  auto_only       every notice of the absence is an automatic reply
  names_backup    some notice of the absence names someone as covering

Writes data/windows.parquet.

Usage: uv run python -m enron_functional.windows
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from .config import load_config
from .corpus import MAIL_SOURCES, certified_sources, person_mail
from .workdays import HOLIDAYS, working_days

CONTROL_WEEKS = (2, 3, 5, 6)
BASELINE_DAYS = 56
FIRST_DAY = pd.Timestamp("2000-01-01")
FILING = pd.Timestamp("2001-12-01")
HOLIDAY_DATES = {pd.Timestamp(d) for d in HOLIDAYS}


def year_end_days(start: pd.Timestamp, back: pd.Timestamp) -> bool:
    """Whether [start, back) contains a day from December 24 to January 1."""
    return any((d.month == 12 and d.day >= 24) or (d.month == 1 and d.day == 1)
               for d in pd.date_range(start, back - pd.Timedelta(days=1)))


def overlaps(start: pd.Timestamp, back: pd.Timestamp, spans: list[tuple[pd.Timestamp, pd.Timestamp]]) -> bool:
    return any(start < b and s < back for s, b in spans)


def control_windows(start: pd.Timestamp, back: pd.Timestamp,
                    absences: list[tuple[pd.Timestamp, pd.Timestamp]]) -> list[tuple[str, pd.Timestamp, pd.Timestamp]]:
    """The usable control windows of one absence, as (name, start, back)."""
    out = []
    for weeks in CONTROL_WEEKS:
        shift = pd.Timedelta(days=7 * weeks)
        s, b = start - shift, back - shift
        days = pd.date_range(s, b - pd.Timedelta(days=1))
        if overlaps(s, b, absences) or any(d in HOLIDAY_DATES for d in days) or year_end_days(s, b):
            continue
        out.append((f"c{weeks}", s, b))
    return out


def sent_before(mail: pd.DataFrame) -> dict[str, np.ndarray]:
    """Sorted local send dates of each person's person-text messages."""
    return {p: np.sort(g["local"].dt.normalize().values) for p, g in mail.groupby("sender_person")}


def count_between(dates: np.ndarray | None, start: pd.Timestamp, end: pd.Timestamp) -> int:
    if dates is None:
        return 0
    return int(np.searchsorted(dates, np.datetime64(end), "left") - np.searchsorted(dates, np.datetime64(start), "left"))


def build(absences: pd.DataFrame, notices: pd.DataFrame, mail: pd.DataFrame) -> pd.DataFrame:
    named = notices.set_index("path")["backup_names"].map(len).gt(0)
    sent = sent_before(mail)
    spans = {p: list(zip(g["start"], g["back"])) for p, g in absences.groupby("absent")}
    rows = []
    for a in absences.itertuples(index=False):
        if a.start < FIRST_DAY or not working_days(a.start.date(), a.back.date()):
            continue
        flags = {"absence_id": a.absence_id, "person": a.absent,
                 "baseline_sent": count_between(sent.get(a.absent), a.start - pd.Timedelta(days=BASELINE_DAYS), a.start),
                 "main_period": a.start < FILING, "holiday_week": year_end_days(a.start, a.back),
                 "auto_only": list(a.kinds) == ["auto-reply"],
                 "names_backup": bool(any(named.get(path, False) for path in a.paths))}
        rows.append({**flags, "window": "away", "start": a.start, "back": a.back})
        for name, s, b in control_windows(a.start, a.back, spans[a.absent]):
            rows.append({**flags, "window": name, "start": s, "back": b})
    return pd.DataFrame(rows)


def main() -> None:
    config = load_config()
    source, data = config["paths"]["source"], config["paths"]["data"]
    certified_sources(source, MAIL_SOURCES)
    absences = pd.read_parquet(data / "absences.parquet")
    notices = pd.read_parquet(data / "absence_notices.parquet", columns=["path", "backup_names"])
    windows = build(absences, notices, person_mail(source))
    windows.to_parquet(data / "windows.parquet", index=False)
    away = windows[windows["window"] == "away"]
    main_sample = away[away["main_period"] & ~away["holiday_week"] & (away["baseline_sent"] >= 20)]
    controls = windows[windows["absence_id"].isin(main_sample["absence_id"]) & (windows["window"] != "away")]
    print(f"{len(away):,} absences from 2000 on; main sample {len(main_sample):,} absences of "
          f"{main_sample['person'].nunique():,} people with {len(controls):,} control windows "
          f"({controls.groupby('absence_id').size().reindex(main_sample['absence_id'], fill_value=0).eq(0).sum()} "
          f"absences with none)")


if __name__ == "__main__":
    main()
