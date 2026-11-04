"""`desk sky` and `desk almanac`: one day, or a Lady Day-to-Lady Day year."""
from __future__ import annotations

import csv
import html
import io
import json
from pathlib import Path

from desk.paths import PACKAGE_DIR
from desk.sky import calendar as C
from desk.sky.astro import LAT, LON, hm, moon_day, period_hm, sun_day

PRAYERBOOK = json.loads((PACKAGE_DIR / "data" / "prayerbook.json").read_text(encoding="utf-8"))

CONVENTIONS = (
    "Penge Common, 51.415 N, 0.060 W, sea-level horizon. Sunrise and sunset: upper limb on the "
    "horizon with 34' refraction, in local apparent (sundial) time. Civil twilight ends with the "
    "Sun's centre 6 deg below the horizon, in local mean time (GMT - 14 s); moonrise and moonset "
    "also local mean time. Ephemeris: PyEphem 4 (libastro; VSOP87 Sun, ELP 2000-82 Moon). "
    "Delta T: libastro's model - Morrison & Stephenson (2004) century values, linearly "
    "interpolated, before 1700; the Astronomical Almanac's annual table from 1700.")


def book_for(day: C.Day) -> tuple[str, str]:
    y = day.civil[0]
    if y >= 1662:
        return "1662", ""
    note = ""
    if 1645 <= y <= 1660:
        note = ("1645-1660: the Prayer Book was set aside for the Directory for the Publique "
                "Worship of God (ordinance printed 1644/5, TCP A36061); the days below are the "
                "1559 book's")
    return "1559", note


LEAP_RULE = ("in a leap year the day after 23 February is the doubled day, so St Matthias "
             "falls on the 25th: \"When the yeeres of our Lord may be diuided into foure euen "
             "partes ... the Sunday letter leapeth, and that yere the Psalmes and Lessons which "
             "serue for the xxiij day of February, shall be read againe the day following\" "
             "(TCP A05983)")


def _is_leap(day: C.Day) -> bool:
    y = day.civil[0]
    if day.civil_calendar == C.JULIAN:
        return y % 4 == 0
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def fixed_days(day: C.Day) -> tuple[list, list]:
    book, _ = book_for(day)
    m, d = day.civil[1], day.civil[2]
    b = PRAYERBOOK[book]
    leap_feb = m == 2 and _is_leap(day)
    holy = []
    for h in b["holy_days"]:
        hm_, hd = h["month"], h["day"]
        if leap_feb and (hm_, hd) == (2, 24):
            hd = 25
            h = {**h, "tag": "DOCUMENTED" if book == "1559" else "REASONABLE INFERENCE",
                 "date_evidence": [LEAP_RULE] + (["the 1662 transcription does not restate the rule"]
                                                 if book == "1662" else [])}
        if (hm_, hd) == (m, d):
            holy.append(h)
    other = [c for c in b["calendar_days"] if c["month"] == m and c["day"] == d]
    return holy, other


def sunday_name(day: C.Day) -> str | None:
    if day.weekday_index != 0:
        return None
    y = day.civil[0]
    e, _ = C.easter(y)
    diff = day - e
    if diff == 0:
        return "Easter Day"
    if -63 <= diff < 0:
        names = {-63: "Septuagesima", -56: "Sexagesima", -49: "Quinquagesima",
                 -42: "first Sunday in Lent", -35: "second Sunday in Lent",
                 -28: "third Sunday in Lent", -21: "fourth Sunday in Lent",
                 -14: "fifth Sunday in Lent", -7: "Sunday next before Easter (Palm Sunday)"}
        return names.get(diff)
    if 0 < diff < 39:
        return f"{_ord(diff // 7)} Sunday after Easter"
    if diff == 42:
        return "Sunday after Ascension Day"
    if diff == 49:
        return "Whitsunday"
    if diff == 56:
        return "Trinity Sunday"
    adv = C.advent_sunday(y)
    if diff > 56 and day < adv:
        n = (diff - 56) // 7
        if day + 7 >= adv:
            return f"{_ord(n)} Sunday after Trinity (Sunday next before Advent)"
        return f"{_ord(n)} Sunday after Trinity"
    if adv <= day:
        k = (day - adv) // 7
        if k < 4:
            return f"{_ord(k + 1)} Sunday in Advent"
        return f"{_ord(k - 3)} Sunday after Christmas"
    # January to Septuagesima: after Christmas / after the Epiphany
    epiph = C.civil_day(y, 1, 6)
    if day < epiph:
        return "Sunday after Christmas"
    return f"{_ord((day - epiph) // 7 + 1)} Sunday after the Epiphany"


def _ord(n: int) -> str:
    words = ["", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth",
             "ninth", "tenth", "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth",
             "sixteenth", "seventeenth", "eighteenth", "nineteenth", "twentieth",
             "twenty-first", "twenty-second", "twenty-third", "twenty-fourth", "twenty-fifth",
             "twenty-sixth", "twenty-seventh"]
    return words[n] if 0 < n < len(words) else f"{n}th"


