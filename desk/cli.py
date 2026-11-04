"""The `desk` command.

  desk check FILE --year 1589      report on a scene (.md, .txt, .docx)
  desk lookup WORD... --year 1589  evidence for one word or phrase, in the terminal
  desk sky DATE [--ns]             one day at Penge: calendar, feasts, Sun, Moon
  desk almanac YEAR                Lady Day-to-Lady Day year as CSV and HTML
  desk build [--stage ...]         download the corpus and build the index
  desk holdout                     acceptance test 1 (held-out 1570-1589 texts)
  desk watchlist --annotate        write the corpus's own dates into watchlist.yaml
  desk info                        what the index holds
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from desk import paths


def _checker(args):
    from desk.check.check import Checker, Config
    cfg = Config(year=args.year, window=args.window, note_min=args.note_min,
                 use_watchlist=not args.no_watchlist,
                 watchlist_path=Path(args.watchlist) if args.watchlist else None,
                 baseline_path=Path(args.baseline) if args.baseline else None,
                 expect_min=args.phrase_expect)
    from desk.index import Index
    return Checker(cfg, Index(Path(args.index) if args.index else paths.index_path()))


def cmd_check(args) -> int:
    ch = _checker(args)
    if len(args.file) > 1 and (args.html or args.json):
        print("desk: --html/--json name one report; use --out with several files", file=sys.stderr)
        return 2
    for f in args.file:
        _check_one(ch, args, Path(f))
    print("Absence from the corpus is never proof: print lags speech.")
    return 0


def _check_one(ch, args, src: Path) -> None:
    from desk.report.html import write
    t0 = time.time()
    res = ch.check_file(src)
    out = Path(args.out) if args.out else src.parent
    stem = f"{src.stem}.{args.year}" + ("" if not args.no_watchlist else ".nowatch")
    html_path = Path(args.html) if args.html else out / f"{stem}.report.html"
    json_path = Path(args.json) if args.json else out / f"{stem}.report.json"
    write(res, html_path, json_path)
    s = res["summary"]["occurrences"]
    words = sum(res["streams_words"].values())
    print(f"{src.name}: {words} words checked against print before {args.year} "
          f"({time.time() - t0:.1f}s)")
    print(f"{'':12s}{'narration':>11s}{'dialogue':>10s}{'interior':>10s}")
    for st in ("FLAG", "BORDERLINE", "NOTE", "UNVERIFIED", "WATCH"):
        r = s[st]
        print(f"{st:12s}{r['narration']:>11d}{r['dialogue']:>10d}{r['interior']:>10d}")
    shown = [it for it in res["items"].values() if it["status"] in ("FLAG", "BORDERLINE", "UNVERIFIED", "WATCH")]
    for it in shown[: args.top]:
        ff = (it.get("evidence") or {}).get("first_firm") or {}
        date = f"{ff['year']} {ff['tcp']}" if ff else "-"
        streams = ",".join(sorted({o["stream"][:3] for o in it["occurrences"]}))
        print(f"  {it['status']:<10s} {it['text'][:24]:<24s} {it['tag']:<21s} {date:<14s} {streams}")
    if len(shown) > args.top:
        print(f"  ... {len(shown) - args.top} more in the report")
    if res["romani"]:
        print(f"Romani/cant stream: {len(res['romani'])} tokens "
              f"({sum(1 for r in res['romani'] if not r.get('watch'))} unplaced)")
    print(f"report: {html_path}\njson:   {json_path}\n")


def cmd_lookup(args) -> int:
    ch = _checker(args)
    text = " ".join(args.words)
    from desk.keys import form_key
    keys = tuple(k for k in (form_key(w) for w in text.split()) if k)
    print(f"'{text}' against print before {args.year}")
    if len(keys) == 1:
        res = ch.resolve(text)
        _print_evidence(ch, res, args.year)
        for line in ch.evidence_lines(res):
            print(f"  {line['year']} {line['tcp']}: …{line['left']} [{line['kw']}] {line['right']}…")
    else:
        ev = ch.phrase_evidence(keys)
        if ev is None:
            print("  not in the phrase index (phrases printed in fewer than "
                  f"{ch.idx.info.get('ngram_min_df', '?')} texts are only found if on the watch list)")
            parts = [ch.resolve(k) for k in keys]
            for k, r in zip(keys, parts):
                print(f"  {k}: {r['status']}")
        else:
            _print_evidence(ch, ev, args.year)
            for line in ev.get("kwic", []):
                print(f"  {line.get('year')} {line.get('tcp')}: …{line['left']} [{line['kw']}] {line['right']}…")
            t = ch.idiom_test(keys)
            if t:
                print(f"  phrase heuristic: {t['note']}")
    for e in ch.watch:
        if (e.match in ("word", "exact") and len(keys) == 1 and keys[0] in e.keys) or \
                (e.match == "phrase" and keys in [tuple(p) for p in e.phrases]):
            print(f"  watch list: {e.reason} [{e.tag}]" + (f" ({e.source})" if e.source else ""))
    print("Absence from the corpus is never proof: print lags speech.")
    return 0


def _print_evidence(ch, ev: dict, year: int) -> None:
    print(f"  status {ev['status']} [{ev['tag']}] - {ev.get('basis', '')}"
          + (f"; {ev['note']}" if ev.get("note") else ""))
    for label, c in (("earliest firm-dated", ev.get("first_firm")), ("earlier, date not firm", ev.get("first_any"))):
        if c:
            print(f"  {label}: {c['year']} {c['tcp']} {c['title'][:90]} [imprint {c['date_raw']}; {c['date_kind']}]")
    if ev.get("ntexts") is not None:
        print(f"  texts before {year}: {ev.get('n_before')}"
              f"{' (decade resolution)' if ev.get('n_before_approx') else ''}; texts in all: {ev.get('ntexts')}")
    dec = ev.get("decades") or {}
    if dec:
        print("  by decade: " + " ".join(f"{d}s:{n}" for d, n in sorted(dec.items(), key=lambda x: int(x[0]))))


def cmd_sky(args) -> int:
    from desk.sky import calendar as C
    from desk.sky.report import day_info, format_day
    y, m, d = C.parse_date(args.date)
    if args.ns:
        day = C.day_ns(y, m, d)
    elif args.os:
        day = C.day_os(y, m, d)
    else:
        day = C.civil_day(y, m, d)
    info = day_info(day)
    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=1))
    else:
        print(format_day(info))
    return 0


def cmd_almanac(args) -> int:
    from desk.sky.report import almanac, write_csv, write_html
    out = Path(args.out) if args.out else Path("almanac")
    out.mkdir(parents=True, exist_ok=True)
    rows = almanac(args.year)
    csv_p = out / f"penge-almanac-{args.year}.csv"
    html_p = out / f"penge-almanac-{args.year}.html"
    write_csv(rows, csv_p)
    write_html(rows, args.year, html_p)
    print(f"{len(rows)} days, {rows[0]['legal']} to {rows[-1]['legal']}\n{csv_p}\n{html_p}")
    return 0


def cmd_build(args) -> int:
    data = paths.data_dir()
    data.mkdir(parents=True, exist_ok=True)
    stage = data / "stageA"
    db = paths.index_path()
    stages = args.stage.split(",") if args.stage != "all" else [
        "fetch", "aggregate", "kwic", "ngrams", "scan", "holdout", "etymology", "clean"]
    tcp_csv = data / "TCP.csv"
    if "fetch" in stages or "aggregate" in stages:
        if not tcp_csv.exists():
            import urllib.request
            from desk.build.sources import TCP_METADATA
            print("downloading TCP.csv")
            tcp_csv.write_bytes(urllib.request.urlopen(TCP_METADATA["url"]).read())
    if "fetch" in stages:
        from desk.build import fetch
        fetch.run(data, args.collections.split(","), workers=args.workers, source=args.source)
    if "aggregate" in stages:
        import re as _re
        from desk.build.aggregate import aggregate
        for coll in args.collections.split(","):
            gm = stage / f"super-{coll}" / ".gitmodules"
            if gm.exists():
                shards = set(_re.findall(r"path\s*=\s*texts/(\S+)", gm.read_text()))
                missing = [x for x in shards if not (stage / "done" / f"{coll}-{x}").exists()]
                if missing:
                    print(f"warning: {len(missing)} {coll} shards not extracted yet "
                          f"({', '.join(sorted(missing)[:8])}...); the index will lack them")
        aggregate(data, tcp_csv, db)
    if "kwic" in stages:
        from desk.build.kwic import render_all
        render_all(db, stage, workers=args.workers)
    if "ngrams" in stages:
        from desk.build.ngrams import build
        build(db, stage, workers=args.workers)
    if "scan" in stages:
        from desk.build import scan
        from desk.watchlist import load, phrases
        scan.run(db, stage, phrases(load(paths.watchlist_path())), workers=args.workers)
    if "holdout" in stages:
        from desk.build.holdout import write_texts
        write_texts(db, stage, data / "holdout")
    if "etymology" in stages:
        from desk import etymology
        src = args.kaikki or "https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl"
        if src.startswith("http"):
            import io
            import subprocess
            print(f"streaming {src}")
            proc = subprocess.Popen(["curl", "-sS", "--retry", "5", src], stdout=subprocess.PIPE)
            etymology.build_from_kaikki(io.TextIOWrapper(proc.stdout, encoding="utf-8"),
                                        paths.etymology_path())
            proc.wait()
        elif src.endswith(".sqlite"):
            etymology.build_from_extract(Path(src), paths.etymology_path())
        else:
            etymology.build_from_kaikki(Path(src), paths.etymology_path())
    if "clean" in stages:
        # intermediates no longer needed once the index exists; the token
        # streams are kept, as `--stage scan` (after editing watch-list
        # phrases) and `--stage holdout` read them
        import shutil
        for d in (stage / "keys", data / "stageN"):
            if d.exists():
                shutil.rmtree(d)
                print(f"removed {d}")
    if "prayerbook" in stages:
        import runpy
        runpy.run_path(str(paths.REPO_ROOT / "scripts" / "extract_prayerbook.py"), run_name="__main__")
    return 0


def cmd_holdout(args) -> int:
    from desk.build.holdout import run_test
    return run_test(args)


def cmd_watchlist(args) -> int:
    from desk.build.annotate import annotate
    return annotate(paths.watchlist_path(), paths.index_path())


def cmd_info(args) -> int:
    from desk.index import Index
    idx = Index(paths.index_path())
    nt, nw = idx.corpus_total()
    print(f"index: {idx.path}  built {idx.info.get('built')}")
    print(f"texts: {nt:,}  words: {nw:,}  held out: {len(idx.holdout)}")
    for y in (1589, 1689, 1789):
        t, w = idx.corpus_before(y)
        print(f"  printed before {y}: about {t:,} texts, {w:,} words")
    print(f"phrase index: {'yes' if idx.has_ngrams else 'no'}; watch-list phrase scan: "
          f"{'yes' if idx.has_phrases else 'no'}; punctuation scan: {'yes' if idx.has_punct else 'no'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="desk", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--year", type=int, required=True, help="the book's year, e.g. 1589")
        sp.add_argument("--window", type=int, default=15, help="BORDERLINE window in years (15)")
        sp.add_argument("--note-min", type=int, default=3,
                        help="NOTE when printed before the year in fewer texts than this (3)")
        sp.add_argument("--no-watchlist", action="store_true", help="corpus evidence only")
        sp.add_argument("--watchlist", help="another watch-list file")
        sp.add_argument("--baseline", help="Henry's own passages for the Latin/French comparison "
                                           "(default samples/baseline.md)")
        sp.add_argument("--index", help="the index file (default data/index.sqlite)")
        sp.add_argument("--phrase-expect", type=float, default=10.0,
                        help="phrase heuristic: texts expected before the year at the later "
                             "rate, below which a later phrase is not flagged (10)")

    sp = sub.add_parser("check", help="report on a scene (or several)")
    sp.add_argument("file", nargs="+")
    common(sp)
    sp.add_argument("--out", help="directory for the reports (default: beside the file)")
    sp.add_argument("--top", type=int, default=12, help="flagged items to list in the terminal (12)")
    sp.add_argument("--html")
    sp.add_argument("--json")
    sp.set_defaults(fn=cmd_check)

    sp = sub.add_parser("lookup", help="evidence for one word or phrase")
    sp.add_argument("words", nargs="+")
    common(sp)
    sp.set_defaults(fn=cmd_lookup)

    sp = sub.add_parser("sky", help="one day at Penge")
    sp.add_argument("date", help="YYYY-MM-DD (as dated in England then, unless --ns/--os)")
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--ns", action="store_true", help="the date is New Style (Gregorian)")
    g.add_argument("--os", action="store_true", help="the date is Old Style (Julian)")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(fn=cmd_sky)

    sp = sub.add_parser("almanac", help="a Lady Day-to-Lady Day year")
    sp.add_argument("year", type=int)
    sp.add_argument("--out", help="output directory (default ./almanac)")
    sp.set_defaults(fn=cmd_almanac)

    sp = sub.add_parser("build", help="download the corpus and build the index")
    sp.add_argument("--stage", default="all",
                    help="fetch,aggregate,kwic,ngrams,scan,holdout,etymology,clean,prayerbook or all")
    sp.add_argument("--collections", default="eebo,ecco", help="eebo,ecco[,evans]")
    sp.add_argument("--source", default="raw", choices=("raw", "git"),
                    help="raw: fetch each text over HTTPS (default); git: shallow clones")
    sp.add_argument("--workers", type=int, default=4)
    sp.add_argument("--kaikki", help="kaikki.org English JSONL: a path, '-' for stdin, or a URL")
    sp.set_defaults(fn=cmd_build)

    sp = sub.add_parser("holdout", help="acceptance test 1")
    sp.add_argument("--year", type=int, default=1589)
    sp.add_argument("--window", type=int, default=15)
    sp.add_argument("--note-min", type=int, default=3)
    sp.add_argument("--out", default=str(paths.REPO_ROOT / "reports" / "acceptance"))
    sp.set_defaults(fn=cmd_holdout)

    sp = sub.add_parser("watchlist", help="annotate the watch list with corpus dates")
    sp.add_argument("--annotate", action="store_true", required=True)
    sp.set_defaults(fn=cmd_watchlist)

    sp = sub.add_parser("info", help="what the index holds")
    sp.set_defaults(fn=cmd_info)

    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except (FileNotFoundError, ValueError) as e:
        print(f"desk: {e}", file=sys.stderr)
        return 2
    except BrokenPipeError:          # e.g. `desk check ... | head`
        import os
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0


if __name__ == "__main__":
    sys.exit(main())
