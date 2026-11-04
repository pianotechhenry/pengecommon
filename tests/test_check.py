"""The checker's rules, against a tiny synthetic index (tests/helpers.py)."""
from __future__ import annotations

from pathlib import Path

import pytest

from desk.check.check import Checker, Config
from desk.check.reader import Paragraph
from desk.etymology import Etymology
from desk.index import Index
from tests.helpers import build


@pytest.fixture(scope="module")
def idx(tmp_path_factory):
    p = build(tmp_path_factory.mktemp("ix") / "index.sqlite")
    return Index(p)


def checker(idx, year=1589, watch=False, wl=None, phrases=False):
    cfg = Config(year=year, use_watchlist=watch, watchlist_path=wl, phrase_heuristic=phrases)
    return Checker(cfg, idx, Etymology(Path("/nonexistent")))


@pytest.mark.parametrize("word,status,tag", [
    ("common", "OK", "DOCUMENTED"),
    ("thin", "NOTE", "DOCUMENTED"),
    ("lateish", "BORDERLINE", "DOCUMENTED"),
    ("late", "FLAG", "DOCUMENTED"),
    ("conjonly", "NOTE", "CONTESTED"),
    ("mixed", "FLAG", "CONTESTED"),
    ("absentword", "UNVERIFIED", "UNVERIFIED"),
])
def test_statuses(idx, word, status, tag):
    r = checker(idx).resolve(word)
    assert (r["status"], r["tag"]) == (status, tag)


def test_window_and_threshold(idx):
    assert checker(idx, year=1580).resolve("lateish")["status"] == "BORDERLINE"  # 1595 = 1580 + 15
    assert checker(idx, year=1579).resolve("lateish")["status"] == "FLAG"        # 1595 > 1579 + 15
    ch = Checker(Config(year=1589, note_min=6, use_watchlist=False), idx, Etymology(Path("/x")))
    assert ch.resolve("common")["status"] == "NOTE"                            # 5 texts < 6


def test_variant_lemma_foreign(idx):
    ch = checker(idx)
    r = ch.resolve("colour")
    assert r["status"] == "OK" and r["tag"] == "REASONABLE INFERENCE" and "color" in r["basis"]
    r = ch.resolve("walks")
    assert r["status"] == "NOTE" and "lemma 'walk'" in r["basis"]
    r = ch.resolve("pater")
    assert r["status"] == "UNVERIFIED" and "foreign" in r["note"]


def test_check_paragraphs_streams_and_romani(idx, tmp_path):
    wl = tmp_path / "wl.yaml"
    wl.write_text("- term: golden boy\n  kind: idiom\n  reason: listed for checking\n  tag: UNVERIFIED\n"
                  "- term: zarq\n  kind: romani\n  reason: test entry\n  tag: REASONABLE INFERENCE\n",
                  encoding="utf-8")
    paras = [Paragraph("“Late golden boy,” said the common thin man. Zarq quorp.", italic=[]),
             Paragraph("Erm. What!?", italic=[(0, 4)])]
    off = checker(idx).check_paragraphs(paras)
    on = checker(idx, watch=True, wl=wl).check_paragraphs(paras)
    items_off, items_on = off["items"], on["items"]
    assert items_off["w:late"]["status"] == "FLAG"
    assert items_off["w:late"]["occurrences"][0]["stream"] == "dialogue"
    assert items_off["w:thin"]["occurrences"][0]["stream"] == "narration"
    assert "i:erm" in items_off and items_off["i:erm"]["occurrences"][0]["stream"] == "interior"
    assert "x:!?" in items_off
    assert "wl:golden boy" not in items_off and "wl:golden boy" in items_on
    rom_off = {r["key"]: r for r in off["romani"]}
    assert "quorp" in rom_off and rom_off["quorp"]["watch"] is None          # unplaced
    rom_on = {r["key"]: r for r in on["romani"]}
    assert rom_on["zarq"]["watch"]["tag"] == "REASONABLE INFERENCE"
    assert off["caveat"].startswith("Absence from the corpus is never proof")


def test_report_renders(idx, tmp_path):
    from desk.report.html import write
    res = checker(idx).check_paragraphs([Paragraph("The late common word.", italic=[])], source="t.md")
    write(res, tmp_path / "r.html", tmp_path / "r.json")
    html = (tmp_path / "r.html").read_text(encoding="utf-8")
    assert "Absence from the corpus is never proof" in html and "w:late" in html


def test_accepted_words_are_not_flagged(idx, tmp_path):
    wl = tmp_path / "wl.yaml"
    wl.write_text("- term: late\n  kind: accepted\n  reason: vetted\n  tag: DOCUMENTED\n", encoding="utf-8")
    res = checker(idx, watch=True, wl=wl).check_paragraphs([Paragraph("The late word.", italic=[])])
    assert "w:late" not in res["items"] and res["accepted"] == {"late": 1}


def test_phrases_compounds_and_punctuation(idx, tmp_path):
    ch = checker(idx)
    r = ch.resolve("everything")                       # not printed closed: "every thing"
    assert r["status"] == "OK" and "every thing" in r["basis"]
    ev = ch.phrase_evidence(("golden", "boy"))
    assert ev["status"] == "FLAG" and ev["first_firm"]["year"] == 1650
    res = ch.check_paragraphs([Paragraph("Ha!! Who!? Kensal  Rise.", italic=[])])
    assert res["items"]["x:!!"]["status"] == "NOTE"            # printed before the year
    assert res["items"]["x:!?"]["status"] == "UNVERIFIED"      # never printed
    wl = tmp_path / "wl.yaml"
    wl.write_text("- term: 'Kensal\\s+Rise'\n  match: regex\n  kind: place\n  reason: station\n"
                  "  tag: DOCUMENTED\n  from_year: 1890\n", encoding="utf-8")
    res = checker(idx, watch=True, wl=wl).check_paragraphs([Paragraph("At Kensal  Rise.", italic=[])])
    hit = res["items"]["wl:Kensal\\s+Rise"]
    assert hit["status"] == "FLAG" and hit["occurrences"][0]["start"] == 3


def test_contractions_are_not_bridged_to_their_lemma(idx):
    # the bridge must never hide a late contraction behind its base verb
    ch = checker(idx)
    assert ch._lemma_bridge({"status": "FLAG", "entry_id": 0}, "don't")["status"] == "FLAG"


def test_silent_names_are_listed_with_context(idx):
    res = checker(idx).check_paragraphs([Paragraph("He spoke of Common things.", italic=[])])
    names = {n["key"]: n for n in res["names"]}
    assert "common" in names and names["common"]["context"]["kw"] == "common"
    assert names["common"]["first_firm"]["year"] == 1550
