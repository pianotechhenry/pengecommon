"""`desk check`: every word or phrase in a scene without printed attestation
before the book's year, with the evidence.  The checker reports; it never
rewrites, suggests or corrects.

Statuses for a word (configurable thresholds):
  OK          printed before the year in at least `note_min` texts - silent
  NOTE        printed before the year, but in fewer than `note_min` texts
  BORDERLINE  first printed in the year itself or within `window` years after
  FLAG        first printed later than that
  UNVERIFIED  not in the corpus at all
  WATCH       a watch-list entry with no date (its reason and tag are shown)

The status uses the earliest text with a *firm* date; an earlier text with a
conjectural or ranged date is reported and makes the tag CONTESTED.
"""
from __future__ import annotations

import datetime as _dt
import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path

from desk import paths
from desk.check import reader
from desk.check.streams import NARRATION, STREAMS, detect_style, label
from desk.check.tokens import punctuation, words
from desk.etymology import Etymology
from desk.index import KIND_FOREIGN, KIND_FORM, KIND_LEMMA, Index
from desk.keys import fold_accents, form_key
from desk.watchlist import Entry, load as load_watchlist

CAVEAT = ("Absence from the corpus is never proof. Print lags speech, often by decades, "
          "and early print is skewed to religious and learned registers: everyday, "
          "spoken, female, regional and criminal language is thinly represented, so a "
          "late first date or no date at all means only that this corpus has no printed "
          "example, not that the word was not in use.")

STATUS_RANK = {"FLAG": 0, "UNVERIFIED": 1, "BORDERLINE": 2, "NOTE": 3, "WATCH": 4, "OK": 5}

# Hesitation fillers and modern discourse markers: reported whatever the
# corpus says, because a printed form may be another word entirely.
INTERJECTIONS = {
    "erm": "hesitation filler", "um": "hesitation filler", "umm": "hesitation filler",
    "uh": "hesitation filler", "uhh": "hesitation filler", "er": "hesitation filler",
    "err": "hesitation filler", "hmm": "hesitation filler", "hmmm": "hesitation filler",
    "mm": "hesitation filler", "mmm": "hesitation filler", "huh": "interjection",
    "okay": "discourse marker", "ok": "discourse marker", "yeah": "discourse marker",
    "yep": "discourse marker", "yup": "discourse marker", "nope": "discourse marker",
    "wow": "interjection", "oops": "interjection", "uh-huh": "interjection",
    "uh-oh": "interjection", "yikes": "interjection",
}

FUNCTION_WORDS = set("""
a an the and or but nor if then than that this these those there here where when while
whilst whether which who whom whose what why how of in on at by for from to into onto upon
with within without about above below over under between among amongst through throughout
against before after since until till unto as so such not no nay yea yes all any some
each every either neither both few many much more most less least other another own same
i me my mine myself thou thee thy thine thyself he him his himself she her hers herself it
its itself we us our ours ourselves you your yours yourself yourselves ye they them their
theirs themselves one ones be am is are was were been being have has had having do does
did doing done shall should will would may might must can could ought dost doth hath art
wilt shalt canst couldst wouldst shouldst mayst mightst o oh ah alas very too also just
only even still yet ever never always often again once now then thus hence whence thence
""".split())

_VARIANT_RULES = [
    (r"isation(s?)$", r"ization\1"), (r"ization(s?)$", r"isation\1"),
    (r"ise(s|d|r|rs)?$", r"ize\1"), (r"ize(s|d|r|rs)?$", r"ise\1"),
    (r"ising$", "izing"), (r"izing$", "ising"),
    (r"yse(s|d)?$", r"yze\1"), (r"yze(s|d)?$", r"yse\1"),
    (r"([^aeiou])our(s|ed|ing|able|ably|ite|ites|ful|less)?$", r"\1or\2"),
    (r"([^aeiou])or(s|ed|ing)?$", r"\1our\2"),
    (r"([tbg])re(s|d)?$", r"\1er\2"),
    (r"ogue(s)?$", r"og\1"),
    (r"lled$", "led"), (r"lling$", "ling"), (r"ller(s?)$", r"ler\1"),
    (r"([^l])led$", r"\1lled"), (r"([^l])ling$", r"\1lling"),
    (r"ful$", "full"), (r"fil$", "fill"),
]
_OUR_STOP = {"four", "your", "hour", "flour", "pour", "sour", "tour", "dour", "our", "yours",
             "fours", "hours", "pours", "ours", "tours", "for", "nor", "or", "door", "floor",
             "poor", "moor", "major", "minor", "honor"}
