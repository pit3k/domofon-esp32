#!/bin/bash
# Export Gerbers + Excellon drill files (mm) for CNC milling into ../gerbers/
# usage: export_gerbers.sh [board.kicad_pcb]
# Only B.Cu is milled. F.Cu contains just the wire jumper(s) modelled as a track so that DRC sees
# the connection -> it is renamed to *-F_Cu-jumpers_DO_NOT_MILL.gtl.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; PCB="$(dirname "$HERE")"
B="${1:-$PCB/domofon.kicad_pcb}"; OUTD="$PCB/gerbers"; N=$(basename "${B%.kicad_pcb}")
mkdir -p "$OUTD"; rm -f "$OUTD"/*
kicad-cli pcb export gerbers --layers "F.Cu,B.Cu,F.SilkS,Edge.Cuts,F.Fab" --use-drill-file-origin -o "$OUTD/" "$B"
kicad-cli pcb export drill --format excellon --excellon-units mm --excellon-separate-th \
  --generate-map --map-format gerberx2 --drill-origin absolute -o "$OUTD/" "$B"
mv "$OUTD/$N-F_Cu.gtl" "$OUTD/$N-F_Cu-jumpers_DO_NOT_MILL.gtl"
sed -i "s/$N-F_Cu.gtl/$N-F_Cu-jumpers_DO_NOT_MILL.gtl/" "$OUTD/$N-job.gbrjob"
ls -1 "$OUTD"
