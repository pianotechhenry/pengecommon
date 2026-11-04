"""A tiny synthetic attestation index, for testing the checker's rules
without the real corpus.  Words and dates here are test data only."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from desk.build.aggregate import SCHEMA

# (tcp, year, kind)
TEXTS = [
    ("T001", 1550, "firm"), ("T002", 1560, "firm"), ("T003", 1570, "firm"),
    ("T004", 1575, "conjectural"), ("T005", 1580, "firm"), ("T006", 1595, "firm"),
    ("T007", 1600, "firm"), ("T008", 1620, "firm"), ("T009", 1650, "firm"),
    ("T010", 1700, "firm"),
]
# key -> tids (0-based indexes into TEXTS); kind 0 form, 1 lemma, 2 foreign
ENTRIES = [
    (0, "common", [0, 1, 2, 4, 5]),        # OK for 1589
    (0, "thin", [2]),                      # NOTE: one text before 1589
    (0, "lateish", [5, 6]),                # BORDERLINE: 1595
    (0, "late", [8, 9]),                   # FLAG: 1650
    (0, "conjonly", [3]),                  # only a conjectural date (1575)
    (0, "mixed", [3, 7]),                  # conjectural 1575, firm 1620: FLAG, CONTESTED
    (0, "colour", [7]),                    # the British spelling only later...
    (0, "color", [0, 1, 2]),               # ...the variant early
    (1, "walk", [0, 1, 2]),                # lemma only; the form 'walks' absent
    (2, "pater", [0, 1]),                  # foreign only
    (0, "golden", [0, 1, 2, 4]), (0, "boy", [0, 1, 2, 4]),
]


def build(path: Path) -> Path:
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    for i, (tcp, year, kind) in enumerate(TEXTS):
        con.execute("INSERT INTO texts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (i, tcp, "eebo", tcp[:3], f"Title {tcp}", "Anon", year, kind,
                     f"[{year}?]" if kind != "firm" else str(year), "eng", 10000, "A", "", 0))
    for eid, (kind, key, tids) in enumerate(ENTRIES):
        firm = [t for t in tids if TEXTS[t][2] == "firm"]
        decades = {}
        for t in tids:
            d = TEXTS[t][1] // 10 * 10
            decades[d] = decades.get(d, 0) + 1
        con.execute("INSERT INTO entries VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (eid, kind, key, tids[0], firm[0] if firm else None, len(tids), len(tids) * 3,
                     ",".join(f"{d}:{n}" for d, n in sorted(decades.items())), None, None,
                     ",".join(str(t) for t in tids[:5])))
        for slot, t in enumerate(tids[:3]):
            con.execute("INSERT INTO kwic VALUES (?,?,?,?,?)",
                        (eid, slot, t, 0, f"left context\t{key}\tright context"))
    for d in range(1470, 1810, 10):
        n = sum(1 for _, y, _ in TEXTS if y // 10 * 10 == d)
        con.execute("INSERT INTO corpus_decades VALUES (?,?,?)", (d, n, n * 10000))
    # phrase tables: "every thing" printed early (closed-compound fallback);
    # "golden boy" only from 1650; "!?" never; "!!" from 1570
    from desk.build.ngrams import pack_decades
    import numpy as np
    from desk.keys import ngram_hash, to_signed
    con.executescript("""
      CREATE TABLE ngrams(hash INTEGER PRIMARY KEY, n INTEGER, first_any INTEGER,
        first_firm INTEGER, ntexts INTEGER, decades BLOB) WITHOUT ROWID;
      CREATE TABLE phrases(phrase TEXT PRIMARY KEY, first_any INTEGER, first_firm INTEGER,
        ntexts INTEGER, decades TEXT, kwic TEXT);
      CREATE TABLE punct(seq TEXT PRIMARY KEY, first_any INTEGER, first_firm INTEGER,
        ntexts INTEGER, decades TEXT, kwic TEXT);""")
    for words, tids in ((["every", "thing"], [0, 1, 2, 4]), (["golden", "boy"], [8, 9])):
        dec = sorted({TEXTS[t][1] // 10 * 10 for t in tids})
        blob = pack_decades(np.array([(d - 1470) // 10 for d in dec]),
                            np.array([sum(1 for t in tids if TEXTS[t][1] // 10 * 10 == d) for d in dec]))
        con.execute("INSERT INTO ngrams VALUES (?,?,?,?,?,?)",
                    (to_signed(ngram_hash(words)), 2, tids[0], tids[0], len(tids), blob))
    con.execute("INSERT INTO punct VALUES ('!!', 2, 2, 1, '1570:1', '[]')")
    con.execute("INSERT INTO info VALUES ('built', 'test')")
    con.commit()
    con.close()
    return path
