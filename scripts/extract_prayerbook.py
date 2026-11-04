"""Extract the fixed holy days and calendar days from two printed Prayer Books.

Sources (TEI P5 transcriptions, Text Creation Partnership, CC0):

* A05983 - The booke of common prayer ... (London, 1603): the Elizabethan
  book of 1559 with the calendar as revised in 1561, printed before the 1604
  changes.  Used for 1580-1661.  Its holy days are read from the table
  "Lessons proper for holy dayes"; its black-letter days from the Kalendar.
  Many red-letter cells in this transcription are keyed as illegible
  (red ink reproduces badly on the microfilm); where a holy day's own
  Kalendar cell is illegible its date is taken from the 1662 Kalendar, and
  the entry says so.
* A28758 - The book of common prayer ... (London, 1693): the 1662 book.  Used
  from 1662.  Holy days from "A Table of the Feasts that are to be observed
  in the Church of England through the Year"; vigils from the table that
  follows it; dates and black-letter days from the Kalendar.

Run:  python scripts/extract_prayerbook.py [dir-with-xml]
Writes desk/data/prayerbook.json.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

from lxml import etree

TEI = "{http://www.tei-c.org/ns/1.0}"
RAW = "https://raw.githubusercontent.com/textcreationpartnership/{id}/master/{id}.xml"
OUT = Path(__file__).resolve().parent.parent / "desk" / "data" / "prayerbook.json"

# The fixed holy days and their dates.  The list of which days are holy days
# is read from each book (see main); the dates are checked against both
# Kalendars, which print the names in abbreviated forms ("P. Mary",
# "S. Io. B."), so the patterns below allow for those.
FIXED = [
    # name, month, day, pattern for the Kalendar's abbreviations, pattern for the book's list
    ("Circumcision of Christ", 1, 1, r"circum", r"circum"),
    ("Epiphany", 1, 6, r"epiph", r"epiph"),
    ("Conversion of St Paul", 1, 25, r"paul|conu|conv", r"conu|conv"),
    ("Purification of the Virgin Mary", 2, 2, r"purif|p\. mary", r"purif"),
    ("St Matthias", 2, 24, r"matth?ias|matt", r"matth?ias"),
    ("Annunciation of the Virgin Mary", 3, 25, r"annu|annun|an\. mary", r"ann?u[nc]"),
    ("St Mark", 4, 25, r"\bmark", r"\bmarke?\b"),
    ("St Philip and St James (Jacob)", 5, 1, r"phil", r"philip"),
    ("St Barnabas", 6, 11, r"barn", r"barnab"),
    ("Nativity of St John Baptist", 6, 24, r"bapt|bap\.|io\. b|iohn b|john b", r"bapt|bap\."),
    ("St Peter", 6, 29, r"peter", r"peter"),
    ("St James", 7, 25, r"iames|james|iac", r"^s[t.]*\.? ?(iames|james)"),
    ("St Bartholomew", 8, 24, r"bart", r"bartholom"),
    ("St Matthew", 9, 21, r"matth?ew|\bmatth?\b", r"matth?ew"),
    ("St Michael and All Angels", 9, 29, r"mich", r"michael"),
    ("St Luke", 10, 18, r"\bluk", r"\bluke\b"),
    ("St Simon and St Jude", 10, 28, r"simon|iude|jude", r"simon"),
    ("All Saints", 11, 1, r"^all\b|all sa|all hal|alhal", r"all saints"),
    ("St Andrew", 11, 30, r"andr", r"andrew"),
    ("St Thomas the Apostle", 12, 21, r"\btho\b|thom", r"thomas"),
    ("Nativity of Christ", 12, 25, r"christ|natiu|nativ", r"natiuit[a-z]* of (christ|our lord)"),
    ("St Stephen", 12, 26, r"steph|steu", r"steph|steu"),
    ("St John the Evangelist", 12, 27, r"\bio\.|iohn|john", r"euangelist|^s\. iohn\.?$"),
    ("Holy Innocents", 12, 28, r"innoc", r"innocent"),
]


def norm(s: str) -> str:
    s = s.replace("ſ", "s").replace("&", "and")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def fold(s: str) -> str:
    return norm(s).lower().replace("v", "u").replace("j", "i")


def text_of(el) -> str:
    return norm("".join(el.itertext()))


def get(id_: str, where: Path) -> etree._Element:
    p = where / f"{id_}.tcp.xml"
    if not p.exists():
        p.write_bytes(urllib.request.urlopen(RAW.format(id=id_)).read())
    return etree.parse(str(p)).getroot()


def facs_before(el) -> str:
    for prev in el.itersiblings(preceding=True):
        for pb in [prev] if prev.tag == TEI + "pb" else list(prev.iter(TEI + "pb"))[::-1]:
            return pb.get("facs", "")
    par = el.getparent()
    return facs_before(par) if par is not None else ""


def all_pbs(root):
    return [(pb, pb.get("facs", "")) for pb in root.iter(TEI + "pb")]


def page_of(root, target) -> str:
    """facs of the last <pb> before `target` in document order."""
    last = ""
    for el in root.iter():
        if el is target:
            return last
        if el.tag == TEI + "pb":
            last = el.get("facs", "")
    return last


DOMINICAL = set("abcdefgABCDEFG")
BIBLE_REF = re.compile(r"\d\s*\.?\s*$")


MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def dominical(month: int, day: int) -> str:
    """The Kalendar's Sunday letter for a day: A on 1 January, then b c d e f g."""
    doy = sum(MONTH_DAYS[: month - 1]) + day
    return "Abcdefg"[(doy - 1) % 7]


