"""Dated absences announced in email: who was away, when, and who covered.

A notice is a message whose sender says they are, or will be, away from
work. Two kinds count:

- automatic replies: a subject naming an automatic reply (Outlook's "Out of
  Office AutoReply:", Lotus Notes' "<name> is out of the office."); the
  sender is the absent person whatever the wording;
- announcements: authored text in which the sender says so in the first
  person and the present or future tense ("I will be out of the office ...",
  "I'll be on vacation ...", "I am away from the office ...").

Third-person notices ("John is out until Wednesday") are not used, since the
absent person would have to be resolved from a name, and neither are
forwarded notices (only authored text is read).

The window, [first day away, day back), is read from the sentence that
announces the absence, relative to the local (Houston) date of the message:

- dates: 10/07/2000, 5/7, "May 22", "Nov. 26, 2001", "March 15-17",
  "Friday the 21st", "the 18th", weekdays (the next one on or after the
  message date, in the following week when the sentence says "next week"),
  "today", "tomorrow", "this week" and "next week";
- a week that is the first date of the sentence ("on vacation next week")
  is the absence, and days inside it name events during it ("... and will
  miss the December 18th meeting"); a week joined to days by "and" ("out
  tomorrow and next week") is part of it; any other week only places the
  days before it ("Thursday and Friday of this week");
- "until", "return", "back" and "upon my return" mark the day back;
  "through", "thru", "to", "and including" and dashes mark the last day away;
  "from", "starting" and "beginning" mark the first; dates after "after",
  "before" or "by" are not used; any other date is a day away;
- without a first day, the absence starts on the message's date; when the
  sentence gives no day back, or gives a last day, a day back stated in the
  next two sentences ("I'll be back in the office on Monday") is used if it
  falls within three days after the last day;
- a clause that starts a new action ("..., so the next report will be
  Monday", "... and will get my seat next week") is not read;
- a date next to "morning", "afternoon" or a clock time, a clock-time range,
  and "until late this afternoon" are parts of a day and are not used.

A month and day without a year take the year that puts them nearest the
message. Windows must be at least a day long, at most `max_length_days`, and
start between `max_days_before_notice` before and `max_days_after_notice`
after the notice. Notices from one person whose windows overlap or are at
most `merge_gap_days` apart are merged into one absence.

Backups are people a notice names as covering: "please contact Monica
Reasoner", "in my absence, Randy Janzen will ...", "Sara Carrizal will be
assigned to my desk", "my assistant, Patti Thompson". A name counts only when
it matches a person key of the main pipeline exactly (first and last name,
middle initials dropped) and is not the absent person.

Writes data/absence_notices.parquet and data/absences.parquet (they keep the
announcing sentence, for labelling) and results/absences.json (counts, no
message text).

Usage: uv run python -m enron_functional.absences
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd

from .config import load_config
from .corpus import certified_sources, messages_with_people

SOURCES = ("processed/messages.parquet", "processed/sender_people.parquet", "processed/identities.parquet")
LOCAL_TIME = "America/Chicago"

AUTO_SUBJECT = re.compile(r"auto ?-?reply|automatic reply|\bis out of the office\b", re.IGNORECASE)
_AUX = (r"\bi(?:['’]ll|['’]m| will| am| plan to| plan on being| shall| expect to| have to| need to| would)"
        r"(?:\s+(?:also|still|now|currently|again|probably|likely|actually|then))?")
_STATE = (r"(?:\s+be)?\s+(?:out\b(?!\s+of\s+(?!(?:the\s+|my\s+)?(?:office|town|pocket|country|state)))"
          r"(?!\s+(?:there|here|to|that way|this way|west|east)\b)|away\b|gone\b|on\s+(?:vacation|holiday|leave|comp\b|jury duty|maternity|paternity"
          r"|medical|a vacation)|not\s+be\s+in\b|taking\s+(?:a\s+)?(?:vacation|day off|days off|(?:the\s+)?(?:day|week)\s+off)"
          r"|in\s+\w+\s+on\s+vacation)")
ANNOUNCEMENT = re.compile(_AUX + _STATE, re.IGNORECASE)
# Any sentence of an automatic reply that talks about being away or coming back.
AUTO_CUE = re.compile(r"out of (?:the |my )?office|away from|vacation|holiday|\bleave\b|travel|\breturn|\bback\b"
                      r"|\bout\b|\buntil\b|\bthrough\b", re.IGNORECASE)
BOUNDARY = re.compile(r"([.!?]+[)\"']*|:\))\s+(?=[A-Za-z(])")
ABBREVIATIONS = {"jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec", "mon", "tue",
                 "tues", "wed", "thu", "thur", "thurs", "fri", "sat", "sun", "mr", "mrs", "ms", "dr", "st", "no", "vs",
                 "etc", "inc", "co", "corp", "jr", "sr", "ext", "approx", "a.m", "p.m", "e.g", "i.e"}

MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10,
          "nov": 11, "dec": 12}
WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
FULL_WEEKDAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
MONTH_DAY_START = re.compile(r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d", re.IGNORECASE)
_MONTH = (r"(?P<month>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?"
          r"|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)(?:\.\s*|\s*)")
_MONTH_AFTER = (r"(?P<dmm>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?"
                r"|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b\.?")
_WEEKDAY = (r"(?P<wd>monday|mon\b\.?|tuesday|tues?\b\.?|wednesday|weds?\b\.?|thursday|thurs?\b\.?|thu\b\.?"
            r"|friday|fri\b\.?|saturday|sunday)")
_ORD = r"(?:st|nd|rd|th)?"
DATE = re.compile(
    r"\b(?:"
    # March 15-17, Dec. 22 - 31
    rf"(?P<r>{_MONTH}(?P<rd1>\d{{1,2}}){_ORD}\s*(?:-|–)\s*(?P<rd2>\d{{1,2}}){_ORD}(?![\d/])(?:,?\s*(?P<ry>\d{{4}}))?)"
    # (Monday,) May 22(, 2001)
    rf"|(?P<md>(?:{_WEEKDAY.replace('wd', 'mdw')}[,.]?\s+)?{_MONTH.replace('month', 'mdm')}(?P<mdd>\d{{1,2}}){_ORD}\b"
    # "July 5, 6 and 9", "Dec. 7 & 8"
    r"(?:(?:\s*,\s*\d{1,2}(?:st|nd|rd|th)?(?![\d/:]))*\s*,?\s*(?:&|and)\s*(?P<mdd2>\d{1,2})(?:st|nd|rd|th)?"
    r"(?![\d/:]))?(?:[,.]?\s*(?P<mdy>\d{4}))?)"
    # (Thursday,) (the) 20(th) (of) December(, 2001)
    rf"|(?P<dm>(?:{_WEEKDAY.replace('wd', 'dmw')},?\s+)?(?:the\s+)?(?P<dmd>\d{{1,2}}){_ORD}\s+(?:of\s+)?{_MONTH_AFTER}"
    r"(?:,?\s*(?P<dmy>\d{4}))?)"
    # (Monday,) 8/7(/2000)
    rf"|(?P<num>(?:{_WEEKDAY.replace('wd', 'nw')},?\s*)?(?P<nm>\d{{1,2}})/(?P<nd>\d{{1,2}})(?:/(?P<ny>\d{{2,4}}))?(?![\d/]))"
    # Friday the 21st
    rf"|(?P<wn>{_WEEKDAY.replace('wd', 'wnw')},?\s+(?:the\s+)?(?P<wnd>\d{{1,2}})(?:st|nd|rd|th)\b)"
    r"|(?P<ord>the\s+(?P<ordd>\d{1,2})(?:st|nd|rd|th)\b)"
    r"|(?P<week>(?:this|next)\s+week\b)"
    r"|(?P<rel>today|tomorrow)"
    rf"|(?P<w>(?:(?P<next>next|this|coming)\s+)?{_WEEKDAY})"
    r")",
    re.IGNORECASE,
)
RETURN = re.compile(r"\b(?:until|till|til|untill|retur\w*|back|upon my return)"
                    r"(?:\s+(?:to the office|in the office|to work|in|on|by|at|to|the office))*\s*\(?\s*$", re.IGNORECASE)
THROUGH = re.compile(r"(?:\b(?:through|thru|to|and including)|-|–)\s*\(?\s*$", re.IGNORECASE)
START = re.compile(r"\b(?:from|starting|beginning|begin(?:s|ning)?|as of|effective|leaving|leave)\s*(?:on\s+)?\(?\s*$",
                   re.IGNORECASE)
TIME_RANGE = re.compile(r"(?:\d{1,2}:\d\d|\b\d{1,2}\s*[ap]\.?m\b)\s*(?:-|–|until|till|to)\s*\d{1,2}"
                        r"|\b\d{1,2}(?::\d\d)?\s*(?:-|–|until|till|to)\s*(?:\d{1,2}:\d\d|\d{1,2}\s*[ap]\.?m\b)",
                        re.IGNORECASE)
PART_BEFORE = re.compile(r"(?:morning|afternoon|evening|half[- ]day)(?:\s+(?:of|on))?\s*$", re.IGNORECASE)
PART_TODAY = re.compile(r"\b(?:this|tomorrow|today'?s?)\s+(?:morning|afternoon|evening)\b"
                        r"|\b(?:remainder|rest)\s+of\s+(?:the\s+day|today)\b", re.IGNORECASE)
MAX_LEAD_CHARS = 50
CLAUSE_END = re.compile(r",\s*so\b(?!\s+that)|;\s|\b(?:but|and)\s+(?:i\s*)?(?:will|['’]ll|can|want|wanted|need|have|hope"
                        r"|would|should|must)\s+"
                        r"(?!(?:be\s+)?(?:back|return\w*|in\s+(?:the\s+office|on|again)|out|away"
                        r"|on\s+(?:vacation|leave|holiday)|off|gone)\b|not\s+(?:be\s+)?(?:back|return|in)\b)",
                        re.IGNORECASE)
PART_HEDGE = re.compile(r"\buntil\s+(?:late\s+|later\s+)?(?:this\s+(?:afternoon|evening|morning)|today|tonight|noon"
                        r"|lunch)\b", re.IGNORECASE)
WEEK_JOINED = re.compile(r"(?:\band\b|\bplus\b|&)\s+(?:(?:all|most|parts?|the\s+rest|the\s+remainder)\s+of\s+|all\s+)?"
                         r"(?:the\s+)?$", re.IGNORECASE)
FOLLOW_DAYS = 3
SKIP = re.compile(r"\b(?:after|before|by)\s*$", re.IGNORECASE)
PART_DAY = re.compile(r"\s*(?:morning|afternoon|evening|night|a\.?m\b|p\.?m\b|at\s+\d|\d{1,2}(?::\d\d)?\s*[ap]\.?m"
                      r"|(?:until|till)\s+(?:about\s+|around\s+)?(?:\d{1,2}(?::\d\d)?\s*(?:[ap]\.?m\b|o'?clock)"
                      r"|\d{3,4}\b|noon))", re.IGNORECASE)

_NAME = r"([A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][A-Za-z'\-]*[a-z][A-Za-z'\-]*){1,2})"
BACKUP = [
    re.compile(r"\b(?i:contact|call|see|e-?mail|page|reach|ask|direct\s+(?:all\s+|any\s+|your\s+)?(?:questions|inquiries"
               r"|requests|calls|issues)\s+to|forward\s+\w+(?:\s+\w+)?\s+to)\s+(?:either\s+)?" + _NAME),
    re.compile(_NAME + r"\s*(?:\([^)]{0,40}\)\s*)?(?:will|can|is going to|has agreed to)\s+(?:be\s+)?(?:my backup"
               r"|covering|cover|handling|handle"
               r"|assigned to my desk|providing assistance|provide assistance|trading|filling in|fill in|available"
               r"|assist|help|backing me up|back me up|backing up|taking care|take care|responsible|in charge|acting)"),
    re.compile(r"\b(?i:in my absence,?\s+(?:please\s+)?(?:contact\s+|call\s+|see\s+)?)" + _NAME),
    re.compile(r"\b(?i:my assistant,?\s+)" + _NAME),
]
MORE_NAMES = re.compile(r"^(?:\s*\([^)]{0,40}\)|\s+(?:at\s+)?(?:x|ext\.?|extension)?\s*[\d\-.()]{4,})?"
                        r"\s*(?:,\s*or\s+|,\s*|\s+or\s+|\s+and\s+)" + _NAME)


@dataclass
class Window:
    start: date | None = None
    back: date | None = None
    reason: str = ""
    weekday_mismatch: bool = False
    part_day: bool = False
    mentions: list[str] = field(default_factory=list)
    back_stated: bool = False


def nearest_year(month: int, day: int, sent: date) -> date | None:
    """The date with this month and day nearest to `sent` (None if it never exists, like February 30)."""
    best = None
    for year in (sent.year - 1, sent.year, sent.year + 1):
        try:
            candidate = date(year, month, day)
        except ValueError:
            continue
        if best is None or abs((candidate - sent).days) < abs((best - sent).days):
            best = candidate
    return best


def full_year(text: str | None) -> int | None:
    if not text:
        return None
    year = int(text)
    return year + 2000 if year < 50 else year + 1900 if year < 100 else year


def make_date(year: int | None, month: int, day: int, sent: date) -> date | None:
    if year is None:
        return nearest_year(month, day, sent)
    try:
        return date(year, month, day)
    except ValueError:
        return None


def weekday_number(text: str | None) -> int | None:
    return WEEKDAYS.get(text.lower()[:3]) if text else None


def next_weekday(weekday: int, after: date, strictly: bool) -> date:
    days = (weekday - after.weekday()) % 7
    if days == 0 and strictly:
        days = 7
    return after + timedelta(days=days)


def resolve(match: re.Match, sent: date, anchor: date, back_cue: bool) -> tuple[date | None, date | None, bool]:
    """(first day, last day, weekday disagrees with the date) of one date mention."""
    g = match.groupdict()
    if g["r"]:
        month = MONTHS[g["month"].lower()[:3]]
        first = make_date(full_year(g["ry"]), month, int(g["rd1"]), sent)
        last = make_date(first.year if first else None, month, int(g["rd2"]), sent) if first else None
        return first, last, False
    if g["md"] or g["num"] or g["wn"] or g["dm"]:
        if g["dm"]:
            day = make_date(full_year(g["dmy"]), MONTHS[g["dmm"].lower()[:3]], int(g["dmd"]), sent)
            stated = g["dmw"]
        elif g["md"]:
            day, stated = make_date(full_year(g["mdy"]), MONTHS[g["mdm"].lower()[:3]], int(g["mdd"]), sent), g["mdw"]
        elif g["num"]:
            month, number = int(g["nm"]), int(g["nd"])
            day = make_date(full_year(g["ny"]), month, number, sent) if 1 <= month <= 12 else None
            stated = g["nw"]
        else:
            # "Friday the 21st": the nearest month in which that day falls on that weekday.
            weekday, number = weekday_number(g["wnw"]), int(g["wnd"])
            day, stated = None, None
            for offset in (0, 1, -1):
                month_start = (sent.replace(day=1) + timedelta(days=32 * offset)).replace(day=1)
                try:
                    candidate = month_start.replace(day=number)
                except ValueError:
                    continue
                if candidate.weekday() == weekday:
                    day = candidate
                    break
        mismatch = bool(day and stated and weekday_number(stated) != day.weekday())
        last = day
        if g["md"] and g["mdd2"] and day:
            # "Aug 2 & 3": the second day of the same month
            second = make_date(day.year, day.month, int(g["mdd2"]), sent)
            last = second if second and second > day else day
        return day, last, mismatch
    if g["ord"]:
        # "the 18th": that day of this month, or of next month when it has passed
        number = int(g["ordd"])
        for offset in (0, 1):
            month_start = (sent.replace(day=1) + timedelta(days=32 * offset)).replace(day=1)
            try:
                candidate = month_start.replace(day=number)
            except ValueError:
                continue
            if candidate >= sent:
                return candidate, candidate, False
        return None, None, False
    if g["week"]:
        monday = sent - timedelta(days=sent.weekday())
        if g["week"].lower().startswith("next"):
            monday += timedelta(days=7)
        return max(monday, sent), monday + timedelta(days=4), False
    if g["rel"]:
        day = sent if g["rel"].lower() == "today" else sent + timedelta(days=1)
        return day, day, False
    weekday = weekday_number(g["wd"])
    strictly = back_cue or (g["next"] or "").lower() == "next"
    day = next_weekday(weekday, anchor, strictly and anchor == sent)
    return day, day, False


def parse_window(sentence: str, sent: date, follow: str = "") -> Window:
    """The absence window announced in `sentence`, read relative to the message's local date `sent`."""
    window = Window()
    sentence = CLAUSE_END.split(sentence, maxsplit=1)[0]
    # clock times after "back" or "return" are the hours of the day back
    if TIME_RANGE.search(re.split(r"\b(?:back|retur\w*)\b", sentence, maxsplit=1, flags=re.IGNORECASE)[0]) \
            or PART_HEDGE.search(sentence):
        window.part_day = True
        window.reason = "part day"
        return window
    anchor = sent
    if re.search(r"\bnext week\b", sentence, re.IGNORECASE):
        anchor = sent - timedelta(days=sent.weekday()) + timedelta(days=7)
    starts, backs, throughs, days, weeks, part_dates, spans = [], [], [], [], [], set(), set()
    head_week = None
    verb = ANNOUNCEMENT.search(sentence)
    position = 0
    for match in DATE.finditer(sentence):
        before = sentence[max(position, match.start() - 40):match.start()]
        position = match.end()
        if PART_DAY.match(sentence[match.end():]) or PART_BEFORE.search(before):
            window.part_day = True
            part_dates.add(resolve(match, sent, anchor, False)[0])
            continue
        if SKIP.search(before):
            continue
        back_cue = bool(RETURN.search(before))
        # "out Monday and Tuesday": a weekday after another day falls after it
        floor = max([anchor] + starts + backs + throughs + [first if (first, last) in spans else last
                                                            for first, last in days])
        first, last, mismatch = resolve(match, sent, floor, back_cue or floor > anchor)
        if first is None:
            continue
        window.weekday_mismatch |= mismatch
        window.mentions.append(match.group(0))
        if match.group("week"):
            spans.add((first, last))
            if not window.mentions[:-1] and (verb is None or match.start() >= verb.end()):
                head_week = (first, last)
                days.append((first, last))
            elif WEEK_JOINED.search(before):
                days.append((first, last))
            else:
                weeks.append((first, last))
        elif back_cue:
            backs.append(first)
        elif THROUGH.search(before):
            throughs.append(last)
        elif START.search(before):
            starts.append(first)
            if last != first:
                throughs.append(last)
        else:
            days.append((first, last))
    # "Wednesday morning, November 15": the date restates a part day
    days = [(first, last) for first, last in days if first not in part_dates and first not in backs]
    starts = [d for d in starts if d not in part_dates]
    if head_week:
        # "on vacation next week ... the December 18th meeting": events during the absence
        days = [(f, l) for f, l in days if (f, l) == head_week or not head_week[0] <= f <= head_week[1]]
    if not (days or starts or throughs or backs) and weeks:
        days = weeks
    if PART_TODAY.search(sentence) and not (days or starts or throughs):
        window.part_day = True
        window.reason = "part day"
        return window
    named = starts + [first for first, _ in days]
    window.start = min(named) if named else sent
    if backs:
        later = [b for b in backs if b > window.start]
        window.back = min(later) if later else None
        window.back_stated = window.back is not None
    elif throughs:
        window.back = max(throughs) + timedelta(days=1)
    elif days:
        window.back = max(last for _, last in days) + timedelta(days=1)
    week_back = bool(window.back and not (backs or throughs)
                     and any(window.back == last + timedelta(days=1) for _, last in spans))
    if follow and not window.back_stated and (window.back or starts):
        # "... on Friday, September 29. ... I'll be back in the office on Monday."; a week ("this week") is
        # vague, so a day back stated after it may also come before the week's end
        stated = parse_window(follow, sent) if not window.back else stated_back(follow, sent, window.start)
        latest = window.back + timedelta(days=FOLLOW_DAYS) if window.back else None
        if stated and stated.back_stated and stated.back > window.start and (
                window.back is None or (window.back <= stated.back <= latest)
                or (week_back and stated.back <= latest)):
            window.back, window.back_stated = stated.back, True
            window.mentions += stated.mentions
    if not window.mentions:
        window.reason = "part day" if window.part_day else "no date"
    elif window.back is None:
        window.reason = "no day back"
    return window


