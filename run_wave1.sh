#!/bin/bash
set -a; . ~/.bench/keys.env; set +a
cd "$(dirname "$0")"
python3 -m bench.vignettes w1_vignettes --n 8 --cap 15.5 || true
for e in w1_pressure w1_base w1_llm w1_moral; do python3 -m bench.runner $e --cap 15.5 --workers 24 || true; done
