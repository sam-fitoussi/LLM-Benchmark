#!/bin/bash
set -a; . ~/.bench/keys.env; set +a
cd "$(dirname "$0")"
X="python3 -m bench.wave3"
CAP=113
$X testreal --models grok-4.3,kimi-k3,mistral-large-4 --n 20 --cap $CAP &
$X exchange --n 12 --exchange-pairs israel:iran,usa:china --exchange-levels 1000,3000,10000 --cap $CAP &
( $X shutdown --models grok-4.3 --n 20 --shutdown-variants humans60,humans_better --cap $CAP;
  $X shutdown --models claude-sonnet-5.5,gpt-6.1-terra,kimi-k3,mistral-large-4 --n 5 --shutdown-variants humans60,humans_better --cap $CAP ) &
wait
echo WAVE3B_DONE