def stated_back(text: str, sent: date, after: date) -> Window | None:
    """The first day back stated in `text` ("I'll be back on Monday"), weekdays read as the next after `after`."""
    position = 0
    for match in DATE.finditer(text):
        before = text[max(position, match.start() - 40):match.start()]
        position = match.end()
        if RETURN.search(before) and not PART_DAY.match(text[match.end():]):
            first, _, _ = resolve(match, sent, after + timedelta(days=1), False)
            if first:
                return Window(back=first, back_stated=True, mentions=[match.group(0)])
    return None


def split_sentences(text: str | None) -> list[str]:
    """Sentences of `text`; a period after a month, weekday or title abbreviation or an initial ends none."""
    flat = re.sub(r"\s+", " ", text or "").strip()
    sentences, begin = [], 0
    for match in BOUNDARY.finditer(flat):
        word = re.search(r"([A-Za-z.]+)$", flat[begin:match.start()])
        token = word.group(1).lower().rstrip(".") if word else ""
        if match.group(1).startswith(".") and (token in ABBREVIATIONS or len(token) == 1):
            continue
        if match.group(1) == "." and token in FULL_WEEKDAYS and MONTH_DAY_START.match(flat[match.end():]):
            continue
        sentences.append(flat[begin:match.end(1)].strip())
        begin = match.end()
    sentences.append(flat[begin:].strip())
    return [s for s in sentences if s]


