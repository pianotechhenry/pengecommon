"""Unit tests: keys, dates, calendar, tokens, streams, reader, watch list."""
from __future__ import annotations

import numpy as np
import pytest

from desk.build.dates import parse_imprint
from desk.build.extract import _combine
from desk.check import reader
from desk.check.streams import DIALOGUE, INTERIOR, NARRATION, detect_style, label
from desk.check.tokens import punctuation, words
from desk.keys import bigram_hash, form_key, trigram_hash, word_hash
from desk.sky import calendar as C
from desk.watchlist import load


def test_form_key():
    assert form_key("Lovers’") == "lovers'"
    assert form_key("ſin") == "sin"
    assert form_key("“Golden") == "golden"
    assert form_key("To-Morrow,") == "to-morrow"


def test_ngram_hash_matches_numpy():
    a, b, c = "see", "you", "later"
    h = np.array([word_hash(a), word_hash(b), word_hash(c)], dtype=np.uint64)
    assert int(_combine(h[:1], h[1:2])[0]) == bigram_hash(a, b)
    assert int(_combine(h[:1], h[1:2], h[2:3])[0]) == trigram_hash(a, b, c)


@pytest.mark.parametrize("raw,year,kind", [
    ("1625.", 1625, "firm"), ("[1623]", 1623, "firm"), ("[1569?]", 1569, "conjectural"),
    ("[ca. 1600]", 1600, "conjectural"), ("163[9?]", 1639, "conjectural"),
    ("M.D.LXVI. [1566]", 1566, "firm"), ("An. M.D.XXXIII. [1533, i.e. 1534]", 1534, "firm"),
    ("Anno. M.D.LIIII. mense Septembri]", 1554, "firm"), ("[between 1550 and 1560]", 1550, "ranged"),
    ("1580-1590?", 1580, "ranged"), ("155-?", 1550, "ranged"), ("[15--?]", 1500, "ranged"),
    ("Anno 1.5.62.", 1562, "firm"), ("[1641 or 1642]", 1641, "ranged"),
])
def test_imprint_dates(raw, year, kind):
    assert parse_imprint(raw) == (year, kind)


def test_easter_and_styles():
    assert C.fmt(C.easter(1589)[0].os) == "30 March 1589"
    assert C.fmt(C.easter(1689)[0].os) == "31 March 1689"
    assert C.fmt(C.easter(1753)[0].ns) == "22 April 1753"
    assert C.fmt(C.easter(2025)[0].ns) == "20 April 2025"
    d = C.day_os(1689, 5, 1)
    assert C.fmt(d.ns) == "11 May 1689" and d.weekday == "Wednesday"
    last_os = C.civil_day(1752, 9, 2)
    assert last_os.weekday == "Wednesday" and C.fmt((last_os + 1).civil) == "14 September 1752"
    with pytest.raises(ValueError):
        C.civil_day(1752, 9, 5)


def test_legal_year():
    assert C.civil_day(1689, 2, 10).legal_label() == "10 February 1688/9"
    assert C.civil_day(1700, 3, 1).legal_label() == "1 March 1699/1700"
    assert C.civil_day(1690, 1, 5).legal_label() == "5 January 1689/90"
    assert C.civil_day(1689, 3, 25).legal_label() == "25 March 1689"
    assert C.civil_day(1753, 2, 1).legal_label() == "1 February 1753"


def test_advent_and_quarter_days():
    assert C.advent_sunday(1589).weekday == "Sunday"
    names = [n for _, n in C.quarter_days(1589)]
    assert any("Lady Day" in n for n in names) and len(names) == 4
    assert len([n for _, n in C.quarter_days(1760)]) == 8      # with Old Style equivalents


def test_tokens():
    t = "‘Now get lost,’ she said. ’Tis the boys’ fault, goin’ on. What!? to-morrow, ma'am, that's"
    toks = [w.text for w in words(t)]
    assert toks == ["Now", "get", "lost", "she", "said", "’Tis", "the", "boys’", "fault",
                    "goin’", "on", "What", "to-morrow", "ma'am", "that's"]
    assert [p[0] for p in punctuation(t)] == ["!?"]


def test_streams_british_and_double():
    t = "‘Go now,’ she said, ‘or the boys’ supper spoils.’ He went."
    lab = label(t, [], detect_style([t]))
    assert lab[t.index("Go")] == DIALOGUE and lab[t.index("she")] == NARRATION
    assert lab[t.index("supper")] == DIALOGUE and lab[t.index("He")] == NARRATION
    p = reader._inline("“See you,” he said. *Not now.* “I *told* you.”")
    lab = label(p.text, p.italic, detect_style([p.text]))
    assert lab[p.text.index("See")] == DIALOGUE
    assert lab[p.text.index("Not")] == INTERIOR
    assert lab[p.text.index("told")] == DIALOGUE        # emphasis inside dialogue


def test_markdown_and_docx(tmp_path):
    md = tmp_path / "s.md"
    md.write_text("<!-- a note\nto self -->\n# One\n\nShe *thought* of it.\nStill.\n\n* * *\n\n“Yes,” he said.\n",
                  encoding="utf-8")
    ps = reader.read(md)
    assert [p.text for p in ps] == ["One", "She thought of it. Still.", "“Yes,” he said."]
    assert ps[0].heading and ps[1].italic == [(4, 11)]
    import docx
    d = docx.Document()
    para = d.add_paragraph("He ")
    r = para.add_run("would not")
    r.italic = True
    para.add_run(" go.")
    d.save(tmp_path / "s.docx")
    ps = reader.read(tmp_path / "s.docx")
    assert ps[0].text == "He would not go." and ps[0].italic == [(3, 12)]


def test_watchlist_seed():
    from desk.paths import watchlist_path
    es = {e.term: e for e in load(watchlist_path())}
    assert es["Rowan"].case and es["Rowan"].from_year == 1900
    assert es["see you later"].phrase == ("see", "you", "later")
    assert "connected" in es["connect"].keys
    assert all(e.tag in ("DOCUMENTED", "REASONABLE INFERENCE", "CONTESTED", "UNVERIFIED")
               for e in es.values())


def test_open_ended_dates():
    from desk.build.dates import combine, parse_catalogue
    assert parse_imprint("[not after 1672]") == (1672, "ranged")
    assert parse_catalogue("1uuu-1672?") == (1672, "ranged")
    assert parse_catalogue("1000") == (None, "ranged")
    assert combine("[not after 1672]", "", "1uuu-1672?")[:2] == (1672, "ranged")
