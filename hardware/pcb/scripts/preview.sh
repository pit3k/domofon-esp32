#!/bin/bash
# usage: preview.sh board.kicad_pcb out.png [layers] [extra kicad-cli args, e.g. --mirror]
B=$1; O=$2; L=${3:-B.Cu,F.SilkS,Edge.Cuts,F.CrtYd}; shift 3 2>/dev/null || shift $#
TMP=$(mktemp --suffix=.svg)
kicad-cli pcb export svg --layers "$L" --mode-single --exclude-drawing-sheet --page-size-mode 2 "$@" -o "$TMP" "$B" >/dev/null 2>&1 || { echo svg export failed; exit 1; }
rsvg-convert -b white -z 6 "$TMP" -o "$O"
rm -f "$TMP"
