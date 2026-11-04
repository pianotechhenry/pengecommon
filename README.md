# Commons desk: period language and sky for *The Commons Series*

`desk check` lists every word or phrase in a scene with no printed attestation before the
book's year, with the evidence. It never edits a file, suggests wording or writes period text.
`desk sky` and `desk almanac` give the calendar and sky at Penge Common, 1580–1800.

**Install** (Python 3.10+, git, curl): `python -m venv .venv && . .venv/bin/activate && pip
install -e .`, then build the index once with `scripts/build_index.sh`. This takes 3–6 hours and
downloads 15–20 GB, needing 25 GB free; every stage can be resumed. The result is a 2.6 GB index
of 60,932 texts and 1.38 billion words.

## Commands

- `desk check scene.md --year 1589` accepts `.md`, `.txt` or `.docx`. Italic is interior thought,
  quoted text is dialogue and the rest is narration, each reported separately. It writes
  `scene.1589.report.html` (click a marked word for its evidence) and `.json`. Options:
  `--window 15`, `--note-min 3`, `--no-watchlist`, and `--phrases`, which also flags phrases
  first printed later (a heuristic: about 0.3 false flags per 1,000 words of period text).
  `desk lookup WORD --year 1689` gives the same evidence in the terminal.
- `desk sky 1689-05-01` takes the date as written then (Old Style until 2 September 1752;
  `--ns` or `--os` forces the calendar). It gives both styles, the weekday, the legal year
  (which began on 25 March until 1752), Easter (Julian computus, Gregorian from 1753), the
  Sunday, holy days and quarter days, sunrise and sunset by the sundial, the end of civil
  twilight (local mean time), and the moon.
- `desk almanac 1589` writes a printable Lady Day-to-Lady Day year as CSV and HTML.

## Reading a report

A word is silent when printed before the year in 3 or more texts. Otherwise it is marked:

| status | meaning |
|---|---|
| NOTE | printed before the year, but thinly |
| BORDERLINE | first printed in the year or within the window after it |
| FLAG | first printed later |
| UNVERIFIED | not in the corpus |
| WATCH | a watch-list hit |

Dates use the earliest **firm**-dated text. An earlier conjectural or ranged imprint (`[1585?]`)
is shown, and makes the entry CONTESTED.

The evidence tags:

- **DOCUMENTED**: a cited text or source says so.
- **REASONABLE INFERENCE**: drawn from evidence that does not state it directly, such as a
  spelling variant, a lemma, or a compound printed as two words.
- **CONTESTED**: the evidence conflicts.
- **UNVERIFIED**: there is no evidence either way.

`watchlist.yaml` is yours, for what a corpus cannot see: senses, names, places, Romani, cant and
idioms. Give vetted words `kind: accepted`. The Romani/cant section lists every token not resolved
as English, each with its watch-list entry or "unplaced — for the consultant". The Latin/French
share is a heuristic, compared only with your `samples/baseline.md`.

## Limits

Absence from the corpus is never proof. Print lags speech, and early print leans to religious and
learned registers. Spellings are matched through EarlyPrint's regularised forms, which miss some;
`reports/acceptance/holdout.md` measures the false flags that result. Dates are of the edition
transcribed, not of composition. ECCO-TCP is small, so 1789 checks are thinner.

## Sources (licence · size · route, November 2026)

- EEBO-TCP I and II (59,006 texts, 1.33 bn words) and ECCO-TCP (1,997 texts, 56 m words), in
  EarlyPrint's regularised, lemmatised edition. CC0. 233 git shards, fetched per file or cloned
  shallow, with the XML streamed and never stored, from `bitbucket.org/eads004/eebotcp` and
  `…/eccotcp`. EarlyPrint has about 2,000 of ECCO-TCP's 2,473 texts; Evans-TCP is optional
  (`--collections eebo,ecco,evans`).
- TCP catalogue `TCP.csv`. CC0. 29 MB, from `raw.githubusercontent.com/textcreationpartnership`.
- Wiktionary English via kaikki.org (Wiktextract JSONL, 30 October 2026). CC BY-SA 4.0 / GFDL.
  3.4 GB, streamed.
- Prayer Books: TCP A05983 (the 1559 book, printed 1603) and A28758 (the 1662 book, printed
  1693). CC0.
- PyEphem 4.2 (MIT): VSOP87 for the Sun, ELP 2000-82 for the Moon, and ΔT from Morrison &
  Stephenson (2004) before 1700.

Results are in `reports/acceptance/`; sample reports and almanacs in `reports/sample/`.
