"""Acceptance test 2: which of Henry's listed problems does the desk catch,
with the watch list off (corpus and built-in rules only) and on?

Henry's draft (samples/book2_ch1-2.md) is checked if present; the listed
items are also checked on their own, one per line
(tests/fixtures/acceptance2_items.md, a word list, not prose), so the result
does not depend on the draft being available.  Writes
reports/acceptance/items.md and the sample reports in reports/sample/.
"""
from __future__ import annotations

import sys

from desk import paths
from desk.check.check import Checker, Config
from desk.check import reader
from desk.index import Index
from desk.report.html import write

ROOT = paths.REPO_ROOT
ITEMS = ["structural", "connect", "erm", "What!?", "Now get lost", "See you later", "Golden Boy",
         "forest", "ma'am", "Rowan", "Janos", "sar", "dej", "jertis"]
LABEL = {"connect": "connect (modern emotional sense)"}


def describe(items_in_para: list[dict]) -> str:
    if not items_in_para:
        return "not caught"
    parts = []
    for it in sorted(items_in_para, key=lambda x: x["status"]):
        ev = it.get("evidence") or {}
        ff = ev.get("first_firm") or {}
        date = f", form first printed {ff['year']} ({ff['tcp']})" if ff else ""
        kind = {"word": "word", "watch": "watch list", "interjection": "interjection rule",
                "punct": "punctuation rule", "phrase": "phrase heuristic"}[it["type"]]
        parts.append(f"{it['status']} [{it['tag']}] by {kind}{date}")
    return "; ".join(parts)


def main() -> int:
    idx = Index(paths.index_path())
    out_dir = ROOT / "reports" / "sample"
    out_dir.mkdir(parents=True, exist_ok=True)
    fixture = ROOT / "tests" / "fixtures" / "acceptance2_items.md"
    results = {}
    for watch in (False, True):
        ch = Checker(Config(year=1689, use_watchlist=watch), idx)
        res = ch.check_paragraphs(reader.read(fixture), source=str(fixture.relative_to(ROOT)))
        tag = "watchlist-on" if watch else "watchlist-off"
        write(res, out_dir / f"acceptance2_items.1689.{tag}.html", out_dir / f"acceptance2_items.1689.{tag}.json")
        per_para = {}
        for it in res["items"].values():
            for o in it["occurrences"]:
                per_para.setdefault(o["para"], {})[it["id"]] = it
        results[watch] = per_para
    lines = ["# Acceptance test 2: the listed problems, year 1689", "",
             "Henry's draft `samples/book2_ch1-2.md` is not in the repository, so each listed item was "
             "checked on its own line (`tests/fixtures/acceptance2_items.md`); on a real draft the "
             "context (dialogue, a following word) can only add evidence. Watch list off = corpus "
             "evidence plus the built-in interjection and punctuation rules.", "",
             "| item | watch list off | watch list on | caught |", "|---|---|---|---|"]
    for i, item in enumerate(ITEMS):
        off = list(results[False].get(i, {}).values())
        on = list(results[True].get(i, {}).values())
        verdict = "with watch list OFF" if off else ("only with it ON" if on else "**not caught**")
        lines.append(f"| {LABEL.get(item, item)} | {describe(off)} | {describe(on)} | {verdict} |")
    draft = ROOT / "samples" / "book2_ch1-2.md"
    if draft.exists():
        for watch in (False, True):
            ch = Checker(Config(year=1689, use_watchlist=watch), idx)
            res = ch.check_file(draft)
            tag = "watchlist-on" if watch else "watchlist-off"
            write(res, out_dir / f"book2_ch1-2.1689.{tag}.html", out_dir / f"book2_ch1-2.1689.{tag}.json")
        lines += ["", "Henry's draft was also checked: see reports/sample/book2_ch1-2.1689.*.html."]
    out = ROOT / "reports" / "acceptance" / "items.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
