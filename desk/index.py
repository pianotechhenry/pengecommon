"""Read-only access to the attestation index built by ``desk build``."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from desk.keys import ngram_hash, to_signed

KIND_FORM, KIND_LEMMA, KIND_FOREIGN = 0, 1, 2


@dataclass
class Text:
    tid: int
    tcp: str
    title: str
    author: str
    year: int
    kind: str
    date_raw: str
    collection: str
    words: int

    def cite(self) -> dict:
        return {"tcp": self.tcp, "title": self.title, "author": self.author,
                "year": self.year, "date_kind": self.kind, "date_raw": self.date_raw,
                "collection": self.collection}


class Index:
    def __init__(self, path: Path):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(
                f"no attestation index at {path}; build it with `desk build` (see README)")
        self.path = path
        self.con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
        self.texts: dict[int, Text] = {}
        for row in self.con.execute(
                "SELECT tid, tcp, title, author, year, date_kind, date_raw, collection, words "
                "FROM texts WHERE holdout=0"):
            self.texts[row[0]] = Text(*row)
        self.holdout = [r[0] for r in self.con.execute("SELECT tcp FROM texts WHERE holdout=1")]
        self.decades = {d: (n, w) for d, n, w in
                        self.con.execute("SELECT decade, ntexts, nwords FROM corpus_decades")}
        self.info = dict(self.con.execute("SELECT key, value FROM info"))
        tables = {r[0] for r in self.con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.has_ngrams = "ngrams" in tables
        self.has_phrases = "phrases" in tables
        self.has_punct = "punct" in tables

    # -- corpus size -----------------------------------------------------------
    def corpus_before(self, year: int) -> tuple[int, int]:
        """Texts and words in decades wholly before `year`, plus the year's own
        decade pro rata (decade resolution)."""
        nt = nw = 0.0
        for d, (n, w) in self.decades.items():
            if d + 10 <= year:
                nt += n
                nw += w
            elif d < year:
                frac = (year - d) / 10
                nt += n * frac
                nw += w * frac
        return int(nt), int(nw)

    def corpus_total(self) -> tuple[int, int]:
        return (sum(n for n, _ in self.decades.values()),
                sum(w for _, w in self.decades.values()))

    def texts_between(self, a: int, b: int) -> float:
        """Approximate number of texts dated in [a, b)."""
        total = 0.0
        for d, (n, _) in self.decades.items():
            lo, hi = max(a, d), min(b, d + 10)
            if hi > lo:
                total += n * (hi - lo) / 10
        return total

    # -- entries -----------------------------------------------------------------
    @lru_cache(maxsize=200_000)
    def entry(self, kind: int, key: str):
        r = self.con.execute(
            "SELECT id, kind, key, first_any, first_firm, ntexts, ntok, decades, lemma_id, lemmas, early "
            "FROM entries WHERE kind=? AND key=?", (kind, key)).fetchone()
        if not r:
            return None
        return {
            "id": r[0], "kind": r[1], "key": r[2], "first_any": r[3], "first_firm": r[4],
            "ntexts": r[5], "ntok": r[6], "decades": _decades(r[7]), "lemma_id": r[8],
            "lemmas": r[9], "early": [int(x) for x in (r[10] or "").split(",") if x],
        }

    @lru_cache(maxsize=50_000)
    def entry_by_id(self, eid: int):
        r = self.con.execute("SELECT kind, key FROM entries WHERE id=?", (eid,)).fetchone()
        return self.entry(r[0], r[1]) if r else None

    def kwic(self, eid: int) -> list[dict]:
        out = []
        for slot, tid, line in self.con.execute(
                "SELECT slot, tid, line FROM kwic WHERE entry_id=? ORDER BY slot", (eid,)):
            t = self.texts.get(tid)
            if t is None or line is None:
                continue
            left, kw, right = (line.split("\t") + ["", "", ""])[:3]
            out.append({"slot": slot, "left": left, "kw": kw, "right": right, **t.cite()})
        return out

    def year(self, tid: int | None) -> int | None:
        if tid is None or tid < 0:
            return None
        t = self.texts.get(tid)
        return t.year if t else None

    def text(self, tid: int | None) -> Text | None:
        return self.texts.get(tid) if tid is not None else None

    # -- phrases --------------------------------------------------------------
    def ngram(self, words: list[str]):
        if not self.has_ngrams or len(words) not in (2, 3):
            return None
        h = to_signed(ngram_hash(words))
        r = self.con.execute(
            "SELECT n, first_any, first_firm, ntexts, decades FROM ngrams WHERE hash=?", (h,)).fetchone()
        if not r:
            return None
        from desk.build.ngrams import unpack_decades
        return {"n": r[0], "first_any": r[1], "first_firm": r[2], "ntexts": r[3],
                "decades": unpack_decades(r[4]) if isinstance(r[4], bytes) else _decades(r[4]),
                "source": "n-gram index (phrases in >= %s texts)" % self.info.get("ngram_min_df", "?")}

    def phrase(self, text: str):
        if not self.has_phrases:
            return None
        r = self.con.execute(
            "SELECT first_any, first_firm, ntexts, decades, kwic FROM phrases WHERE phrase=?",
            (text,)).fetchone()
        if not r:
            return None
        import json
        return {"first_any": r[0], "first_firm": r[1], "ntexts": r[2], "decades": _decades(r[3]),
                "kwic": json.loads(r[4] or "[]"), "source": "exhaustive phrase scan"}

    def punct(self, seq: str):
        if not self.has_punct:
            return None
        r = self.con.execute(
            "SELECT first_any, first_firm, ntexts, decades, kwic FROM punct WHERE seq=?", (seq,)).fetchone()
        if not r:
            return {"absent": True}
        import json
        return {"first_any": r[0], "first_firm": r[1], "ntexts": r[2], "decades": _decades(r[3]),
                "kwic": json.loads(r[4] or "[]")}


def _decades(s) -> dict[int, int]:
    out = {}
    if not s:
        return out
    for part in str(s).split(","):
        d, _, n = part.partition(":")
        if d and n:
            out[int(d)] = int(n)
    return out