def day_info(day: C.Day) -> dict:
    y = day.civil[0]
    book, book_note = book_for(day)
    holy, other = fixed_days(day)
    moveable = [n for d, n in C.moveable_feasts(y) if d.jdn == day.jdn]
    if day.civil[1] == 12:   # Advent Sunday of the year belongs to the coming church year
        pass
    ember = [n for d, n in C.ember_days(y) if d.jdn == day.jdn]
    quarter = [n for d, n in C.quarter_days(y) if d.jdn == day.jdn]
    e, computus = C.easter(y)
    s = sun_day(day)
    mo = moon_day(day)
    return {
        "os": C.fmt(day.os), "ns": C.fmt(day.ns), "weekday": day.weekday,
        "calendar_in_force": "Old Style (Julian)" if day.civil_calendar == C.JULIAN else "New Style (Gregorian)",
        "legal": day.legal_label(), "legal_year": day.legal_year,
        "easter": C.fmt(e.civil) + f" ({computus})",
        "sunday": sunday_name(day),
        "prayer_book": {"book": book, "source": PRAYERBOOK[book]["source"],
                        "title": PRAYERBOOK[book]["title"], "note": book_note},
        "holy_days": [{"name": h["name"], "printed": h["listed_as"], "tag": h["tag"],
                       "evidence": h["date_evidence"]} for h in holy],
        "calendar_days": [{"printed": c["printed"], "cite": c["cite"], "tag": c["tag"]} for c in other],
        "moveable": moveable, "ember": ember, "quarter": quarter,
        "sun": {"rise_lat": s.sunrise_lat, "set_lat": s.sunset_lat, "rise_lmt": s.sunrise_lmt,
                "set_lmt": s.sunset_lmt, "civil_dawn_lmt": s.civil_dawn_lmt,
                "civil_dusk_lmt": s.civil_dusk_lmt, "noon_lmt": s.noon_lmt},
        "moon": {"phase": mo.phase_name, "illumination": round(mo.illumination, 3),
                 "age_days": round(mo.age_days, 1), "rise_lmt": mo.rise_lmt, "set_lmt": mo.set_lmt,
                 "events": [(n, t) for n, t in mo.events]},
        "delta_t_s": round(s.delta_t_s, 1),
    }


def format_day(info: dict) -> str:
    lines = [f"Penge Common ({LAT:.3f} N, {abs(LON):.3f} W)"]
    lines.append(f"{info['weekday']} {info['os']} Old Style = {info['ns']} New Style")
    lines.append(f"Calendar in force in England: {info['calendar_in_force']}")
    lines.append(f"As dated then: {info['legal']}  (legal year {info['legal_year']}"
                 + (", beginning 25 March)" if info["legal_year"] <= 1751 else ")"))
    lines.append(f"Easter this year: {info['easter']}")
    pb = info["prayer_book"]
    if info["sunday"]:
        lines.append(f"Sunday: {info['sunday']}")
    for h in info["holy_days"]:
        lines.append(f"Holy day: {h['name']} - printed '{h['printed']}' [{pb['source']}; {h['tag']}]")
        for ev in h["evidence"]:
            lines.append(f"    date: {ev}")
    for n in info["moveable"]:
        lines.append(f"Moveable feast: {n}")
    for n in info["ember"]:
        lines.append(n)
    for n in info["quarter"]:
        lines.append(f"Quarter day: {n}")
    for c in info["calendar_days"]:
        lines.append(f"Calendar: '{c['printed']}' ({c['cite']}; {c['tag']})")
    lines.append(f"Prayer Book calendar: {pb['book']} - {pb['title']} [TCP {pb['source']}]")
    if pb["note"]:
        lines.append("  " + pb["note"])
    s = info["sun"]
    lines.append(f"Sun: rises {period_hm(s['rise_lat'])} am, sets {period_hm(s['set_lat'])} pm by the sundial "
                 f"(local apparent time); {hm(s['rise_lmt'])} and {hm(s['set_lmt'])} local mean time")
    lines.append(f"Civil twilight: begins {hm(s['civil_dawn_lmt'])}, ends {hm(s['civil_dusk_lmt'])} "
                 f"({period_hm(s['civil_dusk_lmt'])} pm) local mean time; apparent noon {hm(s['noon_lmt'])} LMT")
    m = info["moon"]
    ev = "; ".join(f"{n} at {hm(t)} LMT" for n, t in m["events"])
    lines.append(f"Moon: {m['phase']}, {m['illumination'] * 100:.0f}% lit, {m['age_days']} days old; "
                 f"rises {hm(m['rise_lmt'])}, sets {hm(m['set_lmt'])} LMT" + (f"; {ev}" if ev else ""))
    lines.append(f"Delta T used: {info['delta_t_s']} s")
    lines.append("Conventions: " + CONVENTIONS)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# almanac

