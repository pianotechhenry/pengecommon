#!/usr/bin/env python3
"""Etymology helper for the Commons Series database.

  python3 tools/etym.py check WORD [WORD ...]           Wiktionary, English section
  python3 tools/etym.py check --lang all kushti          every language section (Romani etc.)
  python3 tools/etym.py check --lang German Meiler       one named section
  python3 tools/etym.py duden Meiler_Reaktor Forst       Duden Herkunft (use the URL slug)
  python3 tools/etym.py export rows.json                  rebuild exports/ from a Notion rows dump
  python3 tools/etym.py lint rows.json                    check a rows dump against the rules in CLAUDE.md

Needs: python3, beautifulsoup4, lxml, curl. Network: en.wiktionary.org, www.duden.de.
Etymonline sits behind a Cloudflare bot check and cannot be fetched from a cloud
session; check it by hand in a browser. Never fill a gap from memory (see CLAUDE.md).
Raw pages are cached in .cache/ so reruns are free and polite.
"""
import csv, json, pathlib, re, subprocess, sys, time, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache"
UA = ("CommonsSeriesEtymologyLog/1.1 (author's research database; low-rate, cached; "
      "github.com/pianotechhenry/pengecommon)")
POS = {"Noun", "Verb", "Adjective", "Proper noun", "Adverb", "Interjection", "Pronoun",
       "Suffix", "Prefix", "Phrase", "Preposition", "Conjunction", "Determiner"}


def _clean(s):
    return re.sub(r"\s+", " ", re.sub(r"\[edit\]", "", s)).strip()


def _get(url, cache_name, sleep=1.5):
    CACHE.mkdir(exist_ok=True)
    f = CACHE / cache_name
    if f.exists() and f.stat().st_size > 1000:
        return f.read_text(), "cached"
    for attempt in range(3):
        r = subprocess.run(["curl", "-sS", "-L", "--max-time", "40", "-A", UA,
                            "-w", "\n%{http_code}", url], capture_output=True, text=True)
        body, _, code = r.stdout.rpartition("\n")
        if code == "200":
            f.write_text(body)
            time.sleep(sleep)
            return body, code
        if code == "404":
            return None, code
        time.sleep(10 * (attempt + 1))
    return None, code


def wiktionary(word, lang="English"):
    from bs4 import BeautifulSoup
    url = "https://en.wiktionary.org/wiki/" + urllib.parse.quote(word.replace(" ", "_"))
    html, code = _get(url, "wikt_" + word.replace("/", "_") + ".html")
    out = [f"## {word}  {url}"]
    if html is None:
        return "\n".join(out + [f"   (no page: HTTP {code})"])
    soup = BeautifulSoup(html, "lxml")
    root = soup.find("div", class_="mw-parser-output") or soup
    seen = []
    for h2 in root.find_all("h2"):
        name = _clean(h2.get_text())
        if not name:
            continue
        seen.append(name)
        if lang != "all" and name != lang:
            continue
        out.append(f"[{name}]  {url}#{urllib.parse.quote(name)}")
        node = h2.parent if "mw-heading" in (h2.parent.get("class") or []) else h2
        cur, in_ety = node.next_sibling, False
        while cur is not None:
            nm = getattr(cur, "name", None)
            if nm == "div" and "mw-heading" in (cur.get("class") or []):
                hd = cur.find(["h2", "h3", "h4", "h5"])
                if hd is not None and hd.name == "h2":
                    break
                t = _clean(hd.get_text()) if hd is not None else ""
                in_ety = t.startswith("Etymology")
                if in_ety:
                    out.append(f"  {t}")
                elif t in POS:
                    ol = cur.find_next_sibling("ol")
                    li = ol.find("li") if ol else None
                    if li:
                        out.append(f"    {t}: " + _clean(li.get_text(" "))[:200])
            elif nm in ("p", "ul", "dl") and in_ety:
                t = _clean(cur.get_text(" "))
                if t:
                    out.append("    " + t[:900])
            cur = cur.next_sibling
    if lang != "all" and lang not in seen:
        out.append(f"   (no {lang} section; page has: {', '.join(seen[:10])})")
    return "\n".join(out)


