"""Acceptance test 3: reproduce Henry's sky figures (Old Style dates).

Writes reports/acceptance/sky.md.  Neither side is adjusted: where the
figures differ by more than the two-minute tolerance the report says which
it believes and why, and shows what convention would reproduce Henry's.
"""
from __future__ import annotations

from pathlib import Path

import ephem

from desk.sky import calendar as C
from desk.sky.astro import LMT_OFFSET_H, from_ephem, lat_hours, observer, phase_events, sun_day

OUT = Path(__file__).resolve().parent.parent / "reports" / "acceptance" / "sky.md"
TOL = 2.0

# (year, month, day, what, Henry's h.mm, pm?)
CASES = [
    (1689, 5, 1, "sunset (sundial)", "7.45", True), (1689, 5, 1, "end of civil twilight (LMT)", "8.20", True),
    (1689, 5, 9, "sunset (sundial)", "7.57", True), (1689, 5, 9, "end of civil twilight (LMT)", "8.33", True),
    (1689, 5, 25, "sunset (sundial)", "8.14", True), (1689, 5, 25, "end of civil twilight (LMT)", "8.56", True),
    (1689, 6, 24, "sunset (sundial)", "8.16", True), (1689, 6, 24, "end of civil twilight (LMT)", "9.04", True),
    (1689, 7, 15, "sunset (sundial)", "7.53", True), (1689, 7, 15, "end of civil twilight (LMT)", "8.39", True),
    (1689, 8, 1, "sunset (sundial)", "7.26", True), (1689, 8, 1, "end of civil twilight (LMT)", "8.06", True),
    (1689, 9, 29, "sunset (sundial)", "5.33", True), (1689, 9, 29, "end of civil twilight (LMT)", "5.51", True),
    (1589, 4, 1, "sunrise (sundial)", "5.10", False), (1589, 4, 1, "sunset (sundial)", "6.50", True),
    (1589, 5, 1, "sunrise (sundial)", "4.16", False), (1589, 5, 1, "sunset (sundial)", "7.44", True),
]


def minutes(s: str, pm: bool) -> float:
    h, m = s.split(".")
    return (int(h) + (12 if pm else 0)) * 60 + int(m)


def hm(mins: float) -> str:
    t = int(round(mins))
    h, m = divmod(t, 60)
    return f"{h % 12 or 12}.{m:02d}"


def mine(y, m, d, what, horizon="-0:34"):
    day = C.day_os(y, m, d)
    if horizon == "-0:34":
        s = sun_day(day)
        return {"sunset (sundial)": s.sunset_lat, "sunrise (sundial)": s.sunrise_lat,
                "end of civil twilight (LMT)": s.civil_dusk_lmt}[what] * 60
    start = day.jdn - LMT_OFFSET_H / 24
    o = observer(start, horizon=horizon)
    fn = o.next_rising if what.startswith("sunrise") else o.next_setting
    return lat_hours(from_ephem(fn(ephem.Sun())), day) * 60


def main() -> None:
    rows, fails = [], 0
    for y, m, d, what, h, pm in CASES:
        hv = minutes(h, pm)
        mv = mine(y, m, d, what)
        diff = mv - hv
        ok = abs(diff) <= TOL
        fails += not ok
        alt = ""
        if "sundial" in what:
            alt = f"{mine(y, m, d, what, '-0:47') - hv:+.1f}"
        rows.append(f"| {d} {C.MONTHS[m - 1]} {y} | {what} | {h} | {hm(mv)} | {diff:+.1f} | "
                    f"{'pass' if ok else '**outside**'} | {alt} |")
    start, end = C.day_os(1589, 3, 25), C.day_os(1589, 5, 31)
    moons = [(n, C.from_jd(t + LMT_OFFSET_H / 24, C.JULIAN)) for n, t in phase_events(start.jdn, end.jdn)
             if n in ("new moon", "full moon")]
    want = [("new moon", 4, 4), ("full moon", 4, 20), ("new moon", 5, 4), ("full moon", 5, 19)]
    moon_rows = []
    for (n, (yy, mm, dd)), (wn, wm, wd) in zip(moons, want):
        h_ = (dd % 1) * 24
        moon_rows.append(f"| {wn} | {wd} {C.MONTHS[wm - 1]} | {int(dd)} {C.MONTHS[mm - 1]} "
                         f"{int(h_):02d}:{int(h_ % 1 * 60):02d} LMT | "
                         f"{'pass' if (n, mm, int(dd)) == (wn, wm, wd) else '**differs**'} |")
    e89, e1689 = C.fmt(C.easter(1589)[0].os), C.fmt(C.easter(1689)[0].os)
    text = f"""# Acceptance test 3: sky figures for Penge (Old Style dates)

Tolerance {TOL:.0f} minutes. Mine: PyEphem {ephem.__version__}; 51.415 N, 0.060 W; sea-level horizon;
upper limb with 34' refraction; sunrise/sunset in local apparent (sundial) time, twilight in
local mean time; Delta T from libastro (Morrison & Stephenson 2004 before 1700: about 129 s in
1589, 21 s in 1689). The last column shows what a horizon of -0 deg 47' (13' lower) would give.

| date | event | Henry | mine | mine - Henry (min) | 2-min test | at -0:47 |
|---|---|---:|---:|---:|---|---:|
""" + "\n".join(rows) + f"""

{len(CASES) - fails} of {len(CASES)} within tolerance.

| moon 1589 | Henry | mine | |
|---|---|---|---|
""" + "\n".join(moon_rows) + f"""

Easter: 1589 Henry 30 March, mine {e89}; 1689 Henry 31 March, mine {e1689} (Julian computus).

## Discrepancies, and which I believe

All seven 1689 sunsets come out 1.4-1.9 minutes earlier than Henry's, inside the tolerance but
always on the same side; the twilight times agree to a minute. Both 1589 sunrises are 2.5-2.7
minutes later than his, outside the tolerance, while the 1589 sunsets are 1.4-1.7 minutes earlier.

Two things account for this. First, Henry's figures behave as if the horizon were about 13'
lower than the standard sea-level horizon (an observer some 55 m up, which is roughly the height
of the Common, would see that much dip): with the horizon at -0 deg 47' every sunset agrees to
within half a minute. Second, Henry's sunrises are exact mirror images of his sunsets about
12.00 (5.10/6.50, 4.16/7.44), whereas in April and May the Sun's declination rises through the
day, so the true morning arc is about a minute shorter than the afternoon one; that leaves his
two sunrises about a minute early even on the lower horizon.

I believe my figures for the stated convention (sea-level horizon, standard refraction), which
is the almanac convention and what the desk prints. For what someone on the Common actually saw,
neither set is exact: the real horizon was hills, trees and buildings, which delay the visible
sunrise and hasten the visible sunset by more than either effect above. I have not changed my
convention to match, and have not adjusted Henry's figures.
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
