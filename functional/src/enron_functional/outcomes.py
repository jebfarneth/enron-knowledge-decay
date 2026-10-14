"""Outcomes of every absence window and control window (PLAN.md, "Outcome"; decisions 1 to 3).

Primary, one row per message: every person-text message an internal person
sent To the window's person from Houston midnight of the window's first day
until 24 hours before midnight of its day back, and whether `links.parquet`
holds a reply to it within 24 hours (any confidence; `answered`). For the
sensitivity runs the same messages also carry `answered_high` (a
high-confidence reply within 24 hours) and, for messages sent at least 48
hours before the day back, `answered_48` (a reply within 48 hours).

Secondary, one row per window:
  stalled           threads the person sent to in the 7 days before the window: the
                    share with no message during the window and one within 14 days
                    after it
  rerouted          the person's contacts (3 or more messages exchanged in the 56 days
                    before the window): the share of their messages during the window
                    addressed to someone they had not emailed in those 56 days
  catch_up          messages the person sent on the first two working days from the
                    day back, over their average per working day in the 56 days
                    before the window

Each window is measured against its own dates, so control windows get the
same treatment as absences.

Writes data/outcome_messages.parquet and data/window_outcomes.parquet.

Usage: uv run python -m enron_functional.outcomes
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from .config import load_config
from .corpus import MAIL_SOURCES, certified_sources, person_mail, replies
from .workdays import working_days

DAY = pd.Timedelta(days=1)
BASELINE = pd.Timedelta(days=56)
EMPTY = pd.DataFrame({"local": pd.Series(dtype="datetime64[ns]"), "sender_person": [], "to_people": [],
                      "cc_people": [], "thread": [], "path": []})
EMPTY_RECEIVED = EMPTY


def slice_days(frame: pd.DataFrame, column: str, begin: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Rows with `column` in [begin, end); `frame` sorted by `column`."""
    values = frame[column].values
    return frame.iloc[np.searchsorted(values, np.datetime64(begin)):np.searchsorted(values, np.datetime64(end))]


def message_outcomes(windows: pd.DataFrame, mail: pd.DataFrame, links: pd.DataFrame) -> pd.DataFrame:
    to_person = mail[["path", "local", "to_people"]].explode("to_people").dropna(subset=["to_people"])
    to_person = to_person.rename(columns={"to_people": "person"}).sort_values("local")
    by_person = {p: g for p, g in to_person.groupby("person")}
    first = links.sort_values("response_seconds").drop_duplicates("parent_path")
    first_any = dict(zip(first["parent_path"], first["response_seconds"]))
    high = links[links["link_confidence"] == "high"].sort_values("response_seconds").drop_duplicates("parent_path")
    first_high = dict(zip(high["parent_path"], high["response_seconds"]))
    rows = []
    for w in windows.itertuples(index=False):
        received = by_person.get(w.person)
        if received is None:
            continue
        inside = slice_days(received, "local", w.start, w.back - DAY)
        for path, local in zip(inside["path"], inside["local"]):
            seconds, seconds_high = first_any.get(path), first_high.get(path)
            rows.append({"absence_id": w.absence_id, "window": w.window, "person": w.person, "path": path,
                         "local": local,
                         "answered": seconds is not None and seconds <= 86400,
                         "answered_high": seconds_high is not None and seconds_high <= 86400,
                         "eligible_48": local <= w.back - 2 * DAY,
                         "answered_48": seconds is not None and seconds <= 2 * 86400})
    return pd.DataFrame(rows)


def stalled_share(person: str, start: pd.Timestamp, back: pd.Timestamp, sent: pd.DataFrame,
                  thread_days: dict[str, np.ndarray]) -> tuple[float, int]:
    threads = set(slice_days(sent, "local", start - 7 * DAY, start)["thread"].dropna())
    if not threads:
        return float("nan"), 0
    stalled = 0
    for thread in threads:
        days = thread_days[thread]
        during = ((days >= np.datetime64(start)) & (days < np.datetime64(back))).any()
        after = ((days >= np.datetime64(back)) & (days < np.datetime64(back + 14 * DAY))).any()
        stalled += (not during) and after
    return stalled / len(threads), len(threads)


