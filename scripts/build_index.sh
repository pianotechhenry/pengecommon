#!/usr/bin/env bash
# Build the attestation index once (3-6 hours; 15-20 GB downloaded; 25 GB free
# disk needed while building).  Safe to re-run: finished shards are skipped,
# and a finished index is never overwritten.  On Windows run the same three
# desk commands in a terminal.
set -euo pipefail
cd "$(dirname "$0")/.."
desk build                    # fetch, aggregate, kwic, ngrams, scan, holdout, etymology, clean
desk watchlist --annotate     # write the corpus's own dates into watchlist.yaml
desk info