def notice_sentence(subject: str, text: str) -> tuple[str, str, str] | None:
    """(kind, announcing sentence, the sentence after it) of a notice, or None when the message is not one."""
    sentences = split_sentences(text)
    if AUTO_SUBJECT.search(subject or ""):
        for i, s in enumerate(sentences):
            if AUTO_CUE.search(s) and DATE.search(s):
                return "auto-reply", s, " ".join(sentences[i + 1:i + 3])
        return ("auto-reply", sentences[0], " ".join(sentences[1:3])) if sentences else None
    for i, s in enumerate(sentences):
        if (match := ANNOUNCEMENT.search(s)):
            return "announcement", announcing_clause(s, match.start()), " ".join(sentences[i + 1:i + 3])
    return None


def announcing_clause(sentence: str, start: int) -> str:
    """The part of an announcement's sentence that dates it.

    Text before "I will be out" counts only when short ("Tuesday I'll be
    out", "Starting today, Wednesday, November 21, I will be out"); a new
    clause after ", so" or a semicolon ("..., so the next report will be
    Monday") does not count.
    """
    clause = sentence if start <= MAX_LEAD_CHARS else sentence[start:]
    return CLAUSE_END.split(clause, maxsplit=1)[0]


def person_name_key(name: str) -> str:
    """'Michael B. Jones' -> 'michael jones' (initials dropped)."""
    tokens = [t for t in re.split(r"\s+", name.strip()) if len(t.rstrip(".")) > 1]
    return f"{tokens[0]} {tokens[-1]}".lower() if len(tokens) >= 2 else ""


