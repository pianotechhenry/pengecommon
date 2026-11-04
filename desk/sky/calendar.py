"""Calendar arithmetic for England, 1580-1800.

* Old Style (Julian) was the civil calendar until Wednesday 2 September 1752,
  followed by Thursday 14 September 1752 New Style (Gregorian), under the
  Calendar (New Style) Act 1750 (24 Geo. II c. 23).
* The legal year began on 25 March (Lady Day) until 1751; 1752 was the first
  legal year to begin on 1 January.  Dates from 1 January to 24 March are
  therefore double-dated before 1752 ("10 February 1688/9").
* Easter: Julian computus to 1752 (Easter 1752 fell before the change);
  Gregorian computus from 1753, which is what the Act's tables give.

All arithmetic is on Julian Day Numbers (Meeus, *Astronomical Algorithms*,
2nd ed., ch. 7-8).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

JULIAN = "julian"
GREGORIAN = "gregorian"

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
            "Saturday"]


def jd(y: int, m: int, d: float, calendar: str) -> float:
    """Julian Day (at 0h UT when d is a whole day number) for a calendar date."""
    if m <= 2:
        y -= 1
        m += 12
    if calendar == GREGORIAN:
        a = y // 100
        b = 2 - a + a // 4
    else:
        b = 0
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + b - 1524.5


def from_jd(j: float, calendar: str) -> tuple[int, int, float]:
    j += 0.5
    z = math.floor(j)
    f = j - z
    if calendar == GREGORIAN:
        alpha = math.floor((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - alpha // 4
    else:
        a = z
    b = a + 1524
    c = math.floor((b - 122.1) / 365.25)
    d = math.floor(365.25 * c)
    e = math.floor((b - d) / 30.6001)
    day = b - d - math.floor(30.6001 * e) + f
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    return int(year), int(month), day


# England: last Julian day and first Gregorian day of the civil calendar.
SWITCH_LAST_OS = jd(1752, 9, 2, JULIAN)          # Wednesday 2 Sept 1752 OS
SWITCH_FIRST_NS = jd(1752, 9, 14, GREGORIAN)     # Thursday 14 Sept 1752 NS
assert SWITCH_FIRST_NS - SWITCH_LAST_OS == 1


@dataclass(frozen=True)
class Day:
    """One civil day, held as its Julian Day Number at 0h UT."""
    jdn: float

    @property
    def os(self) -> tuple[int, int, int]:
        y, m, d = from_jd(self.jdn, JULIAN)
        return y, m, int(d)

    @property
    def ns(self) -> tuple[int, int, int]:
        y, m, d = from_jd(self.jdn, GREGORIAN)
        return y, m, int(d)

    @property
    def civil_calendar(self) -> str:
        """The calendar in force in England on this day."""
        return JULIAN if self.jdn <= SWITCH_LAST_OS else GREGORIAN

    @property
    def civil(self) -> tuple[int, int, int]:
        return self.os if self.civil_calendar == JULIAN else self.ns

    @property
    def weekday(self) -> str:
        return WEEKDAYS[int(math.floor(self.jdn + 1.5)) % 7]

    @property
    def weekday_index(self) -> int:
        return int(math.floor(self.jdn + 1.5)) % 7

    def __add__(self, n: int) -> "Day":
        return Day(self.jdn + n)

    def __sub__(self, other):
        if isinstance(other, Day):
            return int(round(self.jdn - other.jdn))
        return Day(self.jdn - other)

    def __lt__(self, other: "Day") -> bool:
        return self.jdn < other.jdn

    def __le__(self, other: "Day") -> bool:
        return self.jdn <= other.jdn

    # -- legal year ----------------------------------------------------------
    @property
    def legal_year(self) -> int:
        y, m, d = self.civil
        if y <= 1751 and (m < 3 or (m == 3 and d < 25)):
            return y - 1
        return y

    def legal_label(self) -> str:
        """'10 February 1688/9' style for 1 Jan-24 Mar before 1752."""
        y, m, d = self.civil
        if self.legal_year != y:
            if (y - 1) // 100 != y // 100:
                tail = str(y)
            elif (y - 1) // 10 != y // 10:
                tail = str(y)[-2:]
            else:
                tail = str(y)[-1]
            return f"{d} {MONTHS[m - 1]} {y - 1}/{tail}"
        return f"{d} {MONTHS[m - 1]} {y}"


def day_os(y: int, m: int, d: int) -> Day:
    return Day(jd(y, m, d, JULIAN))


def day_ns(y: int, m: int, d: int) -> Day:
    return Day(jd(y, m, d, GREGORIAN))


def civil_day(y: int, m: int, d: int) -> Day:
    """A date as written in England at the time (OS to 2 Sept 1752, NS after)."""
    j_os = jd(y, m, d, JULIAN)
    if j_os <= SWITCH_LAST_OS:
        return Day(j_os)
    j_ns = jd(y, m, d, GREGORIAN)
    if j_ns >= SWITCH_FIRST_NS:
        return Day(j_ns)
    raise ValueError(
        f"{d} {MONTHS[m - 1]} {y} did not exist in England: 3-13 September 1752 "
        "were omitted when the Gregorian calendar was adopted."
    )


def fmt(t: tuple[int, int, int]) -> str:
    y, m, d = t
    return f"{d} {MONTHS[m - 1]} {y}"


_MONTH_RE = {m.lower()[:3]: i + 1 for i, m in enumerate(MONTHS)}


def parse_date(s: str) -> tuple[int, int, int]:
    """Accept 1589-04-01, 1589/4/1, '1 April 1589', 'April 1 1589'."""
    s = s.strip()
    m = re.fullmatch(r"(\d{3,4})[-/.](\d{1,2})[-/.](\d{1,2})", s)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    m = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\.?,?\s+(\d{3,4})", s)
    if m and m.group(2).lower()[:3] in _MONTH_RE:
        return int(m.group(3)), _MONTH_RE[m.group(2).lower()[:3]], int(m.group(1))
    m = re.fullmatch(r"([A-Za-z]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{3,4})", s)
    if m and m.group(1).lower()[:3] in _MONTH_RE:
        return int(m.group(3)), _MONTH_RE[m.group(1).lower()[:3]], int(m.group(2))
    raise ValueError(f"cannot read the date {s!r}; use YYYY-MM-DD")


# ---------------------------------------------------------------------------
# Easter and the moveable feasts

def easter_julian(y: int) -> tuple[int, int]:
    a, b, c = y % 4, y % 7, y % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    n = d + e + 114
    return n // 31, (n % 31) + 1


def easter_gregorian(y: int) -> tuple[int, int]:
    a = y % 19
    b, c = divmod(y, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    n = h + l_ - 7 * m + 114
    return n // 31, (n % 31) + 1


def easter(y: int) -> tuple[Day, str]:
    """Easter Day of the (January-reckoned) year y, and which computus."""
    if y <= 1752:
        m, d = easter_julian(y)
        return day_os(y, m, d), "Julian computus (Old Style)"
    m, d = easter_gregorian(y)
    return day_ns(y, m, d), "Gregorian computus (Calendar Act 1750 tables)"


# Offsets from Easter Day.  Names as the Prayer Book gives them where it does.
MOVEABLE = [
    (-63, "Septuagesima Sunday"),
    (-56, "Sexagesima Sunday"),
    (-49, "Quinquagesima (Shrove) Sunday"),
    (-47, "Shrove Tuesday"),
    (-46, "Ash Wednesday (first day of Lent)"),
    (-42, "Quadragesima, first Sunday in Lent"),
    (-21, "Fourth Sunday in Lent (Mid-Lent)"),
    (-7, "Palm Sunday (Sunday next before Easter)"),
    (-3, "Thursday before Easter (Maundy Thursday)"),
    (-2, "Good Friday"),
    (-1, "Easter Even"),
    (0, "Easter Day"),
    (1, "Monday in Easter week"),
    (2, "Tuesday in Easter week"),
    (7, "First Sunday after Easter (Low Sunday)"),
    (35, "Rogation Sunday"),
    (36, "Rogation Monday"),
    (37, "Rogation Tuesday"),
    (38, "Rogation Wednesday"),
    (39, "Ascension Day"),
    (49, "Whitsunday"),
    (50, "Monday in Whitsun week"),
    (51, "Tuesday in Whitsun week"),
    (56, "Trinity Sunday"),
]


def advent_sunday(y: int) -> Day:
    """Nearest Sunday to St Andrew (30 November), in the civil calendar."""
    andrew = civil_day(y, 11, 30)
    w = andrew.weekday_index          # 0 = Sunday
    delta = -w if w <= 3 else 7 - w
    return andrew + delta


def ember_days(y: int) -> list[tuple[Day, str]]:
    """Wednesday, Friday, Saturday after the first Sunday in Lent, Whitsunday,
    Holy Cross (14 Sept) and St Lucy (13 Dec)."""
    e, _ = easter(y)
    out = []
    for base, label in ((e - 42, "after the first Sunday in Lent"),
                        (e + 49, "after Whitsunday")):
        for off in (3, 5, 6):
            out.append((base + off, f"Ember day ({label})"))
    for (m, d), label in (((9, 14), "after Holy Cross Day, 14 September"),
                          ((12, 13), "after St Lucy, 13 December")):
        anchor = civil_day(y, m, d)
        w = anchor.weekday_index
        wed = anchor + ((3 - w) % 7 or 7)
        for off in (0, 2, 3):
            out.append((wed + off, f"Ember day ({label})"))
    return out


def moveable_feasts(y: int) -> list[tuple[Day, str]]:
    e, _ = easter(y)
    feasts = [(e + off, name) for off, name in MOVEABLE]
    feasts.append((advent_sunday(y), "Advent Sunday"))
    return feasts


QUARTER_DAYS = [
    ((3, 25), "Lady Day (Annunciation) - quarter day"),
    ((6, 24), "Midsummer Day (Nativity of St John Baptist) - quarter day"),
    ((9, 29), "Michaelmas (St Michael and All Angels) - quarter day"),
    ((12, 25), "Christmas Day - quarter day"),
]


def quarter_days(y: int) -> list[tuple[Day, str]]:
    out = []
    for (m, d), label in QUARTER_DAYS:
        day = civil_day(y, m, d)
        out.append((day, label))
        if day.civil_calendar == GREGORIAN:
            out.append((day_os(y, m, d), label.replace(" - quarter day", "") +
                        " - Old Style equivalent"))
    return out