def almanac(year: int) -> list[dict]:
    start = C.civil_day(year, 3, 25)
    end = C.civil_day(year + 1, 3, 25)
    rows = []
    d = start
    while d < end:
        rows.append(day_info(d))
        d = d + 1
    return rows


COLUMNS = ["date (O.S.)", "date (N.S.)", "weekday", "as dated", "Sunday / feast / holy day",
           "calendar (black-letter)", "sunrise (sundial)", "sunset (sundial)",
           "civil twilight ends (LMT)", "moon", "moon lit %", "moonrise (LMT)", "moonset (LMT)",
           "moon phase event"]


def _row(info: dict) -> list:
    feasts = []
    if info["sunday"]:
        feasts.append(info["sunday"])
    feasts += [h["name"] + ("" if h["tag"] == "DOCUMENTED" else f" [{h['tag']}]") for h in info["holy_days"]]
    feasts += info["moveable"] + info["ember"] + info["quarter"]
    cal = [c["printed"] + ("" if c["tag"] == "DOCUMENTED" else " [?]") for c in info["calendar_days"]]
    s, m = info["sun"], info["moon"]
    return [info["os"], info["ns"], info["weekday"], info["legal"], "; ".join(dict.fromkeys(feasts)),
            "; ".join(cal), period_hm(s["rise_lat"]), period_hm(s["set_lat"]),
            period_hm(s["civil_dusk_lmt"]), m["phase"], f"{m['illumination'] * 100:.0f}",
            hm(m["rise_lmt"]), hm(m["set_lmt"]),
            "; ".join(f"{n} {hm(t)}" for n, t in m["events"])]


def write_csv(rows: list[dict], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for r in rows:
            w.writerow(_row(r))


def write_html(rows: list[dict], year: int, path: Path) -> None:
    out = io.StringIO()
    first, last = rows[0], rows[-1]
    out.write(f"""<!doctype html><html lang="en-GB"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Penge almanac {year}</title><style>
:root{{--bg:#fff;--fg:#1d1b18;--muted:#666;--rule:#ccc;--hd:#f2efe8}}
@media (prefers-color-scheme: dark){{:root:not([data-theme=light]){{--bg:#161513;--fg:#ece8e1;--muted:#aaa;--rule:#444;--hd:#262420}}}}
:root[data-theme=dark]{{--bg:#161513;--fg:#ece8e1;--muted:#aaa;--rule:#444;--hd:#262420}}
body{{background:var(--bg);color:var(--fg);font:11px/1.35 Georgia,serif;margin:16px}}
h1{{font-size:18px;margin:0 0 4px}} h2{{font-size:14px;margin:14px 0 4px;page-break-before:auto}}
table{{border-collapse:collapse;width:100%}} th,td{{border-bottom:1px solid var(--rule);padding:2px 4px;text-align:left;vertical-align:top}}
th{{background:var(--hd);font-weight:600}} td.n{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
tr.sun td{{font-weight:600}} .small{{color:var(--muted);font-size:10px}}
.wrap{{overflow-x:auto}}
@media print{{h2{{page-break-before:always}} h2.first{{page-break-before:avoid}} body{{margin:8mm}}}}
</style></head><body>
<h1>Penge Common almanac: Lady Day {html.escape(first['legal'])} to {html.escape(last['legal'])}</h1>
<p class="small">{html.escape(CONVENTIONS)} Holy days from the {html.escape(PRAYERBOOK[book_for(C.civil_day(year, 3, 25))[0]]['title'])};
black-letter days as keyed in the TCP transcription ([?] = row position uncertain in the transcription).
Times in the period's style: 7.45 = a quarter to eight.</p>
""")
    month = None
    for r in rows:
        mlabel = r["os"].split(" ", 1)[1] if r["calendar_in_force"].startswith("Old") else r["ns"].split(" ", 1)[1]
        if mlabel != month:
            if month is not None:
                out.write("</tbody></table></div>")
            out.write(f"<h2 class=\"{'first' if month is None else ''}\">{html.escape(mlabel)}</h2><div class=\"wrap\"><table><thead><tr>"
                      + "".join(f"<th>{html.escape(c)}</th>" for c in COLUMNS) + "</tr></thead><tbody>")
            month = mlabel
        cells = _row(r)
        cls = ' class="sun"' if r["weekday"] == "Sunday" else ""
        out.write(f"<tr{cls}>" + "".join(
            f"<td class=\"n\">{html.escape(str(c))}</td>" if i in (6, 7, 8, 10, 11, 12)
            else f"<td>{html.escape(str(c))}</td>" for i, c in enumerate(cells)) + "</tr>")
    out.write("</tbody></table></div></body></html>")
    Path(path).write_text(out.getvalue(), encoding="utf-8")