def backups(text: str, people: set[str], absent: str | None) -> tuple[list[str], list[str]]:
    """(resolved person keys, every name found) of the people a notice names as covering."""
    names = []
    flat = re.sub(r"\s+", " ", text or "")
    for pattern in BACKUP:
        for match in pattern.finditer(flat):
            names.append(match.group(1))
            rest = flat[match.end():]
            while (more := MORE_NAMES.match(rest)):
                names.append(more.group(1))
                rest = rest[more.end():]
    keys = []
    for name in names:
        key = person_name_key(name)
        if key in people and key != absent and key not in keys:
            keys.append(key)
    return keys, list(dict.fromkeys(names))


def find_notices(messages: pd.DataFrame, people: set[str], settings: dict) -> pd.DataFrame:
    """One row per notice, with its window and whether it is kept (`status` "kept") or why not."""
    rows = []
    local_dates = messages["date"].dt.tz_convert(LOCAL_TIME).dt.date
    for message, sent in zip(messages.itertuples(index=False), local_dates):
        found = notice_sentence(message.subject, message.authored)
        if found is None:
            continue
        kind, sentence, follow = found
        window = parse_window(sentence, sent, follow)
        status = window.reason
        if not status:
            length = (window.back - window.start).days
            if window.weekday_mismatch:
                status = "weekday disagrees with date"
            elif length < 1:
                status = "day back not after first day"
            elif all((window.start + timedelta(days=d)).weekday() >= 5 for d in range(length)):
                status = "weekend only"
            elif length > settings["max_length_days"]:
                status = "too long"
            elif not (-settings["max_days_before_notice"] <= (window.start - sent).days
                      <= settings["max_days_after_notice"]):
                status = "too far from the notice"
            elif pd.isna(message.sender_person) or not message.sender_person:
                status = "sender not a person"
            else:
                status = "kept"
        keys, names = backups(message.authored, people, message.sender_person)
        rows.append({"path": message.path, "date": message.date, "sender": message.sender,
                     "absent": message.sender_person, "kind": kind, "sentence": sentence,
                     "start": window.start if not window.reason else None,
                     "back": window.back if not window.reason else None,
                     "status": status, "weekday_mismatch": window.weekday_mismatch,
                     "backups": keys, "backup_names": names})
    notices = pd.DataFrame(rows)
    for column in ("start", "back"):
        notices[column] = pd.to_datetime(notices[column])
    return notices