def duden(slug):
    from bs4 import BeautifulSoup
    url = "https://www.duden.de/rechtschreibung/" + urllib.parse.quote(slug)
    html, code = _get(url, "duden_" + slug + ".html", sleep=2)
    out = [f"## {slug}  {url}"]
    if html is None:
        return "\n".join(out + [f"   (no page: HTTP {code}; try https://www.duden.de/suchen/dudenonline/{slug})"])
    soup = BeautifulSoup(html, "lxml")
    for sec in ("herkunft", "bedeutung", "bedeutungen"):
        d = soup.find(id=sec)
        if d:
            out.append(f"   [{sec}] " + _clean(d.get_text(" "))[:700])
    return "\n".join(out)


FIELDS = ["Word", "Status", "Note", "First recorded", "Source", "Checked", "Languages",
          "Use in", "Field guide", "Found in", "Added by", "Etymology", "url"]


def _val(row, key):
    v = row.get(key, "")
    if key == "Checked":
        v = row.get("date:Checked:start", v) or ""
    if isinstance(v, str) and v.startswith("["):
        try:
            v = json.loads(v)
        except ValueError:
            pass
    if isinstance(v, list):
        v = "; ".join(v)
    if v == "__YES__":
        v = "yes"
    if v in ("__NO__", None):
        v = ""
    return str(v)


