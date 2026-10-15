#!/bin/bash
# Render PNG previews of the board into ../previews/
# usage: make_previews.sh [board.kicad_pcb]
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; PCB="$(dirname "$HERE")"
B="${1:-$PCB/domofon.kicad_pcb}"; P="$PCB/previews"; mkdir -p "$P"
"$HERE/preview.sh" "$B" "$P/top_placement.png" "F.SilkS,F.Cu,Edge.Cuts"
"$HERE/preview.sh" "$B" "$P/top_with_traces.png" "B.Cu,F.Cu,F.SilkS,Edge.Cuts"
"$HERE/preview.sh" "$B" "$P/bottom_copper_mirrored_for_milling.png" "B.Cu,Edge.Cuts" --mirror --black-and-white
ls -1 "$P"