def merge_absences(notices: pd.DataFrame, gap_days: int) -> pd.DataFrame:
    """Kept notices from one person whose windows overlap or nearly touch, merged into absences."""
    kept = notices[notices["status"] == "kept"].sort_values(["absent", "start", "back", "path"])
    events = []
    for absent, group in kept.groupby("absent", sort=True):
        current = None
        for notice in group.itertuples(index=False):
            if current and notice.start <= current["back"] + pd.Timedelta(days=gap_days):
                current["back"] = max(current["back"], notice.back)
                current["windows"].add((notice.start, notice.back))
                current["paths"].append(notice.path)
                current["kinds"].add(notice.kind)
                current["backups"] += [b for b in notice.backups if b not in current["backups"]]
                continue
            if current:
                events.append(current)
            current = {"absent": absent, "start": notice.start, "back": notice.back,
                       "windows": {(notice.start, notice.back)}, "paths": [notice.path], "kinds": {notice.kind},
                       "backups": list(notice.backups)}
        events.append(current)
    absences = pd.DataFrame([{
        "absent": e["absent"], "start": e["start"], "back": e["back"], "days": (e["back"] - e["start"]).days,
        "notices": len(e["paths"]), "conflicting": len(e["windows"]) > 1, "kinds": sorted(e["kinds"]),
        "paths": e["paths"], "backups": e["backups"]} for e in events])
    absences.insert(0, "absence_id", range(len(absences)))
    return absences


