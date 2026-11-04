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
    "enm": None, "en": None, "sco": "native", "ang": "native", "gmw-pro": "native", "gem-pro": "native",
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


_SRC_TEMPLATES = {"inh", "inh+", "inh-lite", "bor", "bor+", "lbor", "lbor+", "slbor", "ubor",
                  "obor", "der", "der+", "der-lite", "uder", "calque", "cal", "psm", "sl"}
_DERIV_TEMPLATES = {"af", "affix", "suffix", "prefix", "confix", "compound", "com", "blend"}


def code_class(code: str) -> str | None:
    """Class for a Wiktionary language code; None for a stage of English."""
    if code in CODES:
        return CODES[code]
    if code.startswith("la-") or code in ("itc-pro",):
        return "latin"
    if code.startswith("fr") or code.startswith("roa-"):
        return "french" if code.startswith("fr") else "romance"
    if code.startswith("gem") or code.startswith("gmw") or code == "ine-pro":
        return "native"
    if code.startswith("gmq"):
        return "norse"
    if code.startswith(("cel", "sga", "mga", "wlm", "owl")):
        return "celtic"
    return "other" if code else "unknown"


def compact_templates(templates: list[dict]) -> list[tuple]:
    out = []
    for t in templates or []:
        name = t.get("name") or ""
        if name not in _SRC_TEMPLATES and name not in _DERIV_TEMPLATES and name != "etyl":
            continue
        args = t.get("args") or {}
        parts = [str(args[k]) for k in sorted((k for k in args if k.isdigit()), key=int)]
        out.append((name, tuple(parts)))
    return out


def classify_templates(templates: list[tuple], lookup=None, depth: int = 0):
    """Class from Wiktextract etymology templates, in order of appearance.

    The first template naming a source language other than a stage of
    English decides; an affix/compound template defers to its base word.
    """
    for name, parts in templates:
        if name in _DERIV_TEMPLATES:
            if not parts or parts[0] != "en":
                continue
            rest = list(parts[1:])
            if name == "prefix":
                base = rest[1] if len(rest) > 1 else None
            elif name == "suffix":
                base = rest[0] if rest else None
            else:
                base = next((x for x in rest if x and not x.startswith("-") and not x.endswith("-")), None)
            if base and lookup is not None and depth < 3:
                sub = lookup(base.lower(), depth + 1)
                if sub and sub[0] != "unknown":
                    return sub[0], f"{base} + … ({sub[1]})"
            continue
        if name == "etyl":
            code = parts[0] if parts else ""
        else:
            if len(parts) < 2 or parts[0] != "en":
                continue
            code = parts[1]
        cls = code_class(code)
        if cls is None:
            continue
        return cls, f"{name}:{code}"
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
    return _write(out, rows, set(raw))


def build_from_kaikki(src, out: Path) -> int:
    """Official kaikki.org English JSONL, one JSON object per line.

    `src` is a path, or "-" to read a stream (e.g. curl ... | desk build
    --stage etymology --kaikki -), so the 3.4 GB file need not be stored.
    Also records every English headword and inflected form in a lexicon
    table, which the checker uses to tell an English word from an
    unresolved one.
    """
    import io
    import sys
    if hasattr(src, "read"):
        f = src
    elif str(src) == "-":
        f = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
    else:
        f = open(src, encoding="utf-8")
    tmpl: dict[str, list] = {}
    text: dict[str, str] = {}
    lex: dict[str, set] = {}          # form -> headwords it belongs to (proper names excluded)
    n = 0
    with f:
        for line in f:
            n += 1
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("lang_code", "en") != "en":
                continue
            w = (e.get("word") or "").strip()
            if not w:
                continue
            lw = w.lower()
            if e.get("pos") != "name":
                if " " not in lw:
                    lex.setdefault(lw, set()).add(lw)
                for fm in e.get("forms") or []:
                    ff = (fm.get("form") or "").strip().lower()
                    if ff and " " not in ff and len(ff) < 40:
                        lex.setdefault(ff, set()).add(lw)
            et = e.get("etymology_templates")
            if et and lw not in tmpl:
                ct = compact_templates(et)
                if ct:
                    tmpl[lw] = ct
            if e.get("etymology_text") and lw not in text:
                text[lw] = e["etymology_text"]
    memo: dict[str, tuple[str, str]] = {}

    def lookup(word: str, depth: int = 0):
        if word in memo:
            return memo[word]
        if word not in tmpl and word not in text:
            return None
        memo[word] = ("unknown", "")
        r = classify_templates(tmpl.get(word, []), lookup, depth)
        if r is None:
            r = classify_text(text.get(word, ""), lookup, depth)
        memo[word] = r
        return r

    rows = []
    for word in set(tmpl) | set(text):
        cls, chain = lookup(word)
        rows.append((word, cls, chain, "kaikki.org Wiktextract English JSONL"))
    count = _write(out, rows, lex)
    print(f"read {n} entries; {count} words classified; lexicon {len(lex)} forms (proper names excluded)")
    return count


