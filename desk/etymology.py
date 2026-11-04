"""Word origins for the Latin/French-share heuristic, from Wiktionary.

The class of a word is the language it entered English from, read from the
first step of its Wiktionary etymology that is not an earlier stage of
English: "From Middle English mercy, from Anglo-Norman merci, from Latin
merces" -> french.  Consequences worth knowing:

* a word borrowed into Old English (cheese, street, table) is native here;
* a word formed in English ("structure + -al") takes the class of its first
  element, followed recursively;
* "Onomatopoeic" / "imitative" counts as native; anything unread is unknown
  and is left out of the share.

Two builders: the official kaikki.org Wiktextract JSONL (structured
etymology templates, used when present) and the kaikki-derived extract used in
this build (etymology as text only).
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

CLASSES = ("native", "norse", "germanic", "french", "latin", "greek", "romance",
           "celtic", "other", "unknown")

LANGS = [
    # (name as written in Wiktionary, class or None for a stage of English)
    ("Early Modern English", None), ("Middle English", None), ("Modern English", None),
    ("Old English", "native"), ("Anglian Old English", "native"),
    ("Proto-West Germanic", "native"), ("Proto-Germanic", "native"),
    ("Old Norse", "norse"), ("Old Danish", "norse"), ("Old Swedish", "norse"),
    ("Danish", "norse"), ("Norwegian", "norse"), ("Swedish", "norse"), ("Icelandic", "norse"),
    ("Middle Dutch", "germanic"), ("Dutch", "germanic"), ("Middle Low German", "germanic"),
    ("Low German", "germanic"), ("Old High German", "germanic"), ("Middle High German", "germanic"),
    ("German", "germanic"), ("Old Frisian", "germanic"), ("Frankish", "germanic"),
    ("Old Saxon", "germanic"), ("Flemish", "germanic"), ("Yiddish", "germanic"),
    ("Anglo-Norman", "french"), ("Anglo-French", "french"), ("Old Northern French", "french"),
    ("Old French", "french"), ("Middle French", "french"), ("Norman", "french"),
    ("Picard", "french"), ("French", "french"),
    ("Vulgar Latin", "latin"), ("Late Latin", "latin"), ("Medieval Latin", "latin"),
    ("Ecclesiastical Latin", "latin"), ("New Latin", "latin"), ("Classical Latin", "latin"),
    ("Old Latin", "latin"), ("Latin", "latin"),
    ("Ancient Greek", "greek"), ("Byzantine Greek", "greek"), ("Koine Greek", "greek"),
    ("Greek", "greek"),
    ("Italian", "romance"), ("Spanish", "romance"), ("Portuguese", "romance"),
    ("Old Occitan", "romance"), ("Occitan", "romance"), ("Provençal", "romance"),
    ("Catalan", "romance"),
    ("Old Irish", "celtic"), ("Middle Irish", "celtic"), ("Irish", "celtic"),
    ("Scottish Gaelic", "celtic"), ("Welsh", "celtic"), ("Middle Welsh", "celtic"),
    ("Cornish", "celtic"), ("Breton", "celtic"), ("Gaulish", "celtic"), ("Manx", "celtic"),
    ("Angloromani", "other"), ("Romani", "other"), ("Arabic", "other"), ("Persian", "other"),
    ("Hebrew", "other"), ("Turkish", "other"), ("Hindi", "other"), ("Sanskrit", "other"),
    ("Hungarian", "other"), ("Malay", "other"), ("Nahuatl", "other"), ("Chinese", "other"),
    ("Japanese", "other"), ("Russian", "other"), ("Polish", "other"), ("Czech", "other"),
    ("Scots", None),
]
_LANG_RE = re.compile("|".join(re.escape(n) for n, _ in sorted(LANGS, key=lambda x: -len(x[0]))))
_LANG_CLASS = dict(LANGS)

# Wiktionary language codes used in etymology templates (kaikki JSONL)
CODES = {
    "enm": None, "en": None, "ang": "native", "gmw-pro": "native", "gem-pro": "native",
    "non": "norse", "da": "norse", "sv": "norse", "no": "norse", "nb": "norse", "is": "norse",
    "dum": "germanic", "nl": "germanic", "gml": "germanic", "nds": "germanic",
    "goh": "germanic", "gmh": "germanic", "de": "germanic", "ofs": "germanic", "frk": "germanic",
    "fro": "french", "xno": "french", "frm": "french", "fr": "french", "fro-nor": "french",
    "la": "latin", "la-lat": "latin", "la-vul": "latin", "la-med": "latin", "la-new": "latin",
    "la-ecc": "latin", "la-cla": "latin", "LL.": "latin", "ML.": "latin", "NL.": "latin",
    "VL.": "latin", "grc": "greek", "el": "greek", "gkm": "greek",
    "it": "romance", "es": "romance", "pt": "romance", "oc": "romance", "pro": "romance",
    "ca": "romance", "sga": "celtic", "ga": "celtic", "gd": "celtic", "cy": "celtic",
    "kw": "celtic", "br": "celtic", "rom": "other", "rme": "other", "ar": "other",
    "fa": "other", "he": "other", "tr": "other", "hi": "other", "sa": "other", "hu": "other",
}

_PROSE_START = re.compile(
    r"(?:^|\n)(?=(?:From|Inherited from|Borrowed from|Learned borrowing from|Semi-learned borrowing from|"
    r"Unadapted borrowing from|Derived from|Clipping of|Back-formation from|Probably from|Possibly from|"
    r"Perhaps from|Ultimately from|Onomatopoeic|Imitative|Of uncertain origin|Uncertain|The noun|The verb|"
    r"A respelling|Blend of|Short for|Abbreviation of|Variant of|Alteration of|Contraction of|"
    r"First attested|Deverbal from|From earlier|From a |By surface|Named after|Coined by))")
_COMPOUND = re.compile(r"^(?:From|Morphologically|By surface analysis,?)\s+([A-Za-z'-]+)\s*\+\s*[-A-Za-z]+")


def _prose(ety: str) -> str:
    """The prose part of an entry, skipping 'PIE word' and 'Etymology tree' blocks."""
    m = _PROSE_START.search(ety)
    if m:
        return ety[m.start():].lstrip("\n")
    if ety.startswith(("Etymology tree", "PIE word")):
        return ""
    return ety


def classify_text(ety: str, lookup=None, depth: int = 0) -> tuple[str, str]:
    """(class, chain) from an etymology paragraph."""
    if not ety:
        return "unknown", ""
    prose = _prose(ety)
    if not prose:
        # tree only: the last named ancestor before the English line
        tree = ety[ety.find("Etymology tree"):] if "Etymology tree" in ety else ety
        lines = [ln for ln in tree.split("\n")[1:] if ln.strip()]
        for ln in reversed(lines):
            m = _LANG_RE.match(ln)
            if m and _LANG_CLASS.get(m.group(0)):
                return _LANG_CLASS[m.group(0)], m.group(0) + " (tree)"
        return "unknown", ""
    head = prose.split("\n")[0]
    low = head.lower()
    if low.startswith(("onomatopoeic", "imitative")):
        return "native", "imitative"
    m = _COMPOUND.match(head)
    if m and lookup is not None and depth < 3:
        base = m.group(1).lower()
        sub = lookup(base, depth + 1)
        if sub and sub[0] != "unknown":
            return sub[0], f"{base} + … ({sub[1]})"
    # first language that is not a stage of English, in order of mention;
    # stop reading at "Displaced", "Cognate", "Compare", "Doublet" (not the chain)
    cut = re.split(r"\b(?:Displaced|Cognate|Compare|Doublet|Related to|See also|Distantly)", head)[0]
    chain = []
    for mm in _LANG_RE.finditer(cut):
        name = mm.group(0)
        cls = _LANG_CLASS.get(name)
        chain.append(name)
        if cls:
            return cls, " < ".join(chain)
    if "respelling" in low or "abbreviation" in low or "initialism" in low:
        return "other", head[:40]
    return "unknown", " < ".join(chain)


def classify_templates(templates: list[dict]) -> tuple[str, str] | None:
    for t in templates or []:
        if t.get("name") in ("inh", "inh+", "bor", "bor+", "der", "der+", "lbor", "slbor",
                             "ubor", "obor", "lbor+"):
            code = (t.get("args") or {}).get("2", "")
            if code in CODES:
                cls = CODES[code]
                if cls:
                    return cls, f"{t['name']}:{code}"
    return None


SCHEMA = "CREATE TABLE origin(word TEXT PRIMARY KEY, class TEXT, chain TEXT, source TEXT)"


def build_from_extract(src: Path, out: Path) -> int:
    """The kaikki-derived extract: entry(headword, data JSON with 'ety')."""
    con = sqlite3.connect(src)
    raw = {}
    for hw, data in con.execute("SELECT headword, data FROM entry"):
        try:
            ety = json.loads(data).get("ety") or ""
        except ValueError:
            continue
        raw[hw.lower()] = ety
    con.close()
    memo: dict[str, tuple[str, str]] = {}

    def lookup(w: str, depth: int = 0):
        if w in memo:
            return memo[w]
        if w not in raw:
            return None
        memo[w] = ("unknown", "")           # guard against cycles
        memo[w] = classify_text(raw[w], lookup, depth)
        return memo[w]

    rows = []
    for w in raw:
        cls, chain = lookup(w)
        rows.append((w, cls, chain, "kaikki-derived extract (thymesis-dictionary kaikki-en-v1)"))
    return _write(out, rows)


def build_from_kaikki(jsonl: Path, out: Path) -> int:
    """Official kaikki.org English JSONL (one JSON object per line)."""
    raw_text, tmpl = {}, {}
    with open(jsonl, encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("lang_code") not in (None, "en"):
                continue
            w = (e.get("word") or "").lower()
            if not w:
                continue
            c = classify_templates(e.get("etymology_templates"))
            if c and w not in tmpl:
                tmpl[w] = c
            if e.get("etymology_text") and w not in raw_text:
                raw_text[w] = e["etymology_text"]
    memo: dict[str, tuple[str, str]] = {}

    def lookup(w: str, depth: int = 0):
        if w in memo:
            return memo[w]
        if w in tmpl:
            memo[w] = tmpl[w]
            return memo[w]
        if w not in raw_text:
            return None
        memo[w] = ("unknown", "")
        memo[w] = classify_text(raw_text[w], lookup, depth)
        return memo[w]

    rows = []
    for w in set(raw_text) | set(tmpl):
        cls, chain = lookup(w)
        rows.append((w, cls, chain, "kaikki.org Wiktextract English JSONL"))
    return _write(out, rows)


def _write(out: Path, rows) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    con = sqlite3.connect(out)
    con.execute(SCHEMA)
    con.executemany("INSERT OR IGNORE INTO origin VALUES (?,?,?,?)", rows)
    con.commit()
    n = con.execute("SELECT count(*) FROM origin").fetchone()[0]
    con.close()
    return n


class Etymology:
    def __init__(self, path: Path):
        self.ok = Path(path).exists()
        self.con = sqlite3.connect(f"file:{path}?mode=ro", uri=True) if self.ok else None
        self._cache: dict[str, tuple | None] = {}

    def lookup(self, word: str, lemma: str | None = None):
        if not self.ok:
            return None
        for w in (word.lower(), (lemma or "").lower()):
            if not w:
                continue
            if w in self._cache:
                if self._cache[w]:
                    return self._cache[w]
                continue
            r = self.con.execute("SELECT class, chain FROM origin WHERE word=?", (w,)).fetchone()
            self._cache[w] = r
            if r:
                return r
        return None