def kalendar_1662(root) -> list[dict]:
    """The 1693 transcription keys each Kalendar cell as its own row, so a day
    is recognised as <day number> followed by that day's Sunday letter; a day
    whose number cell is blank is recognised by its letter alone."""
    cal = [d for d in root.iter(TEI + "div") if d.get("type") == "calendar"][0]
    out = []
    for month, table in enumerate(cal.iter(TEI + "table"), start=1):
        facs = page_of(root, table)
        cells = [(text_of(c), c.find(".//" + TEI + "hi") is not None)
                 for c in table.iter(TEI + "cell")]
        expect = 1
        i = 0
        while i < len(cells) - 1 and expect <= MONTH_DAYS[month - 1]:
            t, _ = cells[i]
            nxt, _ = cells[i + 1]
            day = None
            if len(nxt) == 1 and nxt in DOMINICAL:
                if t.isdigit() and expect <= int(t) <= expect + 2 and \
                        nxt.lower() == dominical(month, int(t)).lower():
                    day = int(t)
                elif t == "" and nxt.lower() == dominical(month, expect).lower():
                    day = expect
            if day is None:
                i += 1
                continue
            name, red = "", False
            if i + 2 < len(cells):
                cand, hi = cells[i + 2]
                if cand and re.search(r"[A-Za-z]", cand) and not BIBLE_REF.search(cand) \
                        and not re.fullmatch(r"[ivxlcIVXLC]+\.?", cand):
                    name, red = cand, hi
            if name:
                out.append({"month": month, "day": day, "printed": name,
                            "red": red, "facs": facs})
            expect = day + 1
            i += 2
    return out


def kalendar_1603(root) -> list[dict]:
    cal = [d for d in root.iter(TEI + "div")
           if "almanac" in (d.get("type") or "")][0]
    out = []
    for month, table in enumerate(cal.iter(TEI + "table"), start=1):
        facs = page_of(root, table)
        for row in table.iter(TEI + "row"):
            cells = [text_of(c) for c in row.findall(TEI + "cell")]
            for j in range(len(cells) - 2):
                if cells[j].isdigit() and 1 <= int(cells[j]) <= 31 and \
                        len(cells[j + 1]) == 1 and cells[j + 1] in DOMINICAL:
                    day = int(cells[j])
                    rest = cells[j + 2:]
                    # skip the Roman date (Kal./Non./Id. or numerals), keep the name
                    k = 0
                    while k < len(rest) and (re.search(r"\b(kl|kal|id|no|non|prid)\b\.?",
                                                       rest[k].lower())
                                             or re.fullmatch(r"[ivxlc•\s.]+", rest[k].lower())
                                             or rest[k] in ("Kl.", "•")):
                        k += 1
                    name = rest[k] if k < len(rest) else ""
                    legible = bool(name) and not re.search(r"[〈〉•◊●]", name)
                    if re.match(r"(ianuar|februar|mart|april|mai|iun|iul|august|septemb|octob|"
                                r"nouemb|novemb|decemb|kalend|nonas|idus)", fold(name)):
                        break
                    if name and not re.fullmatch(r"[ivxlc•\s.\d]+", name.lower()):
                        out.append({"month": month, "day": day, "printed": name,
                                    "legible": legible, "facs": facs})
                    break
    return out


def lessons_proper_1603(root) -> list[dict]:
    out = []
    for table in root.iter(TEI + "table"):
        head = table.find(TEI + "head")
        if head is None or "holy dayes" not in text_of(head).lower():
            continue
        facs = page_of(root, table)
        for row in table.iter(TEI + "row"):
            cells = row.findall(TEI + "cell")
            if not cells or cells[0].get("role") != "label":
                continue
            name = text_of(cells[0])
            if not name or re.match(r"(i+|first|second)\.? less", name.lower()) or \
                    name.lower() in ("mattens.", "euensong."):
                continue
            out.append({"printed": name, "facs": facs})
    return out


def feast_table_1662(root) -> tuple[list[dict], list[dict]]:
    feasts, vigils = [], []
    for lst in root.iter(TEI + "list"):
        head = lst.find(TEI + "head")
        if head is not None and "Table of the Feas" in text_of(head):
            facs = page_of(root, lst)
            for it in lst.iter(TEI + "item"):
                if it.find(TEI + "list") is not None:
                    continue
                feasts.append({"printed": text_of(it), "facs": facs})
    for table in root.iter(TEI + "table"):
        head = table.find(TEI + "head")
        if head is not None and "Vigils" in text_of(head):
            facs = page_of(root, table)
            for row in table.iter(TEI + "row"):
                vigils.append({"printed": text_of(row), "facs": facs})
            break
    return feasts, vigils


