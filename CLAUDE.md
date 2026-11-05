# CLAUDE.md: Etymology — Did You Know (master)

This repository backs up Henry Blomstrand's etymology database for **The Commons
Series** (six novels on Penge Common, SE20, 1589–2089). The live database is in
Notion; this repo holds the rules, a helper script and CSV snapshots.

Read this file before touching the database. Henry works mostly on his phone:
keep messages to him short.

## Where things are

| What | ID / link |
| --- | --- |
| Database | https://app.notion.com/p/3e3ca20a53884da0b2c6f53d69ed8b24 |
| Data source (use for queries and new rows) | `collection://81b3b6ad-71b4-4ad1-b969-46c8bf8c9d6e` |
| View "To check" (UNCHECKED or blank) | `view://40eaf025-42e8-8186-8975-000ce3dce006` |
| View "Verified" | `view://40eaf025-42e8-81f8-bead-000cc1673dd1` |
| View "Debunked" (FALSE) | `view://40eaf025-42e8-81b9-9d3f-000cae01b71d` |
| View "Field guide" | `view://40eaf025-42e8-8182-ac3e-000ca9d051af` |
| View "By book" (board on Use in) | `view://40eaf025-42e8-81b2-a3df-000cbf86556e` |
| View "Follow-up" (PARTLY VERIFIED, UNSUPPORTED, UNVERIFIABLE) | `view://40faf025-42e8-815c-ad80-000cb8fc638a` |
| View "Consultant" (#Romani or "consultant" in Note) | `view://40faf025-42e8-81d7-beb1-000c0bc62571` |
| Project docs (source of claims) | https://app.notion.com/p/3b1af02542e881dcadd7f5ee6a27ae7a |
| Backup | `exports/etymology.csv`, plus phone-readable `by-book.md`, `field-guide.md`, `debunked.md`, `consultant.md`, `to-check.md` |
| Helper | `tools/etym.py` |

## Schema

| Property | Type | Meaning |
| --- | --- | --- |
| Word | title | The headword, as the project uses it. One row per word. |
| Etymology | text | **The claim as found.** Never rewrite it; it is the record of what was asserted. |
| Languages | multi-select | Languages in the **source's** derivation (`#OldEnglish`, `#Romani`, `#Cant` …). Add options as needed. |
| Note | text | The "did you know", 1–3 plain sentences, in our own words. For FALSE rows, say what the source says instead. |
| First recorded | text | Only as a fetched source states it ("1688 (coined)", "late 16th century", "Old English"). Blank if the source gives no date. |
| Status | select | See below. Blank counts as UNCHECKED. |
| Source | url | The dictionary page behind the Status. |
| Checked | date | When the Source was fetched. |
| Found in | text | Where the claim came from: `Doc 13`, `Original log (28 Jul 2026)`, `chat 4 Nov 2026`, `seed`. Semicolon-separated. |
| Added by | select | Henry · Claude chat · Claude Code. Blank on the 33 original rows: their author was not recorded. |
| Use in | multi-select | 1589 · 1689 · 1789 · 1889 · 1989 · 2089 · Tour · Essays. Where the word is useful. **Not** a period-safety stamp. |
| Field guide | checkbox | A story worth telling aloud. Debunkings count. |

## Status values and how to choose

- **UNCHECKED**: not yet checked (default; blank means the same).
- **VERIFIED**: a dictionary page fetched in that session confirms the claim's etymological core, and any date the claim gives.
- **PARTLY VERIFIED**: the core is confirmed but a date, gloss or extra link is missing from the source or slightly off. The Note says which part.
- **UNSUPPORTED**: the source has the word but is silent on the claim.
- **FALSE**: the source contradicts the claim's core. Keep the row; the Note says what the source says instead.
- **UNVERIFIABLE**: no dictionary entry could be found for the word.

When a claim is mostly right with one wrong detail (e.g. *seed*, *shroud*), use
PARTLY VERIFIED and name the error in the Note. Use FALSE when the central
derivation or the headline story is contradicted (e.g. *bar* from Old Norse,
*grimy* from the Grimes family).

## RULES (also in the Notion database description)

1. Mark a row VERIFIED only from a dictionary page **fetched in this session**:
   Etymonline first, Wiktionary second, Duden for German. **Never from memory.**
2. Paraphrase. At most one quote under 15 words per source. Link; don't copy.
3. If the source contradicts the claim, mark it FALSE, keep the row, and say in
   the Note what the source says instead. Debunkings are wanted: never delete one.
4. Romani words: record what the source says, add "for the consultant" to the
   Note, and never mark one safe for a period (leave Use in blank).
5. One row per word. If the word is already there, merge into that row
   (append to Found in; extend the Note).
6. Added by: Claude Code for rows a Claude Code session creates.

## Source access from a cloud session (checked 5 Nov 2026)

- **Etymonline** sits behind a Cloudflare bot challenge (HTTP 403,
  `cf-mitigated: challenge`). Do not try to get round it (browser user agents,
  archives, proxies): that is bot-check circumvention. Use Wiktionary and say
  so in the Note when a date needs Etymonline.
- **Wiktionary**: fetch normal pages (`https://en.wiktionary.org/wiki/WORD`).
  The `w/api.php` API returns 429 quickly. Pace at about one page per 1.5 s and
  send a descriptive User-Agent. `tools/etym.py` does both and caches pages.
- **Duden**: `https://www.duden.de/rechtschreibung/<Slug>`. Slugs carry a
  disambiguator (`Meiler_Reaktor`, `Koehler_Beruf`, `Kraft_Energie`); find them
  via `https://www.duden.de/suchen/dudenonline/<word>`. Many entries have no
  Herkunft section.
- The environment's network allowlist must include `etymonline.com`,
  `www.etymonline.com`, `en.wiktionary.org` and `www.duden.de`.

## How to check a word (Claude Code)

1. Look for an existing row: query the data source in **rows mode** with a
   `Word` filter (`string_is`, then `string_contains`). Prefer rows mode over
   SQL: SQL counts against the workspace's quota.
2. Fetch: `python3 tools/etym.py check WORD` (English section),
   `--lang all` for Romani and cant, `--lang German`, or `duden SLUG`.
   Romani entries often live under a different spelling (`veś`, `ćhavo`,
   `rukh`, `jag`); follow the "Anglicized form of" pointer.
3. Judge against the rules above. Write Note, Status, Source, Checked,
   First recorded, Languages, Use in, Field guide, Found in.
4. Create or update the row (`notion-create-pages` with the data source as
   parent; `notion-update-page` for an existing row). Multi-selects take a JSON
   array string, the checkbox takes `__YES__`/`__NO__`, the date takes
   `date:Checked:start` and `date:Checked:is_datetime: 0`.
5. Refresh the backup (below) and commit.

Work in batches of about 25 rows and export after each batch.

## Refreshing the backup

1. Read every row in rows mode (100 per call; split with filters, e.g. one call
   per Status value, until each call returns fewer than 100).
2. Save the combined list of row objects as JSON in the scratchpad.
3. `python3 tools/etym.py lint rows.json` checks the rules (status values,
   Source and Checked on every checked row, no duplicate words, Romani rows
   carry "for the consultant" and no period tag). Fix anything it reports.
4. `python3 tools/etym.py export rows.json` rewrites everything in `exports/`
   and prints counts by status.
5. Commit with a message naming the batch.

## State after the first pass (5 Nov 2026)

155 rows: the 33 originals plus 122 harvested from Docs 01–40, the seed
list and the 4 Nov chat. Workspace searches for "Did you know", "from Old
English", "from Latin" and "etymology" found nothing new on Commons pages
(other hits were the AQA Physics Tuition workspace, out of scope).

| Status | Rows |
| --- | --- |
| VERIFIED | 67 |
| PARTLY VERIFIED | 62 |
| UNSUPPORTED | 11 |
| FALSE | 10 |
| UNVERIFIABLE | 5 |

Merged on harvest (rule 5): teller into telling; villein into villain;
Egyptian into gypsy; drover into drove; boot into bote; dukkering into
dukkeripen; suffragist into suffragette.

## Open items

- Dates that only Etymonline gives (first-recorded years) are marked
  PARTLY VERIFIED. `exports/to-check.md` lists every unsettled row with a
  direct Etymonline link for a manual check in a browser.
- drabarni is FALSE against Wiktionary (witch or sorceress, not healer).
  It matters for Jem's mother: raise it with the sensitivity consultant.
- Doc 13's Surrey dialect table and woodland vocabulary are glosses, not
  etymology claims; they were not harvested.
