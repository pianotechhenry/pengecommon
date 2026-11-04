"""Henry's watch list: what a corpus cannot see.

Each entry in watchlist.yaml:

  term:      the word or phrase as it appears in the prose (required)
  kind:      sense | name | place | romani | cant | idiom | word | punctuation
  reason:    why it is listed (required)
  tag:       DOCUMENTED | REASONABLE INFERENCE | CONTESTED | UNVERIFIED (required)
  source:    where the reason comes from (optional)
  from_year: the earliest year the use is recorded, if known (optional);
             a hit is FLAG before it, BORDERLINE within the window after, and
             NOTE (still shown) after that
  match:     word (default: the word and its regular inflections) | exact |
             phrase | regex
  also:      further spellings or forms to match (optional list)
  case:      true to match capitalised forms only (names)
  corpus:    the corpus's own earliest date for the term, for reference
             (filled in by `desk watchlist --annotate`; the report always
             shows the live corpus evidence as well)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from desk.keys import form_key

TAGS = ("DOCUMENTED", "REASONABLE INFERENCE", "CONTESTED", "UNVERIFIED")


@dataclass
class Entry:
    term: str
    kind: str
    reason: str
    tag: str
    source: str = ""
    from_year: int | None = None
    match: str = "word"
    also: list = field(default_factory=list)
    case: bool = False
    corpus: str = ""
    keys: set = field(default_factory=set)
    phrase: tuple = ()
    phrases: list = field(default_factory=list)
    regex: re.Pattern | None = None

    def to_dict(self) -> dict:
        return {"term": self.term, "kind": self.kind, "reason": self.reason, "tag": self.tag,
                "source": self.source, "from_year": self.from_year, "corpus": self.corpus}


def inflections(w: str) -> set[str]:
    w = w.lower()
    out = {w, w + "s", w + "'s", w + "ed", w + "ing"}
    if w.endswith(("s", "x", "z", "ch", "sh")):
        out.add(w + "es")
    if w.endswith("e"):
        out |= {w[:-1] + "ing", w + "d"}
    if w.endswith("y") and len(w) > 2 and w[-2] not in "aeiou":
        out |= {w[:-1] + "ies", w[:-1] + "ied"}
    if len(w) >= 3 and w[-1] not in "aeiouwxy" and w[-2] in "aeiou" and w[-3] not in "aeiou":
        out |= {w + w[-1] + "ed", w + w[-1] + "ing"}
    return out


def load(path: Path) -> list[Entry]:
    path = Path(path)
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if isinstance(data, dict):
        data = data.get("entries", [])
    out = []
    for i, d in enumerate(data):
        if not isinstance(d, dict) or not d.get("term"):
            continue
        tag = str(d.get("tag", "UNVERIFIED")).upper()
        if tag not in TAGS:
            raise ValueError(f"watchlist entry {d.get('term')!r}: tag must be one of {TAGS}")
        e = Entry(term=str(d["term"]), kind=str(d.get("kind", "word")),
                  reason=str(d.get("reason", "")), tag=tag, source=str(d.get("source", "") or ""),
                  from_year=int(d["from_year"]) if d.get("from_year") else None,
                  match=str(d.get("match", "word")), also=list(d.get("also") or []),
                  case=bool(d.get("case", False)), corpus=str(d.get("corpus", "") or ""))
        words = e.term.split()
        if e.match == "regex":
            e.regex = re.compile(e.term)
        elif len(words) > 1 or e.match == "phrase":
            e.match = "phrase"
            e.phrase = tuple(form_key(w) for w in words if form_key(w))
            e.phrases = [e.phrase] + [tuple(form_key(w) for w in str(a).split() if form_key(w))
                                      for a in e.also]
        else:
            base = form_key(e.term)
            e.keys = {base} if e.match == "exact" else inflections(base)
            for a in e.also:
                e.keys.add(form_key(str(a)))
        out.append(e)
    return out


def phrases(entries: list[Entry]) -> list[str]:
    out = []
    for e in entries:
        if e.match == "phrase":
            out.extend(" ".join(p) for p in e.phrases if len(p) >= 2)
    return out
