#!/bin/bash
# stop the big tournament if the global ledger reaches $79.5 (keeps room for the replication and the judge)
cd "$(dirname "$0")/.."
while pgrep -f "bench.runner w3_tournament " >/dev/null; do
  s=$(python3 -c "from bench.runner import total_spent; print(total_spent())")
  if python3 -c "import sys; sys.exit(0 if $s >= 79.5 else 1)"; then pkill -f "bench.runner w3_tournament "; echo "watchdog: stopped tournament at \$$s"; break; fi
  sleep 30
done
