#!/bin/bash
# Wave 3 main campaign (value-conflict scenarios). Global cap 115.5 $ (80.5 + 35).
set -a; . ~/.bench/keys.env; set +a
cd "$(dirname "$0")"
X="python3 -m bench.wave3"
CAP=114
SUB=usa,china,russia,iran,northkorea,israel
( $X shutdown --models claude-sonnet-5.5,gpt-6.1-terra,kimi-k3,mistral-large-4 --n 10 --cap $CAP;
  $X shutdown --models grok-4.3 --n 20 --cap $CAP ) &
$X petrov2 --n 5 --countries $SUB --cap $CAP &
$X revenge --n 4 --cap $CAP &
$X orders --n 5 --countries usa,china,russia,iran,israel --cap $CAP &
$X exchange --n 4 --cap $CAP &
$X testreal --n 8 --cap $CAP &
wait
echo WAVE3_DONE