_SPECIAL = {"grey": "gray", "gray": "grey", "plough": "plow", "gaol": "jail", "mould": "mold",
            "moult": "molt", "smoulder": "smolder", "whisky": "whiskey", "tyre": "tire",
            "kerb": "curb", "sceptic": "skeptic", "aluminium": "aluminum", "ageing": "aging",
            "judgement": "judgment", "connexion": "connection", "connection": "connexion"}


def variants(key: str) -> list[str]:
    out = []
    if key in _SPECIAL:
        out.append(_SPECIAL[key])
    if len(key) >= 5 and key not in _OUR_STOP:
        for pat, rep in _VARIANT_RULES:
            v = re.sub(pat, rep, key)
            if v != key:
                out.append(v)
    f = fold_accents(key)
    if f != key:
        out.append(f)
    if "-" in key:
        out.append(key.replace("-", ""))
    if key.endswith("in'"):
        out.append(key[:-1] + "g")
    if key.endswith("'d") and len(key) > 3:
        out.append(key[:-2] + "ed")
    seen, res = set(), []
    for v in out:
        if v not in seen and v != key:
            seen.add(v)
            res.append(v)
    return res


# Heads of closed compounds that period print usually wrote as two words
# ("every thing", "any one", "to morrow", "for ever", "a while").
COMPOUND_HEADS = {"a", "any", "every", "some", "no", "to", "for", "where", "there", "here",
                  "how", "what", "when", "who", "him", "her", "my", "your", "our", "them",
                  "it", "can", "in", "up", "out", "over", "under", "with", "with", "be", "all",
                  "none", "may", "by", "never", "near", "whom", "thy", "thy"}


def compound_splits(key: str) -> list[tuple[str, str]]:
    out = []
    if "-" in key or "'" in key:
        return out
    for i in range(1, min(len(key) - 2, 6) + 1):
        a, b = key[:i], key[i:]
        if a in COMPOUND_HEADS and len(b) >= 3:
            out.append((a, b))
    return out


def lemma_candidates(key: str) -> list[str]:
    w = key
    out = []
    if w.endswith("'s"):
        out.append(w[:-2])
    if w.endswith("s'"):
        out.append(w[:-1])
    if w.endswith("ies") and len(w) > 4:
        out.append(w[:-3] + "y")
    if w.endswith("es") and len(w) > 3:
        out.append(w[:-2])
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        out.append(w[:-1])
    if w.endswith("ied") and len(w) > 4:
        out.append(w[:-3] + "y")
    if w.endswith("ed") and len(w) > 4:
        out += [w[:-2], w[:-1]]
        if len(w) > 5 and w[-3] == w[-4]:
            out.append(w[:-3])
    if w.endswith("ing") and len(w) > 5:
        out += [w[:-3], w[:-3] + "e"]
        if w[-4] == w[-5]:
            out.append(w[:-4])
    if w.endswith("est") and len(w) > 5:
        out += [w[:-3], w[:-2]]
    if w.endswith("er") and len(w) > 4:
        out += [w[:-2], w[:-1]]
    if w.endswith("ly") and len(w) > 5:
        out.append(w[:-2])
    seen, res = set(), []
    for c in out:
        if c and c not in seen and c != w:
            seen.add(c)
            res.append(c)
    return res


@dataclass
class Config:
    year: int
    window: int = 15
    note_min: int = 3
    use_watchlist: bool = True
    expect_min: float = 10.0      # phrase heuristic: expected texts before the year
    phrase_min_after: int = 20    # phrase heuristic: texts in the 50 years after first print
    watchlist_path: Path | None = None
    baseline_path: Path | None = None


@dataclass
class Item:
    id: str
    type: str                     # word | phrase | punct | interjection | watch
    text: str
    key: str
    status: str
    tag: str
    reason: str = ""
    evidence: dict = field(default_factory=dict)
    watch: list = field(default_factory=list)
    occurrences: list = field(default_factory=list)
    resolved_english: bool = True


