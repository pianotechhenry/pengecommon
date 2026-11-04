"""Sky regression tests.  Henry's figures (acceptance test 3) are checked
here to within 3 minutes so the suite guards against regressions; the exact
differences, and which side to believe, are in reports/acceptance/sky.md."""
from __future__ import annotations

import pytest

from desk.sky import calendar as C
from desk.sky.astro import phase_events, sun_day

# (year, month, day, sundial sunset h.mm, civil twilight end h.mm) - Old Style
H1689 = [((5, 1), 7.45, 8.20), ((5, 9), 7.57, 8.33), ((5, 25), 8.14, 8.56), ((6, 24), 8.16, 9.04),
         ((7, 15), 7.53, 8.39), ((8, 1), 7.26, 8.06), ((9, 29), 5.33, 5.51)]


def mins(hdotmm: float, pm: bool) -> float:
    h = int(hdotmm)
    m = round((hdotmm - h) * 100)
    return (h + (12 if pm else 0)) * 60 + m


@pytest.mark.parametrize("md,sunset,dusk", H1689)
def test_1689_sunset_and_twilight(md, sunset, dusk):
    s = sun_day(C.day_os(1689, *md))
    assert abs(s.sunset_lat * 60 - mins(sunset, True)) <= 3
    assert abs(s.civil_dusk_lmt * 60 - mins(dusk, True)) <= 3


def test_1589_rise_set():
    for (m, d), rise, sset in (((4, 1), 5.10, 6.50), ((5, 1), 4.16, 7.44)):
        s = sun_day(C.day_os(1589, m, d))
        assert abs(s.sunrise_lat * 60 - mins(rise, False)) <= 3
        assert abs(s.sunset_lat * 60 - mins(sset, True)) <= 3


def test_1589_moons_and_easter():
    start, end = C.day_os(1589, 3, 25), C.day_os(1589, 5, 31)
    got = [(n, C.from_jd(t - 0.004 / 24, C.JULIAN)[:2] + (int(C.from_jd(t, C.JULIAN)[2]),))
           for n, t in phase_events(start.jdn, end.jdn) if n in ("new moon", "full moon")]
    assert [(n, m, d) for n, (_, m, d) in got] == [
        ("new moon", 4, 4), ("full moon", 4, 20), ("new moon", 5, 4), ("full moon", 5, 19)]
    assert C.fmt(C.easter(1589)[0].os) == "30 March 1589"
    assert C.fmt(C.easter(1689)[0].os) == "31 March 1689"
