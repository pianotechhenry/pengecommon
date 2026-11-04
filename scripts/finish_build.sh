#!/usr/bin/env bash
# Finish an index build after (or while) the fetch stage runs: waits for any
# running fetch, re-runs it until every shard is extracted (it resumes), then
# runs the remaining stages in order.  Log: data/build.log
set -uo pipefail
cd "$(dirname "$0")/.."
LOG=data/build.log
say() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }
while pgrep -f "desk.build.fetch" >/dev/null; do sleep 30; done
for attempt in 1 2 3; do
  done_n=$(ls data/stageA/done 2>/dev/null | wc -l)
  total=$(( $(grep -c submodule data/stageA/super-eebo/.gitmodules) + $(grep -c submodule data/stageA/super-ecco/.gitmodules) ))
  [ "$done_n" -ge "$total" ] && break
  say "fetch incomplete ($done_n/$total), attempt $attempt"
  desk build --stage fetch >> "$LOG" 2>&1
done
say "fetch complete: $(ls data/stageA/done | wc -l) shards"
for st in aggregate clean kwic ngrams scan holdout; do
  say "stage $st"
  if ! desk build --stage "$st" >> "$LOG" 2>&1; then say "stage $st FAILED"; exit 1; fi
done
say "annotate watch list"
desk watchlist --annotate >> "$LOG" 2>&1
desk build --stage clean >> "$LOG" 2>&1
desk info | tee -a "$LOG"
say "BUILD DONE"
