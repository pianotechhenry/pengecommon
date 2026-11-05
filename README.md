# Etymology — Did You Know (master)

Backup and tools for the Commons Series etymology database.

**Open the database:** https://app.notion.com/p/3e3ca20a53884da0b2c6f53d69ed8b24

## Views

- **To check**: words nobody has checked yet (Status UNCHECKED or blank).
- **Verified**: confirmed against a dictionary page.
- **Debunked**: claims a dictionary contradicts. Keep them.
- **Field guide**: stories worth telling, debunkings included.
- **By book**: a board grouped by book, Tour and Essays.

Each row keeps the original claim in **Etymology**, and the checked version in
**Note**, with a **Source** link and a **Status**.

## Henry: adding a word in the Notion app

1. Open the database and tap **To check**.
2. Tap **+ New** (or **+** at the bottom of the list).
3. Type the word as the title.
4. Fill in what you know:
   - **Etymology**: the claim, as you heard or wrote it.
   - **Found in**: where it came from (a doc number, a book, a page, "chat").
   - **Added by**: Henry.
5. Leave **Status** blank or set UNCHECKED. The row stays in **To check**
   until a Claude session checks it.

Optional: tick **Field guide** if it's a story you want to tell, and set
**Use in** for the book you want it for.

## Claude: adding or checking a word

Start a Claude Code session on this repository and say, for example:

> Check the words in "To check".

or

> Add "chaldron" from Doc 40 and check it.

The session follows `CLAUDE.md`: it checks the dictionary pages, writes the
Note and Status, refreshes `exports/`, and commits.

## What's in this repository

| Path | What |
| --- | --- |
| `CLAUDE.md` | Schema, rules and procedures for Claude sessions. |
| `exports/etymology.csv` | Full snapshot of the database after the latest batch. |
| `exports/field-guide.md` | The Field guide rows, readable on a phone. |
| `exports/debunked.md` | The FALSE rows, readable on a phone. |
| `tools/etym.py` | Checks a word on Wiktionary or Duden; rebuilds `exports/`. |

Etymonline blocks automated access from cloud sessions, so checks use
Wiktionary (and Duden for German). Dates that only Etymonline gives are flagged
in the Notes for a manual check.
