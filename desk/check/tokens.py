"""Tokenise Henry's modern-spelling prose.

A word keeps its internal apostrophes and hyphens ("that's", "to-morrow").
A leading apostrophe is kept for aphetic forms ("’tis", "’em"); a trailing
one for elisions ("goin’", "o’", "th’") and plural possessives.  A left
single quotation mark (‘) is never part of a word.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

L = r"[^\W\d_]"
_WORD = re.compile(
    rf"(?P<lead>[’'])?(?P<core>{L}+(?:[’']{L}+)*(?:-{L}+(?:[’']{L}+)*)*)(?P<trail>[’'](?!{L}))?"
)
_PUNCT = re.compile(r"[!?]{2,}")

APHETIC = {"tis", "twas", "twere", "twill", "twould", "em", "gainst", "tween", "twixt",
           "neath", "til", "mongst", "midst", "cause", "round", "bout", "prentice",
           "scape", "sblood", "slid", "sdeath", "zounds", "t", "s", "ll", "d"}
ELISION_END = re.compile(r"(in|o|th|an|i|wi|ha|gi|ta|fro)$", re.I)


@dataclass
class Token:
    text: str          # as written (apostrophes normalised to ’ kept as typed)
    start: int
    end: int
    sentence_start: bool
    capitalised: bool


def words(text: str) -> list[Token]:
    out = []
    for m in _WORD.finditer(text):
        core = m.group("core")
        start, end = m.start("core"), m.end("core")
        lead, trail = m.group("lead"), m.group("trail")
        if lead:
            prev = text[m.start() - 1] if m.start() else " "
            base = core.lower().replace("’", "'").split("'")[0]
            if not prev.isalpha() and (lead == "’" or base in APHETIC):
                start = m.start()
        if trail:
            if ELISION_END.search(core) or core.lower().endswith("s"):
                end = m.end()
        before = text[:start].rstrip(" \t‘“\"'(—–-")
        sentence_start = (not before) or before[-1] in ".!?…:"
        tok = text[start:end]
        first = next((ch for ch in tok if ch.isalpha()), "")
        out.append(Token(tok, start, end, sentence_start, first.isupper()))
    return out


def punctuation(text: str) -> list[tuple[str, int, int]]:
    return [(m.group(0), m.start(), m.end()) for m in _PUNCT.finditer(text)]