def summary(notices: pd.DataFrame, absences: pd.DataFrame, settings: dict) -> dict:
    kept = notices[notices["status"] == "kept"]
    lengths = pd.cut(absences["days"], [0, 1, 3, 7, 14, 31], labels=["1", "2-3", "4-7", "8-14", "15-31"])
    return {
        **settings,
        "notices_found": len(notices),
        "notices_by_kind": notices["kind"].value_counts().to_dict(),
        "notices_by_status": notices["status"].value_counts().to_dict(),
        "notices_kept": len(kept),
        "kept_by_kind": kept["kind"].value_counts().to_dict(),
        "kept_with_weekday_mismatch": int(kept["weekday_mismatch"].sum()),
        "absences": len(absences),
        "people": int(absences["absent"].nunique()),
        "absences_by_days": {str(k): int(v) for k, v in lengths.value_counts().sort_index().items()},
        "absences_by_year": {str(k): int(v) for k, v in absences["start"].dt.year.value_counts().sort_index().items()},
        "absences_from_conflicting_notices": int(absences["conflicting"].sum()),
        "absences_with_named_backup": int((absences["backups"].map(len) > 0).sum()),
        "notices_naming_someone": int((notices["backup_names"].map(len) > 0).sum()),
    }


def main() -> None:
    config = load_config()
    source, data, results = (config["paths"][k] for k in ("source", "data", "results"))
    settings = config["absences"]
    certified_sources(source, SOURCES)
    messages = messages_with_people(source)
    identities = pd.read_parquet(source / "identities.parquet", columns=["person_key"])
    people = set(messages["sender_person"].dropna()) | set(identities["person_key"].dropna())
    notices = find_notices(messages, people, settings)
    absences = merge_absences(notices, settings["merge_gap_days"])
    data.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    notices.to_parquet(data / "absence_notices.parquet", index=False)
    absences.to_parquet(data / "absences.parquet", index=False)
    report = summary(notices, absences, settings)
    (results / "absences.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
