"""Correct one text's date in a built index without re-aggregating.

    python scripts/redate_text.py B03842 1672 ranged

Used once, for B03842 ("The joviall crew: or, Beggars-bush", imprint
"[not after 1672]"), whose catalogue date "1uuu-1672?" the first build read
as the year 1000; the date parser is fixed for future builds.

The patch is exact for a text that sits at the start of the chronology, as
B03842 did: every entry it contains then lists it among its first five texts,
so each entry's first texts, decade counts and KWIC order can be corrected.
For a text elsewhere in the chronology, rebuild with `desk build --stage
aggregate` instead (which needs the keys/ files).
"""
from __future__ import annotations

import sqlite3
import sys

from desk.build.aggregate import DECADE0, NDEC
from desk.paths import index_path


def dec(y: int) -> int:
    return DECADE0 + 10 * min(max((y - DECADE0) // 10, 0), NDEC - 1)


def main(tcp: str, year: int, kind: str) -> None:
    con = sqlite3.connect(index_path(), timeout=600)
    tid, old_year, words = con.execute(
        "SELECT tid, year, words FROM texts WHERE tcp=?", (tcp,)).fetchone()
    years = dict(con.execute("SELECT tid, year FROM texts"))
    years[tid] = year
    od, nd = dec(old_year), dec(year)
    con.execute("UPDATE texts SET year=?, date_kind=?, date_raw=date_raw || ? WHERE tid=?",
                (year, kind, f" (date corrected to {year}, {kind})", tid))
    con.execute("UPDATE corpus_decades SET ntexts=ntexts-1, nwords=nwords-? WHERE decade=?", (words, od))
    con.execute("UPDATE corpus_decades SET ntexts=ntexts+1, nwords=nwords+? WHERE decade=?", (words, nd))
    rows = con.execute("SELECT id, early, decades FROM entries WHERE ','||early||',' LIKE ?",
                       (f"%,{tid},%",)).fetchall()
    for eid, early, decs in rows:
        tids = sorted((int(x) for x in early.split(",")), key=lambda t: (years[t], t))
        d = {}
        for part in (decs or "").split(","):
            if ":" in part:
                k, v = part.split(":")
                d[int(k)] = int(v)
        d[od] = d.get(od, 0) - 1
        if d[od] <= 0:
            del d[od]
        d[nd] = d.get(nd, 0) + 1
        con.execute("UPDATE entries SET early=?, first_any=?, decades=? WHERE id=?",
                    (",".join(map(str, tids)), tids[0],
                     ",".join(f"{k}:{v}" for k, v in sorted(d.items())), eid))
        k = con.execute("SELECT rowid, tid FROM kwic WHERE entry_id=? AND slot<3 ORDER BY slot",
                        (eid,)).fetchall()
        for slot, (rowid, _) in enumerate(sorted(k, key=lambda r: (years[r[1]], r[1]))):
            con.execute("UPDATE kwic SET slot=? WHERE rowid=?", (slot, rowid))
    con.commit()
    print(f"{tcp}: {old_year} -> {year} ({kind}); {len(rows)} entries corrected")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3])
