import pandas as pd

from enron_functional.windows import control_windows, count_between, year_end_days

T = pd.Timestamp


def test_control_windows_keep_length_and_weekday_and_skip_absences_and_holidays():
    start, back = T("2001-06-13"), T("2001-06-18")                  # Wednesday to Monday
    own = [(start, back), (T("2001-05-22"), T("2001-05-25"))]       # another absence, 3 weeks before
    windows = control_windows(start, back, own)
    assert [w[0] for w in windows] == ["c2", "c5", "c6"]
    for _, s, b in windows:
        assert s.weekday() == start.weekday() and (b - s) == (back - start)
    # two weeks before Tuesday 2000-07-18 is Independence Day
    assert [w[0] for w in control_windows(T("2000-07-18"), T("2000-07-19"), [])] == ["c3", "c5", "c6"]


def test_year_end_days():
    assert year_end_days(T("2000-12-22"), T("2000-12-27"))
    assert year_end_days(T("2001-01-01"), T("2001-01-02"))
    assert not year_end_days(T("2001-01-02"), T("2001-01-05"))


def test_count_between_is_half_open():
    dates = pd.to_datetime(["2001-01-01", "2001-01-05", "2001-01-10"]).values
    assert count_between(dates, T("2001-01-01"), T("2001-01-10")) == 2
    assert count_between(None, T("2001-01-01"), T("2001-01-10")) == 0
