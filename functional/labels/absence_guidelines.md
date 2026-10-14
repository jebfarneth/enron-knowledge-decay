# Labelling guidelines: absence notices

Written on 2026-10-13, after the detection rules were frozen and before any
item of the check sample was drawn or read.

Each item is one email: the date it was sent (Houston time, with the
weekday), its subject and the text its sender wrote (quoted and forwarded
text removed). You do not see what the detector concluded. Answer from the
email alone, using a calendar for the year the email was sent.

**1. `absent`: does the sender say that they themselves are, or will be,
away from work for at least one full working day?** `yes`, `no` or
`unclear`.
- Away means not at work and not working normally: out of the office, on
  vacation, on leave, sick, out of town for personal or business reasons, at
  an all-day conference or off-site. Saying they can still be reached by
  phone or will check voice mail does not change the answer.
- `no` when the absence is only part of a day (a morning, an afternoon, a
  few hours), only on a weekend or holiday, someone else's, in the past, or
  only possible ("I may be out").
- An automatic out-of-office reply is the sender's own notice even when
  written in the third person ("Ann Lee is out of the office").

**2. `first_day`: the first full working day away** (YYYY-MM-DD). When the
email says the sender is already away ("I am out of the office until …",
most automatic replies) and gives no first day, use the date the email was
sent. `unknown` when it cannot be worked out.

**3. `day_back`: the first day the sender is back** (YYYY-MM-DD), that is,
the day after the last day away, weekends included: "through Friday, March
16" gives Saturday, March 17; "until Monday" and "returning Monday" give that
Monday; "on Thursday" alone gives Friday. `unknown` when it cannot be worked
out.

**4. `note`**: optional, one line, for anything unclear.

When an email announces more than one absence, label the first one it
mentions. Weekdays without a date mean the next such day on or after the
send date, unless the email says otherwise ("next week", or a weekday after
another named day). A month and day without a year take the year that puts
them nearest the send date.

**Scoring.** A notice is correct when `absent` is `yes` and both dates are
within one day of the detector's. The one-day allowance covers "until Monday"
(back that Monday, or away through it) and similar wording; exact agreement
is reported too. Items labelled `unclear` are reported separately.
