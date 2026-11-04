# Commons desk: a period-language and sky desk for *The Commons Series*

The desk reads a scene and lists, with evidence, every word or phrase that has no printed
attestation before the book's year. It never edits a file, suggests wording or writes period
text. It flags, cites and stops. It also gives the sky and calendar for any day at Penge
Common, 1580–1800.

**Install** (Python 3.10+): `python -m venv .venv && . .venv/bin/activate && pip install -e .`
Then build the index once with `scripts/build_index.sh`. This takes several hours, downloads
about 17 GB and needs about 25 GB of free disk; every stage can be resumed.

## The three commands

- `desk check scene.md --year 1589` reads `.md`, `.txt` or `.docx`. Italic is interior
  thought, quoted text is dialogue and the rest is narration; each is reported separately.
  The command writes `scene.1589.report.html` (the text with flags marked; click a word for
  its evidence) and `.json`. Options: `--window 15` (the BORDERLINE window), `--note-min 3`,
  and `--no-watchlist` (corpus evidence only). `desk lookup WORD… --year 1689` gives the same
  evidence for one word or phrase in the terminal.
- `desk sky 1689-05-01` shows a date as written in England at the time (Old Style before
  14 September 1752); `--ns` or `--os` forces the calendar. It gives Old and New Style dates,
  the weekday, the legal year (which began 25 March before 1752), Easter by the Julian
  computus (Gregorian from 1753), the Sunday, Prayer Book holy days, quarter days, sunrise and
  sunset by the sundial, the end of civil twilight in local mean time, and the moon.
- `desk almanac 1589` writes a printable Lady Day-to-Lady Day year as CSV and HTML.

## Statuses and tags

A word is silent when it was printed before the year in at least 3 texts. It is marked NOTE
when printed before the year in fewer texts, BORDERLINE when first printed in the year or
within 15 years after, FLAG when first printed later, and UNVERIFIED when it is not in the
corpus. Dates use the earliest *firm*-dated text; earlier conjectural or ranged dates
(`[1585?]`, `1580-1590`) are shown and tagged CONTESTED. `watchlist.yaml` (yours to maintain)
covers what a corpus cannot see: senses, names, places, Romani, cant and idioms. Each hit shows
its reason and tag. Tags: **DOCUMENTED** rests on a cited dated text or source. **REASONABLE
INFERENCE** is drawn from evidence that does not state it directly: a spelling variant, a lemma,
or the phrase heuristic. **CONTESTED** means the evidence conflicts. **UNVERIFIED** means there
is no evidence either way. The Latin/French share per paragraph is a heuristic, compared only
with your own `samples/baseline.md`.

## What the corpus can and cannot tell you

Absence from the corpus is never proof. Print lags speech, and early print is skewed to
religious and learned registers; everyday, female, regional, criminal and Romani speech is
thin or absent. Spelling is matched through EarlyPrint's regularised forms (MorphAdorner), which
miss some spellings. `reports/acceptance/holdout.md` measures how often this produces false
flags. Dates are of the edition transcribed, not of composition. For 1789, ECCO-TCP is small
(about 2,000 texts).

## Sources: licence, size, route (checked November 2026)

| source | licence | size | route |
|---|---|---|---|
| EEBO-TCP Phases I and II, EarlyPrint edition (regularised, lemmatised) | CC0 1.0 | 141 shards, ~17 GB shallow git clones, ~160 GB XML streamed, not stored | `bitbucket.org/eads004/eebotcp` |
| ECCO-TCP, EarlyPrint edition | CC0 1.0 / public domain | 92 shards, under 2 GB | `bitbucket.org/eads004/eccotcp` |
| TCP catalogue `TCP.csv` | CC0 1.0 | 29 MB, 61,315 records | `raw.githubusercontent.com/textcreationpartnership/Texts` |
| Wiktionary English via kaikki.org (Wiktextract JSONL, 30 Oct 2026) | CC BY-SA 4.0 / GFDL | 3.4 GB, streamed | `kaikki.org/dictionary/English/` |
| Prayer Books: TCP A05983 (1603 printing of the 1559 book), A28758 (1693 printing of the 1662 book) | CC0 1.0 | 2 texts | TCP GitHub raw |
| PyEphem 4.2 (VSOP87, ELP 2000-82; ΔT per Morrison & Stephenson 2004 before 1700) | MIT | — | PyPI |

EEBO-TCP Phase II has been public since 2020 and is included. Evans-TCP (American) is optional
(`desk build --collections eebo,ecco,evans`). Reports derived from Wiktionary data are CC BY-SA.
The code is the author's.
