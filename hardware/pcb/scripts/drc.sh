#!/bin/bash
# usage: drc.sh [board.kicad_pcb]
#   no argument: checks ../domofon.kicad_pcb and writes ../drc-report.txt
#   with argument: writes <board>.drc.rpt next to the board
# Regenerates .kicad_pro/.kicad_dru (net classes + custom rules) next to the board,
# runs KiCad DRC (all severities) and prints a summary.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; PCB="$(dirname "$HERE")"
if [ -z "$1" ]; then B="$PCB/domofon.kicad_pcb"; RPT="$PCB/drc-report.txt"
else B="$1"; RPT="${B%.kicad_pcb}.drc.rpt"; fi
python3 "$HERE/mkproject.py" "${B%.kicad_pcb}"
kicad-cli pcb drc --severity-all --format report -o "$RPT" "$B" >/dev/null 2>&1 || true
grep -E "^\*\* Found|^\[" "$RPT" | sed 's/;.*//' | sort | uniq -c