def rerouted_share(person: str, start: pd.Timestamp, back: pd.Timestamp, sent_by: dict[str, pd.DataFrame],
                   received_by: dict[str, pd.DataFrame]) -> tuple[float, int]:
    """Share of the person's contacts' messages during the window that go to someone new to them."""
    exchanged: dict[str, int] = defaultdict(int)
    for to, cc in zip(*slice_days(sent_by.get(person, EMPTY), "local", start - BASELINE, start)[["to_people", "cc_people"]].values.T):
        for r in set(to) | set(cc):
            exchanged[r] += 1
    for sender in slice_days(received_by.get(person, EMPTY_RECEIVED), "local", start - BASELINE, start)["sender_person"]:
        exchanged[sender] += 1
    new, total = 0, 0
    for contact in sorted(c for c, n in exchanged.items() if n >= 3):
        mail = sent_by.get(contact, EMPTY)
        emailed = set()
        for to, cc in zip(*slice_days(mail, "local", start - BASELINE, start)[["to_people", "cc_people"]].values.T):
            emailed |= set(to) | set(cc)
        for to, cc in zip(*slice_days(mail, "local", start, back)[["to_people", "cc_people"]].values.T):
            total += 1
            new += bool((set(to) | set(cc)) - emailed)
    return (new / total if total else float("nan")), total


def catch_up(person: str, start: pd.Timestamp, back: pd.Timestamp, sent: pd.DataFrame) -> float:
    baseline_days = len(working_days((start - BASELINE).date(), start.date()))
    average = len(slice_days(sent, "local", start - BASELINE, start)) / baseline_days if baseline_days else 0
    if average == 0:
        return float("nan")
    first_two = working_days(back.date(), (back + 10 * DAY).date())[:2]
    if len(first_two) < 2:
        return float("nan")
    after = slice_days(sent, "local", pd.Timestamp(first_two[0]), pd.Timestamp(first_two[1]) + DAY)
    return len(after) / (2 * average)


def window_outcomes(windows: pd.DataFrame, mail: pd.DataFrame, threads: pd.Series) -> pd.DataFrame:
    mail = mail.assign(thread=mail["path"].map(threads)).sort_values("local").reset_index(drop=True)
    sent_by = {p: g for p, g in mail.groupby("sender_person")}
    received = mail[["local", "sender_person", "to_people", "cc_people"]].assign(
        recipient=[list(t) + list(c) for t, c in zip(mail["to_people"], mail["cc_people"])]).explode("recipient")
    received_by = {p: g for p, g in received.dropna(subset=["recipient"]).groupby("recipient")}
    thread_days = {t: np.sort(g["local"].values) for t, g in mail.dropna(subset=["thread"]).groupby("thread")}
    rows = []
    for w in windows.itertuples(index=False):
        sent = sent_by.get(w.person, EMPTY)
        stalled, n_threads = stalled_share(w.person, w.start, w.back, sent, thread_days)
        rerouted, n_contact_messages = rerouted_share(w.person, w.start, w.back, sent_by, received_by)
        rows.append({"absence_id": w.absence_id, "window": w.window, "person": w.person,
                     "stalled": stalled, "threads": n_threads, "rerouted": rerouted,
                     "contact_messages": n_contact_messages, "catch_up": catch_up(w.person, w.start, w.back, sent)})
    return pd.DataFrame(rows)


def main() -> None:
    config = load_config()
    source, data = config["paths"]["source"], config["paths"]["data"]
    certified_sources(source, MAIL_SOURCES)
    windows = pd.read_parquet(data / "windows.parquet")
    windows = windows[windows["baseline_sent"] >= 10].reset_index(drop=True)
    mail = person_mail(source)
    links = replies(source)
    messages = message_outcomes(windows, mail, links)
    messages.to_parquet(data / "outcome_messages.parquet", index=False)
    all_links = pd.read_parquet(source / "links.parquet", columns=["path", "thread"])
    per_window = window_outcomes(windows, mail, all_links.set_index("path")["thread"])
    per_window.to_parquet(data / "window_outcomes.parquet", index=False)
    print(f"{len(messages):,} messages to people in {messages[['absence_id', 'window']].drop_duplicates().shape[0]:,} "
          f"windows; {len(per_window):,} windows with secondary outcomes")


if __name__ == "__main__":
    main()
