#!/usr/bin/env bash
# Build the attestation index from scratch (several hours; ~17 GB downloaded,
# ~25 GB of free disk needed while building).  Every stage is resumable:
# re-run the script and finished work is skipped or redone cleanly.
set -euo pipefail
cd "$(dirname "$0")/.."
WORKERS="${WORKERS:-4}"
desk build --stage fetch --workers "$WORKERS"        # EarlyPrint shards -> token streams
desk build --stage aggregate                          # earliest dates, decades, holdout
desk build --stage kwic --workers "$WORKERS"         # KWIC lines in printed spelling
desk build --stage ngrams --workers "$WORKERS"       # bigrams/trigrams for idiom lookups
desk build --stage scan --workers "$WORKERS"         # watch-list phrases, ?! and !? runs
desk build --stage holdout                            # regularised held-out texts
desk build --stage etymology                          # kaikki.org Wiktextract, streamed
desk watchlist --annotate                             # corpus dates into watchlist.yaml
desk build --stage clean                              # drop intermediates (keeps token streams)
desk info
