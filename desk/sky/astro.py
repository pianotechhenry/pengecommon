"""Sun and Moon for Penge Common, via PyEphem.

Conventions (stated in every output):

* Place: 51.415 N, 0.060 W, sea-level horizon (no allowance for hills or
  buildings; the Common's ~60 m elevation changes rise and set by well under a
  minute).
* Sunrise and sunset: upper limb on the horizon, with standard refraction of
  34' (PyEphem with pressure = 0 and horizon = -0:34, the USNO convention).
  Reported in local apparent time (sundial time): the Sun's local hour angle
  plus 12 h, computed directly from apparent sidereal time and the Sun's
  apparent right ascension, so the equation of time is built in.
* Civil twilight ends when the Sun's centre is 6 deg below the horizon.
  Reported, like moonrise and moonset, in local mean time: UT plus the
  longitude (0.060 W = -14.4 s).
* Moonrise and moonset: upper limb, same refraction, topocentric.
* Delta T is PyEphem's own (libastro deltat.c): Morrison & Stephenson (2004)
  century values, linearly interpolated, before 1700 (about 129 s in 1589);
  the Astronomical Almanac's annual tabulation from 1700 (9-17 s in the
  eighteenth century).  The value used is printed with every result.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import ephem

from desk.sky.calendar import Day

LAT = 51.415
LON = -0.060
LMT_OFFSET_H = LON / 15.0          # hours to add to UT for local mean time
EPHEM_EPOCH_JD = 2415020.0         # ephem.Date(0) = 1899 Dec 31 12:00 UT


def to_ephem(jd_ut: float) -> ephem.Date:
    return ephem.Date(jd_ut - EPHEM_EPOCH_JD)


def from_ephem(d) -> float:
    return float(d) + EPHEM_EPOCH_JD


def observer(jd_ut: float, horizon: str = "-0:34") -> ephem.Observer:
    o = ephem.Observer()
    o.lat = str(LAT)
    o.lon = str(LON)
    o.elevation = 0
    o.pressure = 0          # refraction handled by the horizon setting
    o.horizon = horizon
    o.date = to_ephem(jd_ut)
    return o


def lmt_hours(jd_ut: float, day: Day) -> float:
    """Local mean time of an instant, as hours from the civil midnight of `day`."""
    return (jd_ut - day.jdn) * 24.0 + LMT_OFFSET_H


def lat_hours(jd_ut: float, day: Day) -> float:
    """Local apparent (sundial) time of an instant, hours from local midnight."""
    o = observer(jd_ut)
    sun = ephem.Sun()
    sun.compute(o)
    ha = (float(o.sidereal_time()) - float(sun.ra)) % (2 * math.pi)
    t = (math.degrees(ha) / 15.0 + 12.0) % 24.0
    # keep the value on the same civil day as the event
    mean = lmt_hours(jd_ut, day)
    while t - mean > 12:
        t -= 24
    while mean - t > 12:
        t += 24
    return t


def hm(hours: float | None) -> str:
    if hours is None:
        return "-"
    total = int(math.floor(hours * 60 + 0.5))
    h, m = divmod(total, 60)
    return f"{h % 24:02d}:{m:02d}"


def period_hm(hours: float | None) -> str:
    """'7.45' twelve-hour style, as the Prayer Book kalendars print it."""
    if hours is None:
        return "-"
    total = int(math.floor(hours * 60 + 0.5))
    h, m = divmod(total, 60)
    h12 = h % 12 or 12
    return f"{h12}.{m:02d}"


@dataclass
class SunDay:
    sunrise_lat: float | None
    sunset_lat: float | None
    sunrise_lmt: float | None
    sunset_lmt: float | None
    noon_lmt: float
    civil_dawn_lmt: float | None
    civil_dusk_lmt: float | None
    delta_t_s: float


@dataclass
class MoonDay:
    phase_name: str
    illumination: float      # 0..1 at local midnight-to-midnight midpoint (noon LMT)
    age_days: float
    rise_lmt: float | None
    set_lmt: float | None
    events: list             # [(name, lmt hours)] principal phases on this day


def _event(fn, o, body, **kw):
    try:
        return from_ephem(fn(body, **kw))
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        return None


def sun_day(day: Day) -> SunDay:
    start = day.jdn - LMT_OFFSET_H / 24.0     # local midnight, in UT
    o = observer(start)
    sun = ephem.Sun()
    rise = _event(o.next_rising, o, sun)
    o.date = to_ephem(start)
    sett = _event(o.next_setting, o, sun)
    o2 = observer(start, horizon="-6")
    dawn = _event(o2.next_rising, o2, ephem.Sun(), use_center=True)
    o2.date = to_ephem(start)
    dusk = _event(o2.next_setting, o2, ephem.Sun(), use_center=True)
    o3 = observer(start)
    transit = from_ephem(o3.next_transit(ephem.Sun()))
    end = start + 1.0
    def within(x):
        return x if x is not None and start <= x < end else None
    rise, sett, dawn, dusk = within(rise), within(sett), within(dawn), within(dusk)
    return SunDay(
        sunrise_lat=lat_hours(rise, day) if rise else None,
        sunset_lat=lat_hours(sett, day) if sett else None,
        sunrise_lmt=lmt_hours(rise, day) if rise else None,
        sunset_lmt=lmt_hours(sett, day) if sett else None,
        noon_lmt=lmt_hours(transit, day),
        civil_dawn_lmt=lmt_hours(dawn, day) if dawn else None,
        civil_dusk_lmt=lmt_hours(dusk, day) if dusk else None,
        delta_t_s=float(ephem.delta_t(to_ephem(start + 0.5))),
    )


PHASE_FNS = [
    ("new moon", ephem.next_new_moon),
    ("first quarter", ephem.next_first_quarter_moon),
    ("full moon", ephem.next_full_moon),
    ("last quarter", ephem.next_last_quarter_moon),
]


def phase_events(jd_from: float, jd_to: float) -> list[tuple[str, float]]:
    """Principal lunar phases between two instants (UT JDs)."""
    out = []
    for name, fn in PHASE_FNS:
        t = jd_from
        while True:
            e = from_ephem(fn(to_ephem(t)))
            if e >= jd_to:
                break
            out.append((name, e))
            t = e + 0.5
    out.sort(key=lambda x: x[1])
    return out


def moon_day(day: Day) -> MoonDay:
    start = day.jdn - LMT_OFFSET_H / 24.0
    end = start + 1.0
    o = observer(start)
    moon = ephem.Moon()
    rise = _event(o.next_rising, o, moon)
    o.date = to_ephem(start)
    sett = _event(o.next_setting, o, moon)
    rise = rise if rise is not None and rise < end else None
    sett = sett if sett is not None and sett < end else None
    noon = start + 0.5
    moon.compute(to_ephem(noon))
    illum = float(moon.moon_phase)
    prev_new = from_ephem(ephem.previous_new_moon(to_ephem(noon)))
    age = noon - prev_new
    sun = ephem.Sun(to_ephem(noon))
    elong = (float(ephem.Ecliptic(moon).lon) - float(ephem.Ecliptic(sun).lon)) % (2 * math.pi)
    waxing = elong < math.pi
    events = [(n, lmt_hours(t, day)) for n, t in phase_events(start, end)]
    if events:
        name = events[0][0]
    elif illum < 0.03:
        name = "new (dark)"
    elif illum > 0.97:
        name = "full"
    elif waxing:
        name = "waxing crescent" if illum < 0.5 else "waxing gibbous"
    else:
        name = "waning gibbous" if illum > 0.5 else "waning crescent"
    return MoonDay(
        phase_name=name,
        illumination=illum,
        age_days=age,
        rise_lmt=lmt_hours(rise, day) if rise else None,
        set_lmt=lmt_hours(sett, day) if sett else None,
        events=events,
    )