def _write(out: Path, rows, lex: set | None = None) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(out) + ".tmp")
    if tmp.exists():
        tmp.unlink()
    con = sqlite3.connect(tmp)
    con.execute(SCHEMA)
    con.execute("CREATE TABLE lexicon(word TEXT, base TEXT, PRIMARY KEY (word, base)) WITHOUT ROWID")
    con.executemany("INSERT OR IGNORE INTO origin VALUES (?,?,?,?)", rows)
    if isinstance(lex, dict):
        con.executemany("INSERT OR IGNORE INTO lexicon VALUES (?,?)",
                        ((w, b) for w, bases in lex.items() for b in bases))
    else:
        con.executemany("INSERT OR IGNORE INTO lexicon VALUES (?,?)",
                        ((w, w) for w in (set(lex or ()) | {r[0] for r in rows})))
    con.commit()
    n = con.execute("SELECT count(*) FROM origin").fetchone()[0]
    con.close()
    tmp.replace(out)
    return n


class Etymology:
    def __init__(self, path: Path):
        self.ok = Path(path).exists()
        self.con = sqlite3.connect(f"file:{path}?mode=ro", uri=True) if self.ok else None
        self._cache: dict[str, tuple | None] = {}
        self._lex: dict[str, bool] = {}
        self.source = ""
        if self.ok:
            r = self.con.execute("SELECT source FROM origin LIMIT 1").fetchone()
            self.source = r[0] if r else ""
            self.has_lexicon = bool(self.con.execute(
                "SELECT 1 FROM sqlite_master WHERE name='lexicon'").fetchone())
            cols = {r[1] for r in self.con.execute("PRAGMA table_info(lexicon)")} if self.has_lexicon else set()
            self._lex_bases = "base" in cols
        else:
            self.has_lexicon = False
            self._lex_bases = False

    def is_english(self, word: str) -> bool:
        """Is this an English word in Wiktionary's sense: a headword or inflected
        form of an entry that is not a proper name and whose etymology names a
        source other than "other" (so Angloromani 'cosh', entries with no
        etymology such as 'kushti', and stray homographs such as Khmer 'sar'
        are not counted as English)?"""
        if not self.ok:
            return False
        w = word.lower().replace("’", "'")
        if w in self._lex:
            return self._lex[w]
        if self.has_lexicon and self._lex_bases:
            bases = [b for (b,) in self.con.execute("SELECT base FROM lexicon WHERE word=?", (w,))]
        elif self.has_lexicon:
            bases = [w] if self.con.execute("SELECT 1 FROM lexicon WHERE word=?", (w,)).fetchone() else []
        else:
            bases = [w] if self.con.execute("SELECT 1 FROM origin WHERE word=?", (w,)).fetchone() else []
        ok = False
        for b in bases:
            r = self.con.execute("SELECT class FROM origin WHERE word=?", (b,)).fetchone()
            # an entry with no etymology at all is not taken as English either:
            # for the Romani/cant stream, listing too much is the safer error
            if r is not None and r[0] != "other":
                ok = True
                break
        self._lex[w] = ok
        return ok

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


if __name__ == "__main__":
    import sys
    from desk.paths import etymology_path
    if len(sys.argv) > 1 and sys.argv[1] == "kaikki":
        build_from_kaikki(sys.argv[2] if len(sys.argv) > 2 else "-",
                          Path(sys.argv[3]) if len(sys.argv) > 3 else etymology_path())