def export(rows_json):
    rows = json.loads(pathlib.Path(rows_json).read_text())
    if isinstance(rows, dict):
        rows = rows.get("results", rows.get("rows", []))
    rows.sort(key=lambda r: _val(r, "Word").lower())
    ex = ROOT / "exports"
    ex.mkdir(exist_ok=True)
    with open(ex / "etymology.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(FIELDS)
        for r in rows:
            w.writerow([_val(r, k) for k in FIELDS])

    def md(title, intro, pick):
        lines = [f"# {title}", "", intro, ""]
        for r in rows:
            if pick(r):
                fr = _val(r, "First recorded")
                lines.append(f"**{_val(r, 'Word')}** ({_val(r, 'Status')}{', ' + fr if fr else ''})  ")
                lines.append(_val(r, "Note") + "  ")
                src = _val(r, "Source")
                lines.append(f"[source]({src})" if src else "_no source yet_")
                lines.append("")
        return "\n".join(lines)

    (ex / "field-guide.md").write_text(md(
        "Field guide: words worth telling",
        "Rows ticked *Field guide* in Notion. Debunkings included. Generated by tools/etym.py.",
        lambda r: _val(r, "Field guide") == "yes"))
    (ex / "debunked.md").write_text(md(
        "Debunked: claims the dictionaries contradict",
        "Rows marked FALSE. Keep them: knowing what not to say is half the job.",
        lambda r: _val(r, "Status") == "FALSE"))
    books = ["1589", "1689", "1789", "1889", "1989", "2089", "Tour", "Essays"]
    lines = ["# Words by book", "",
             "From the *Use in* tags. A tag means the word is useful there, not that it is",
             "cleared for the period: read the status and note. Romani words carry no tag;",
             "see consultant.md.", ""]
    lines += ["Jump to: " + " · ".join(f"[{b}](#{b.lower()})" for b in books), ""]
    for b in books:
        picked = [r for r in rows if b in _val(r, "Use in").split("; ")]
        lines += [f"## {b}", "", f"{len(picked)} words.", ""]
        for r in picked:
            fr = _val(r, "First recorded")
            lines.append(f"- **{_val(r, 'Word')}** ({_val(r, 'Status')}{', ' + fr if fr else ''}): {_val(r, 'Note')}")
        lines.append("")
    (ex / "by-book.md").write_text("\n".join(lines))

    (ex / "consultant.md").write_text(md(
        "For the sensitivity consultant",
        "Romani words and rows marked 'for the consultant'. Statuses record what a dictionary says; "
        "none of these is cleared for any period.",
        lambda r: "#Romani" in _val(r, "Languages") or "consultant" in _val(r, "Note").lower()))

    order = {"UNCHECKED": 0, "": 0, "UNSUPPORTED": 1, "UNVERIFIABLE": 2, "PARTLY VERIFIED": 3}
    follow = sorted((r for r in rows if _val(r, "Status") in order),
                    key=lambda r: (order[_val(r, "Status")], _val(r, "Word").lower()))
    lines = ["# Follow-up checklist", "",
             "Rows a dictionary could not fully settle from a cloud session: unchecked, unsupported,",
             "unverifiable, then partly verified (usually a date the source does not give).",
             "Tap the Etymonline link, check the point the Note names, then update the row in Notion",
             "(Status, Note, Source, Checked).", ""]
    for r in follow:
        w = _val(r, "Word")
        slug = w.replace("'", "")
        et = ("https://www.etymonline.com/word/" + slug) if " " not in slug else (
            "https://www.etymonline.com/search?q=" + slug.replace(" ", "+"))
        lines.append(f"- [ ] **{w}** ({_val(r, 'Status')}): {_val(r, 'Note')} "
                     f"[Etymonline]({et}) · [current source]({_val(r, 'Source')})")
    (ex / "to-check.md").write_text("\n".join(lines) + "\n")

    counts = {}
    for r in rows:
        counts[_val(r, "Status") or "(blank)"] = counts.get(_val(r, "Status") or "(blank)", 0) + 1
    print(f"{len(rows)} rows -> exports/: etymology.csv, field-guide.md, debunked.md, by-book.md, consultant.md, to-check.md")
    for k in sorted(counts):
        print(f"  {k}: {counts[k]}")


STATUSES = {"UNCHECKED", "VERIFIED", "PARTLY VERIFIED", "UNSUPPORTED", "FALSE", "UNVERIFIABLE"}
USE_IN = {"1589", "1689", "1789", "1889", "1989", "2089", "Tour", "Essays"}


def lint(rows_json):
    rows = json.loads(pathlib.Path(rows_json).read_text())
    if isinstance(rows, dict):
        rows = rows.get("results", rows.get("rows", []))
    problems, seen = [], {}
    for r in rows:
        w, st = _val(r, "Word"), _val(r, "Status")
        tag = f"{w!r}"
        if not w:
            problems.append("row with no Word")
        key = w.strip().lower()
        if key in seen:
            problems.append(f"{tag}: duplicate word (rule 5: merge into one row)")
        seen[key] = True
        if st and st not in STATUSES:
            problems.append(f"{tag}: unknown Status {st!r}")
        if st and st != "UNCHECKED":
            if not _val(r, "Source"):
                problems.append(f"{tag}: {st} but no Source")
            if not _val(r, "Checked"):
                problems.append(f"{tag}: {st} but no Checked date")
            if not _val(r, "Note"):
                problems.append(f"{tag}: {st} but no Note")
        if st == "VERIFIED" and "etymonline" in _val(r, "Note").lower():
            problems.append(f"{tag}: VERIFIED but the Note still asks for Etymonline")
        uses = [u for u in _val(r, "Use in").split("; ") if u]
        for u in uses:
            if u not in USE_IN:
                problems.append(f"{tag}: unknown Use in {u!r}")
        if "#Romani" in _val(r, "Languages"):
            if "consultant" not in _val(r, "Note").lower():
                problems.append(f"{tag}: Romani word without 'for the consultant' (rule 4)")
            if any(u in USE_IN - {"Tour", "Essays"} for u in uses):
                problems.append(f"{tag}: Romani word tagged for a period (rule 4)")
        if len(_val(r, "Note")) > 600:
            problems.append(f"{tag}: Note longer than ~3 sentences")
    print(f"{len(rows)} rows checked, {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
    return 1 if problems else 0


def main(argv):
    if len(argv) < 2 or argv[0] not in ("check", "duden", "export", "lint"):
        print(__doc__)
        return 1
    cmd, args = argv[0], argv[1:]
    if cmd == "export":
        export(args[0])
        return 0
    if cmd == "lint":
        return lint(args[0])
    lang = "English"
    if args and args[0] == "--lang":
        lang, args = args[1], args[2:]
    for w in args:
        print(wiktionary(w, lang) if cmd == "check" else duden(w), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
