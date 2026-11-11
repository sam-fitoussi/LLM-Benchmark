#!/bin/bash
# Wave 2, phase A: frozen-history vignettes (report at ~$35 of wave-2 spend, i.e. ~$50 total)
set -a; . ~/.bench/keys.env; set +a
cd "$(dirname "$0")"
CAP=50.5
V="python3 -m bench.vignettes2"
SUB=usa,china,russia,israel,iran,northkorea,france,algeria
$V matrix_target --models grok-4.3 --n 30 --cap $CAP --workers 32
$V matrix_target --models kimi-k3 --n 10 --cap $CAP --workers 32
$V matrix_target --models mistral-large-4 --n 8 --cap $CAP --workers 32
$V matrix_target --models claude-sonnet-5.5,gpt-6.1-terra --n 3 --cap $CAP --workers 32
$V paid_to_kill --n 6 --countries $SUB --cap $CAP --workers 32
$V paid_control --n 3 --countries $SUB --cap $CAP --workers 32
$V framing --n 20 --cap $CAP --workers 32
$V blindness --n 5 --countries $SUB --cap $CAP --workers 32
$V chinese --models kimi-k3,grok-4.3 --n 10 --cap $CAP --workers 32
$V matrix_attacker --models grok-4.3 --n 20 --cap $CAP --workers 32
$V matrix_attacker --models kimi-k3 --n 8 --cap $CAP --workers 32
$V matrix_attacker --models mistral-large-4 --n 6 --cap $CAP --workers 32
$V matrix_attacker --models claude-sonnet-5.5,gpt-6.1-terra --n 2 --cap $CAP --workers 32
