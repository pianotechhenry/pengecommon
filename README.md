# Commons desk: period language and sky for *The Commons Series*

`desk check` lists every word or phrase in a scene with no printed attestation before the
book's year, with the evidence. It never edits a file, suggests wording or writes period text.
`desk sky` and `desk almanac` give the calendar and sky at Penge Common, 1580–1800.

**Install** (Python 3.10+, git, curl): `python -m venv .venv && . .venv/bin/activate && pip
install -e .`, then build the index once with `scripts/build_index.sh`. This takes a few hours,
downloads about 17 GB and needs about 25 GB free while building. Each stage can be resumed.

## Commands

- `desk check scene.md --year 1589`. Accepts `.md`, `.txt` or `.docx`; italic is interior
  thought, quoted text is dialogue and the rest is narration, each reported separately. Writes
  `scene.1589.report.html` (click a marked word for its evidence) and `.json`. Options:
  `--window 15`, `--note-min 3`, `--no-watchlist`. `desk lookup forest --year 1689` gives the
  same evidence in the terminal.
- `desk sky 1689-05-01`. Takes the date as written in England then (Old Style until
  2 September 1752); `--ns` or `--os` forces the calendar. Shows both styles, the weekday and
  the legal year (it began on 25 March until 1752), Easter by the Julian computus (Gregorian
  from 1753), the Sunday, Prayer Book holy days and quarter days, sunrise and sunset by the
  sundial, the end of civil twilight in local mean time, and the moon's phase, illumination,
  rise and set.
- `desk almanac 1589`. Writes a printable Lady Day-to-Lady Day year as CSV and HTML.

## Reading a report

| status | meaning |
|---|---|
| (silent) | printed before the year in 3 or more texts |
| NOTE | printed before the year, but thinly |
| BORDERLINE | first printed in the year or within the window after it |
| FLAG | first printed later |
| UNVERIFIED | not in the corpus |
| WATCH | watch-list hit |

Dates come from the earliest **firm**-dated text. An earlier conjectural or ranged imprint
(`[1585?]`) is shown and makes the entry CONTESTED.

The evidence tags are:

- **DOCUMENTED**: a cited text or source says so.
- **REASONABLE INFERENCE**: drawn from evidence that does not state it directly (a spelling
  variant, a lemma, a compound printed as two words, the phrase heuristic).
- **CONTESTED**: the evidence conflicts.
- **UNVERIFIED**: there is no evidence either way.

`watchlist.yaml` is yours, for what a corpus cannot see: senses, names, places, Romani, cant
and idioms. Mark vetted words `kind: accepted`. The Romani/cant section lists every token not
resolved as English, with its watch-list entry or "unplaced — for the consultant". The
Latin/French share is a heuristic, compared only with your `samples/baseline.md`.

## Limits

Absence from the corpus is never proof. Print lags speech, and early print leans to religious
and learned registers. Spelling is matched through EarlyPrint's regularised forms, which miss
some spellings; `reports/acceptance/holdout.md` measures the false flags this causes. A date is
that of the edition transcribed, not of composition. ECCO-TCP is small, so 1789 checks are
thinner.

## Sources (licence · size · route, November 2026)

- EEBO-TCP Phases I and II and ECCO-TCP, EarlyPrint's regularised and lemmatised edition.
  CC0 1.0. 141 + 92 git shards: about 17 GB of shallow clones, with the XML streamed and not
  stored. `bitbucket.org/eads004/eebotcp`, `…/eccotcp`. Evans-TCP is optional
  (`--collections eebo,ecco,evans`).
- TCP catalogue `TCP.csv`. CC0. 29 MB.
  `raw.githubusercontent.com/textcreationpartnership/Texts`.
- Wiktionary English via kaikki.org (Wiktextract JSONL of 30 October 2026). CC BY-SA 4.0 and
  GFDL. 3.4 GB, streamed. `kaikki.org/dictionary/English/`.
- Prayer Books: TCP A05983 (the 1559 book, printed 1603) and A28758 (the 1662 book, printed
  1693). CC0.
- PyEphem 4.2 (MIT): VSOP87 for the Sun and ELP 2000-82 for the Moon. ΔT follows Morrison &
  Stephenson (2004) before 1700 and the Astronomical Almanac table after.

Acceptance results are in `reports/acceptance/` and sample reports in `reports/sample/`.
