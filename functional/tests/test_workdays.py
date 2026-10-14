from datetime import date

from enron_functional.workdays import HOLIDAYS, working_days, working_days_apart


def test_holidays_are_weekdays():
    assert all(date.fromisoformat(d).weekday() < 5 for d in HOLIDAYS)


def test_working_days_skip_weekends_and_holidays():
    # Friday Dec 22, 2000 to Tuesday Dec 26: Christmas Monday is a holiday
    assert working_days(date(2000, 12, 22), date(2000, 12, 27)) == [date(2000, 12, 22), date(2000, 12, 26)]
    assert working_days(date(2001, 9, 29), date(2001, 10, 1)) == []


def test_working_days_apart():
    assert working_days_apart(date(2001, 10, 26), date(2001, 10, 29)) == 1   # Friday to Monday
    assert working_days_apart(date(2001, 10, 29), date(2001, 10, 29)) == 0