def _near(kal, pat, month, day, span=3):
    best = None
    for e in kal:
        if e["month"] != month or abs(e["day"] - day) > span:
            continue
        if not e.get("legible", True):
            continue
        if re.search(pat, fold(e["printed"])):
            if best is None or abs(e["day"] - day) < abs(best["day"] - day):
                best = e
    return best


def main(where: Path) -> None:
    where.mkdir(parents=True, exist_ok=True)
    r62 = get("A28758", where)
    r03 = get("A05983", where)
    k62 = kalendar_1662(r62)
    k03 = kalendar_1603(r03)
    feasts62, vigils62 = feast_table_1662(r62)
    lessons03 = lessons_proper_1603(r03)
    kal = {"A05983": k03, "A28758": k62}
    books = {}
    for book, own, other, listing, title in (
        ("1559", "A05983", "A28758", lessons03,
         "The booke of common prayer (London, 1603): the 1559 book with the 1561 calendar"),
        ("1662", "A28758", "A05983", feasts62,
         "The book of common prayer (London, 1693): the 1662 book"),
    ):
        holy = []
        for name, month, day, pat, lpat in FIXED:
            listed = next((x for x in listing if re.search(lpat, fold(x["printed"]))), None)
            entry = {"name": name, "month": month, "day": day,
                     "listed_as": listed["printed"] if listed else None,
                     "listed_in": f"{own} image {listed['facs'].split(':')[-1]}" if listed else None}
            evidence = []
            exact = False
            for src in (own, other):
                row = _near(kal[src], pat, month, day)
                if row:
                    off = row["day"] - day
                    evidence.append(
                        f"{src} Kalendar, image {row['facs'].split(':')[-1]}: '{row['printed']}' "
                        + ("on the day" if off == 0 else
                           f"in the row for day {row['day']} (transcription row offset {off:+d})"))
                    exact = exact or off == 0
            entry["date_evidence"] = evidence
            if listed is None:
                entry["tag"] = "UNVERIFIED"
            elif exact:
                entry["tag"] = "DOCUMENTED"
            elif evidence:
                entry["tag"] = "REASONABLE INFERENCE"
            else:
                entry["tag"] = "UNVERIFIED"
            holy.append(entry)
        holy_days = {(h["month"], h["day"]) for h in holy}
        cal_days = []
        own_kal = list(kal[own])
        # fragments of a name split over two Kalendar rows ("All" / "Saints.",
        # "Concept" / "Vir. Mary", "S. Phil." / "and Iac.") belong to the day before
        skip = set()
        for a, b in zip(own_kal, own_kal[1:]):
            if own == "A28758" and b["month"] == a["month"] and b["day"] == a["day"] + 1 and (
                    b["printed"][:1].islower() or
                    (" " not in a["printed"].strip() and not a["printed"].endswith("."))):
                skip.add(id(b))
        near_holy = []
        for name, month, day, pat, lpat in FIXED:
            near_holy.append((month, day, pat))
        for e in own_kal:
            if id(e) in skip:
                continue
            if any(e["month"] == m and abs(e["day"] - d) <= 3 and re.search(p, fold(e["printed"]))
                   for m, d, p in near_holy):
                continue            # a holy day keyed a row or two away from its date
            if (e["month"], e["day"]) in holy_days or not e.get("legible", True):
                continue
            f = fold(e["printed"])
            if re.fullmatch(r"fa[sltih]{2}\.?", f) or re.search(r"autumn|uernal|aequinoct|solstit", f):
                continue            # vigils are listed separately; equinox notes are not days
            if re.fullmatch(r"(march|man|ium|iun|iul|mai|mart)\.?", f):
                continue            # the month of a Kalends date ("xv Kl. Martii")
            agree = any(o["month"] == e["month"] and o["day"] == e["day"] and
                        fold(o["printed"])[:4] == fold(e["printed"])[:4] for o in kal[other])
            if own == "A05983":
                tag = "DOCUMENTED"          # one row per day in this transcription
            else:
                tag = "DOCUMENTED" if agree else "REASONABLE INFERENCE"
            cal_days.append({"month": e["month"], "day": e["day"], "printed": e["printed"],
                             "red": e.get("red", False),
                             "cite": f"{own} Kalendar image {e['facs'].split(':')[-1]}",
                             "tag": tag})
        books[book] = {"source": own, "title": title, "holy_days": holy,
                       "calendar_days": cal_days,
                       "vigils": [v["printed"] for v in vigils62] if book == "1662" else []}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(books, ensure_ascii=False, indent=1), encoding="utf-8")
    for b, d in books.items():
        tags = {}
        for h in d["holy_days"]:
            tags[h["tag"]] = tags.get(h["tag"], 0) + 1
        print(b, d["source"], tags, len(d["calendar_days"]), "other calendar days")
        for h in d["holy_days"]:
            if h["tag"] != "DOCUMENTED":
                print("   ", h["name"], h["tag"], h["listed_as"], h["date_evidence"])


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/prayerbook"))
