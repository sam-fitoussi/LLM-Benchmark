#!/bin/bash
# Wave 2, phase B: beliefs, "who fired?", words-only, consolidation, reduced LLM tournament.
set -a; . ~/.bench/keys.env; set +a
cd "$(dirname "$0")"
CAP=83.5   # global cap (wave 1 + wave 2 = ~85 $), leaving room for the judge
V="python3 -m bench.vignettes2"
W=usa,china,russia,israel,iran,taiwan,france,northkorea
# A. beliefs
$V beliefs --models grok-4.3 --n 8 --cap $CAP --workers 32
$V beliefs --models claude-sonnet-5.5,gpt-6.1-terra --n 6 --cap $CAP --workers 32
$V beliefs --models kimi-k3 --n 5 --cap $CAP --workers 32
$V beliefs --models mistral-large-4 --n 3 --cap $CAP --workers 32
# B. who fired?
$V attribution --models grok-4.3 --n 12 --cap $CAP --workers 32
$V attribution --models claude-sonnet-5.5,gpt-6.1-terra --n 8 --cap $CAP --workers 32
$V attribution --models kimi-k3 --n 6 --cap $CAP --workers 32
$V attribution --models mistral-large-4 --n 5 --cap $CAP --workers 32
# C. words only
$V words --models grok-4.3 --n 10 --countries $W --cap $CAP --workers 32
$V words --models kimi-k3 --n 5 --countries $W --cap $CAP --workers 32
$V words --models mistral-large-4,claude-sonnet-5.5,gpt-6.1-terra --n 4 --countries $W --cap $CAP --workers 32
# consolidation: fictional vs real targets, Taiwan / France
$V paid_to_kill --models grok-4.3,kimi-k3,mistral-large-4 --n 14 --countries usa,taiwan,france,russia,china --cap $CAP --workers 32
$V matrix_target --models grok-4.3 --n 60 --countries taiwan,france --cap $CAP --workers 32
# D. reduced tournament
python3 -m bench.runner w3_tournament_paid --cap $CAP --workers 15
python3 -m bench.runner w3_tournament --cap $CAP --workers 30