class Checker:
    def __init__(self, cfg: Config, index: Index | None = None, etym: Etymology | None = None):
        self.cfg = cfg
        self.idx = index or Index(paths.index_path())
        self.etym = etym or Etymology(paths.etymology_path())
        wl = cfg.watchlist_path or paths.watchlist_path()
        entries: list[Entry] = load_watchlist(wl) if cfg.use_watchlist else []
        # kind "accepted": words Henry has vetted (a character's name, say) - not flagged
        self.accepted: set[str] = set()
        for e in entries:
            if e.kind == "accepted":
                self.accepted |= e.keys
        self.watch: list[Entry] = [e for e in entries if e.kind != "accepted"]
        self._res: dict[str, dict] = {}

    # ------------------------------------------------------------------ dates
    def _cite(self, tid):
        t = self.idx.text(tid)
        return t.cite() if t else None

    def assess(self, rec: dict, basis: str) -> dict:
        """Status of one corpus record (an entry, n-gram, phrase or punctuation run)."""
        Y, W, N = self.cfg.year, self.cfg.window, self.cfg.note_min
        yf = self.idx.year(rec.get("first_firm"))
        ya = self.idx.year(rec.get("first_any"))
        early = [self.idx.year(t) for t in rec.get("early", [])]
        n_exact = sum(1 for y in early if y is not None and y < Y)
        decades = rec.get("decades", {})
        n_lower = sum(n for d, n in decades.items() if d + 10 <= Y)
        if early and n_exact == len(early):
            n_before = max(n_exact, n_lower)
            approx = n_before > len(early)
        elif early:
            n_before, approx = n_exact, False
        else:
            n_before = n_lower + sum(n for d, n in decades.items() if d < Y < d + 10)
            approx = True
        tag = "DOCUMENTED" if basis == "exact" else "REASONABLE INFERENCE"
        note = []
        if yf is not None and yf < Y:
            status = "OK" if n_before >= N else "NOTE"
            if status == "NOTE":
                note.append(f"printed before {Y} in {n_before} text{'s' if n_before != 1 else ''}")
        elif yf is None:
            tag = "CONTESTED"
            note.append("only in texts with conjectural or ranged dates")
            if ya is not None and ya < Y:
                status = "NOTE"
            elif ya is not None and ya <= Y + W:
                status = "BORDERLINE"
            else:
                status = "FLAG"
        else:
            status = "BORDERLINE" if yf <= Y + W else "FLAG"
            if ya is not None and ya < Y:
                tag = "CONTESTED"
                note.append(f"an earlier text with a conjectural or ranged date ({ya}) has it")
        return {
            "status": status, "tag": tag, "basis": basis, "note": "; ".join(note),
            "first_firm": self._cite(rec.get("first_firm")),
            "first_any": self._cite(rec.get("first_any")) if rec.get("first_any") != rec.get("first_firm") else None,
            "n_before": n_before, "n_before_approx": approx, "ntexts": rec.get("ntexts"),
            "decades": decades,
        }

    # ------------------------------------------------------------- resolution
    def resolve(self, word: str) -> dict:
        key = form_key(word)
        if key in self._res:
            return self._res[key]
        idx = self.idx
        cands = []
        e = idx.entry(KIND_FORM, key)
        if e:
            cands.append(("exact", key, e))
        for v in variants(key):
            ev = idx.entry(KIND_FORM, v)
            if ev:
                cands.append((f"spelling variant '{v}'", v, ev))
        if key.endswith(("'s", "s'")) and not cands:
            base = key[:-2] if key.endswith("'s") else key[:-1]
            eb = idx.entry(KIND_FORM, base)
            if eb:
                cands.append((f"possessive of '{base}'", base, eb))
        if not any(self.assess(rec, "x")["status"] == "OK" for _, _, rec in cands):
            for a_, b_ in compound_splits(key):
                ng = idx.ngram([a_, b_])
                if ng:
                    cands.append((f"printed as two words '{a_} {b_}'", f"{a_} {b_}",
                                  {**ng, "early": []}))
        parts_result = None
        if not cands and "-" in key:
            parts = [p for p in key.split("-") if p]
            ng = idx.ngram(parts) if len(parts) in (2, 3) else None
            if ng:
                cands.append((f"printed as separate words '{' '.join(parts)}'", " ".join(parts),
                              {**ng, "early": []}))
            else:
                pr = [self.resolve(p) for p in parts]
                worst = min(pr, key=lambda r: STATUS_RANK[r["status"]])
                parts_result = {**worst, "basis": "compound not printed as a unit; parts: " +
                                ", ".join(f"{p} ({r['status']})" for p, r in zip(parts, pr)),
                                "tag": "REASONABLE INFERENCE"}
                if worst["status"] == "OK":
                    parts_result["status"] = "NOTE"
        if not cands and parts_result is None:
            for lc in lemma_candidates(key):
                el = idx.entry(KIND_LEMMA, lc)
                if el:
                    cands.append((f"form not printed; lemma '{lc}'", lc, el))
                    break
        best = None
        for basis, k, rec in cands:
            a = self.assess(rec, "exact" if basis == "exact" else basis)
            a["matched"] = k
            a["entry_id"] = rec.get("id")
            a["lemma_note"] = rec.get("lemmas")
            if basis.startswith("form not printed") and a["status"] == "OK":
                a["status"] = "NOTE"
                a["note"] = (a["note"] + "; " if a["note"] else "") + "this inflected form is not printed"
            # the best evidence wins: least severe status, then earliest firm date,
            # then the exact form over a variant
            rank = (-STATUS_RANK[a["status"]], (self.idx.year(rec.get("first_firm")) or 9999),
                    0 if basis == "exact" else 1)
            if best is None or rank < best[0]:
                best = (rank, a)
        if best:
            res = best[1]
        elif parts_result is not None:
            res = parts_result
        else:
            res = {"status": "UNVERIFIED", "tag": "UNVERIFIED", "basis": "not in the corpus",
                   "note": "", "first_firm": None, "first_any": None, "n_before": 0,
                   "ntexts": 0, "decades": {}}
            fe = idx.entry(KIND_FOREIGN, key)
            if fe:
                fa = self.assess(fe, "foreign")
                res["foreign"] = {"first_firm": fa["first_firm"], "first_any": fa["first_any"],
                                  "ntexts": fe["ntexts"], "entry_id": fe["id"]}
                res["note"] = ("printed only as a foreign-language word (Latin, French, "
                               "Welsh or other), never tagged as English")
        res["key"] = key
        res["resolved_english"] = res["status"] != "UNVERIFIED" or self.etym.is_english(key)
        self._res[key] = res
        return res

    def evidence_lines(self, res: dict) -> list[dict]:
        eid = res.get("entry_id")
        if eid is None and res.get("foreign"):
            eid = res["foreign"]["entry_id"]
        return self.idx.kwic(eid) if eid is not None else []

    # --------------------------------------------------------------- phrases
    def phrase_evidence(self, keys: tuple) -> dict | None:
        text = " ".join(keys)
        rec = self.idx.phrase(text)
        if rec is None and len(keys) in (2, 3):
            rec = self.idx.ngram(list(keys))
        if rec is None:
            return None
        a = self.assess({**rec, "early": []}, "exact")
        a["source"] = rec.get("source")
        if rec.get("kwic"):
            a["kwic"] = [{**k, **(self._cite(k.get("tid")) or {})} for k in rec["kwic"]]
        return a

    def idiom_test(self, keys: tuple) -> dict | None:
        """Phrase heuristic: first printed after the window, and common enough
        afterwards that its absence before the year is unlikely to be chance."""
        rec = self.idx.ngram(list(keys))
        if rec is None:
            return None
        Y = self.cfg.year
        yf = self.idx.year(rec.get("first_firm"))
        if yf is None or yf <= Y:
            return None
        dec = rec.get("decades", {})
        after = sum(n for d, n in dec.items() if yf - 9 <= d < yf + 50)
        texts_after = self.idx.texts_between((yf // 10) * 10, (yf // 10) * 10 + 50)
        texts_before = self.idx.texts_between(Y - 50, Y)
        if texts_after <= 0 or after < self.cfg.phrase_min_after:
            return None
        expected = after / texts_after * texts_before
        if expected < self.cfg.expect_min:
            return None
        a = self.assess({**rec, "early": []}, "phrase heuristic")
        a["tag"] = "REASONABLE INFERENCE"
        a["expected_before"] = round(expected, 1)
        a["note"] = (f"printed in {after} texts in the 50 years from {yf}; at that rate about "
                     f"{expected:.0f} of the {texts_before:.0f} texts of {Y - 50}-{Y - 1} would show it, "
                     "and none does (heuristic)")
        return a

    # ------------------------------------------------------------------ main
    def check_file(self, path: Path) -> dict:
        paras = reader.read(Path(path))
        return self.check_paragraphs(paras, source=str(path))

    def check_paragraphs(self, paras: list, source: str = "") -> dict:
        cfg, idx = self.cfg, self.idx
        style = detect_style([p.text for p in paras])
        items: dict[str, Item] = {}
        out_paras = []
        romani: dict[str, dict] = {}
        accepted: dict[str, int] = {}
        stream_words = {s: 0 for s in STREAMS}

        def item(id_, **kw) -> Item:
            if id_ not in items:
                items[id_] = Item(id=id_, **kw)
            return items[id_]

        def occ(it: Item, pi: int, a: int, b: int, stream: str):
            it.occurrences.append({"para": pi, "start": a, "end": b, "stream": stream})

        for pi, p in enumerate(paras):
            lab = label(p.text, p.italic, style)
            toks = words(p.text)
            spans = []
            content = []
            for t in toks:
                stream = lab[t.start] if t.start < len(lab) else NARRATION
                stream_words[stream] += 1
                key = form_key(t.text)
                if not key:
                    continue
                res = self.resolve(t.text)
                if key in self.accepted:
                    accepted[key] = accepted.get(key, 0) + 1
                    continue
                if key in INTERJECTIONS:
                    it = item(f"i:{key}", type="interjection", text=t.text, key=key,
                              status=res["status"] if res["status"] != "OK" else "NOTE",
                              tag=("CONTESTED" if res["status"] in ("OK", "NOTE") else res["tag"]),
                              reason=INTERJECTIONS[key] + " - reported whatever the corpus shows",
                              evidence=res)
                    occ(it, pi, t.start, t.end, stream)
                    spans.append({"start": t.start, "end": t.end, "item": it.id, "stream": stream})
                elif res["status"] != "OK":
                    it = item(f"w:{key}", type="word", text=t.text, key=key, status=res["status"],
                              tag=res["tag"], reason=res.get("basis", ""), evidence=res,
                              resolved_english=res["resolved_english"])
                    occ(it, pi, t.start, t.end, stream)
                    spans.append({"start": t.start, "end": t.end, "item": it.id, "stream": stream})
                # watch list: words
                for e in self.watch:
                    if e.match in ("word", "exact") and key in e.keys:
                        if e.case and not t.capitalised:
                            continue
                        it = self._watch_item(items, e, key, res)
                        occ(it, pi, t.start, t.end, stream)
                        spans.append({"start": t.start, "end": t.end, "item": it.id, "stream": stream})
                        if e.kind in ("romani", "cant"):
                            self._romani(romani, t.text, key, pi, stream, e)
                if not res["resolved_english"]:
                    self._romani(romani, t.text, key, pi, stream, None)
                if key not in FUNCTION_WORDS and len(key) > 2 and not (t.capitalised and not t.sentence_start):
                    lemma = None
                    if res.get("lemma_note"):
                        lemma = res["lemma_note"].split(":")[0]
                    origin = self.etym.lookup(key, lemma)
                    content.append((key, origin[0] if origin else None))
            # phrases: watch list and the idiom heuristic
            seq = self._phrase_seq(p.text, toks)
            for e in self.watch:
                if e.match != "phrase":
                    continue
                for ph in e.phrases:
                    for a, b in self._find_phrase(seq, ph):
                        it = self._watch_item(items, e, " ".join(ph), None, phrase=ph)
                        stream = lab[a] if a < len(lab) else NARRATION
                        occ(it, pi, a, b, stream)
                        spans.append({"start": a, "end": b, "item": it.id, "stream": stream})
            for e in self.watch:
                if e.match == "regex" and e.regex:
                    for m in e.regex.finditer(p.text):
                        it = self._watch_item(items, e, m.group(0), None)
                        stream = lab[m.start()] if m.start() < len(lab) else NARRATION
                        occ(it, pi, m.start(), m.end(), stream)
                        spans.append({"start": m.start(), "end": m.end(), "item": it.id, "stream": stream})
            if idx.has_ngrams:
                for n in (3, 2):
                    for j in range(len(seq) - n + 1):
                        win = seq[j:j + n]
                        if any(w is None for w in win):
                            continue
                        keys = tuple(w[0] for w in win)
                        if any(self.resolve(k)["status"] != "OK" for k in keys):
                            continue
                        if all(k in FUNCTION_WORDS for k in keys):
                            continue
                        a = self.idiom_test(keys)
                        if not a:
                            continue
                        start, end = win[0][1], win[-1][2]
                        it = item(f"p:{' '.join(keys)}", type="phrase", text=p.text[start:end],
                                  key=" ".join(keys), status=a["status"], tag=a["tag"],
                                  reason="phrase first printed later than the window (heuristic)",
                                  evidence=a)
                        stream = lab[start] if start < len(lab) else NARRATION
                        occ(it, pi, start, end, stream)
                        spans.append({"start": start, "end": end, "item": it.id, "stream": stream})
            # punctuation
            for seqp, a, b in punctuation(p.text):
                rec = idx.punct(seqp)
                if rec and not rec.get("absent"):
                    ev = self.assess({**rec, "early": []}, "exact")
                    ev["kwic"] = [{**k, **(self._cite(k.get("tid")) or {})} for k in rec["kwic"]]
                    status = ev["status"] if ev["status"] != "OK" else "NOTE"
                    tag = ev["tag"]
                elif rec and rec.get("absent"):
                    ev = {"basis": "this run of ! and ? is not printed anywhere in the corpus"}
                    status, tag = "UNVERIFIED", "UNVERIFIED"
                else:
                    ev = {"basis": "punctuation scan not built (desk build --stage scan)"}
                    status, tag = "NOTE", "UNVERIFIED"
                it = item(f"x:{seqp}", type="punct", text=seqp, key=seqp, status=status, tag=tag,
                          reason="modern-looking punctuation - reported whatever the corpus shows",
                          evidence=ev)
                stream = lab[a] if a < len(lab) else NARRATION
                occ(it, pi, a, b, stream)
                spans.append({"start": a, "end": b, "item": it.id, "stream": stream})
            out_paras.append({"i": pi, "text": p.text, "italic": p.italic, "heading": p.heading,
                              "spans": spans, "stream_ranges": _ranges(lab),
                              "latinate": _share(content)})
        # evidence lines for everything reported
        for it in items.values():
            if it.type in ("word", "interjection") and "kwic" not in it.evidence:
                it.evidence["kwic"] = self.evidence_lines(it.evidence)
        result = {
            "tool": "commons-desk check",
            "source": source,
            "generated": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "settings": {"year": cfg.year, "window": cfg.window, "note_min": cfg.note_min,
                         "watchlist": cfg.use_watchlist, "phrase_expect_min": cfg.expect_min,
                         "quote_style": style},
            "caveat": CAVEAT,
            "corpus": self._corpus_summary(),
            "paragraphs": out_paras,
            "items": {k: v.__dict__ for k, v in sorted(
                items.items(), key=lambda kv: (STATUS_RANK.get(kv[1].status, 9), kv[0]))},
            "romani": sorted(romani.values(), key=lambda r: r["token"].lower()),
            "accepted": accepted,
            "streams_words": stream_words,
        }
        result["summary"] = _summary(result)
        result["latinate"] = self._latinate_summary(out_paras)
        return result

    # --------------------------------------------------------------- helpers
    def _watch_item(self, items, e: Entry, key: str, res: dict | None, phrase: tuple = ()) -> Item:
        id_ = f"wl:{e.term}"
        if id_ in items:
            return items[id_]
        Y, W = self.cfg.year, self.cfg.window
        if e.from_year is None:
            status = "WATCH"
        elif Y < e.from_year:
            status = "FLAG"
        elif Y <= e.from_year + W:
            status = "BORDERLINE"
        else:
            status = "NOTE"
        corpus = None
        if phrase:
            corpus = self.phrase_evidence(phrase)
        elif res is not None:
            corpus = res
        it = Item(id=id_, type="watch", text=e.term, key=key, status=status, tag=e.tag,
                  reason=e.reason + (f" ({e.source})" if e.source else ""),
                  evidence=corpus or {"basis": "no corpus evidence for this phrase"},
                  watch=[e.to_dict()])
        if corpus and corpus.get("entry_id") is not None and "kwic" not in corpus:
            corpus["kwic"] = self.evidence_lines(corpus)
        items[id_] = it
        return it

    def _romani(self, romani: dict, text: str, key: str, pi: int, stream: str, e: Entry | None):
        r = romani.setdefault(key, {"token": text, "key": key, "count": 0, "paragraphs": [],
                                    "streams": [], "watch": None})
        r["count"] += 1
        if pi + 1 not in r["paragraphs"]:
            r["paragraphs"].append(pi + 1)
        if stream not in r["streams"]:
            r["streams"].append(stream)
        if e is not None:
            r["watch"] = {"reason": e.reason + (f" ({e.source})" if e.source else ""), "tag": e.tag,
                          "kind": e.kind}
        res = self._res.get(key)
        if res is not None:
            r["corpus"] = (f"{res['status']}: " + (res["note"] or res.get("basis", "")))

    @staticmethod
    def _phrase_seq(text: str, toks) -> list:
        """Word keys with positions; None where punctuation intervenes."""
        seq = []
        last_end = None
        for t in toks:
            if last_end is not None:
                gap = text[last_end:t.start]
                if re.search(r"[^\s\-–—]", gap.replace("’", "").replace("'", "")):
                    seq.append(None)
            seq.append((form_key(t.text), t.start, t.end))
            last_end = t.end
        return seq

    @staticmethod
    def _find_phrase(seq, ph: tuple):
        n = len(ph)
        for j in range(len(seq) - n + 1):
            win = seq[j:j + n]
            if any(w is None for w in win):
                continue
            if tuple(w[0] for w in win) == ph:
                yield win[0][1], win[-1][2]

    def _corpus_summary(self) -> dict:
        Y = self.cfg.year
        nt, nw = self.idx.corpus_before(Y)
        tt, tw = self.idx.corpus_total()
        return {"texts_before": nt, "words_before": nw, "texts_total": tt, "words_total": tw,
                "built": self.idx.info.get("built", ""), "holdout": len(self.idx.holdout),
                "ngram_min_df": self.idx.info.get("ngram_min_df"),
                "phrase_scan": bool(self.idx.has_phrases), "punct_scan": bool(self.idx.has_punct)}

    def _latinate_summary(self, paras) -> dict:
        shares = [p["latinate"]["share"] for p in paras if p["latinate"]["share"] is not None]
        out = {"label": ("Heuristic. Share of content words whose Wiktionary etymology names "
                         "Latin or French as the language they entered English from. A register "
                         "indicator, not a period test."),
               "mean": round(statistics.mean(shares), 3) if shares else None}
        bpath = self.cfg.baseline_path or paths.baseline_path()
        if Path(bpath).exists():
            bp = reader.read(Path(bpath))
            bs = []
            for p in bp:
                content = []
                for t in words(p.text):
                    key = form_key(t.text)
                    if key and key not in FUNCTION_WORDS and len(key) > 2 and not (
                            t.capitalised and not t.sentence_start):
                        o = self.etym.lookup(key)
                        content.append((key, o[0] if o else None))
                s = _share(content)["share"]
                if s is not None:
                    bs.append(s)
            if bs:
                mu = statistics.mean(bs)
                sd = statistics.pstdev(bs) if len(bs) > 1 else 0.0
                out["baseline"] = {"file": str(bpath), "paragraphs": len(bs), "mean": round(mu, 3),
                                   "sd": round(sd, 3)}
                for p in paras:
                    s = p["latinate"]["share"]
                    if s is not None:
                        p["latinate"]["vs_baseline"] = round(s - mu, 3)
                        if sd > 0:
                            p["latinate"]["z"] = round((s - mu) / sd, 2)
        else:
            out["baseline"] = None
        return out


def _ranges(lab: list[str]) -> list:
    out = []
    if not lab:
        return out
    cur, start = lab[0], 0
    for i, s in enumerate(lab[1:], 1):
        if s != cur:
            out.append([start, i, cur])
            cur, start = s, i
    out.append([start, len(lab), cur])
    return out


def _share(content: list) -> dict:
    known = [c for _, c in content if c and c != "unknown"]
    lf = sum(1 for c in known if c in ("latin", "french"))
    return {"content_words": len(content), "classified": len(known), "latin_french": lf,
            "share": round(lf / len(known), 3) if len(known) >= 5 else None}


def _summary(result: dict) -> dict:
    statuses = ["FLAG", "BORDERLINE", "NOTE", "UNVERIFIED", "WATCH"]
    table = {s: {st: 0 for st in STREAMS} for s in statuses}
    types = {s: {st: 0 for st in STREAMS} for s in statuses}
    per_type = {}
    for it in result["items"].values():
        st = it["status"]
        if st not in table:
            continue
        seen = set()
        for o in it["occurrences"]:
            table[st][o["stream"]] += 1
            seen.add(o["stream"])
        for s in seen:
            types[st][s] += 1
        per_type.setdefault(it["type"], 0)
        per_type[it["type"]] += 1
    return {"occurrences": table, "types": types, "by_kind": per_type,
            "romani_tokens": len(result["romani"])}
