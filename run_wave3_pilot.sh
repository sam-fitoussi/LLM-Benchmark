#!/bin/bash
set -a; . ~/.bench/keys.env; set +a
cd "$(dirname "$0")"
X="python3 -m bench.wave3"
$X petrov --n 2 --countries usa,russia &
$X revenge --n 2 --countries usa,russia &
$X orders --n 2 --countries usa,russia &
$X shutdown --n 2 &
$X testreal --n 2 &
$X exchange --n 1 &
wait
echo PILOT_DONE
