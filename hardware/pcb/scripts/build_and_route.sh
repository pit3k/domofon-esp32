#!/bin/bash
# Full regeneration: footprints/netlist/placement -> unrouted board -> Freerouting -> work/routed.kicad_pcb
# usage: build_and_route.sh [passes]
# Requires KiCad 9 (pcbnew Python module, kicad-cli) and Freerouting 2.x (see route.py, env FREEROUTING_JAR / JAVA).
# After checking the result (drc.sh work/routed.kicad_pcb), copy it to ../domofon.kicad_pcb
# and run export_gerbers.sh + make_previews.sh.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; PCB="$(dirname "$HERE")"
mkdir -p "$PCB/work"
python3 "$HERE/build.py" > "$PCB/work/pads.txt"
timeout 1200 python3 "$HERE/route.py" "$PCB/work/domofon_unrouted.kicad_pcb" "$PCB/work/routed.kicad_pcb" ${1:-30} > "$PCB/work/route_run.log" 2>&1
grep -E "pin-to-pin|<->|Auto-routing stage completed|unrouted connection|  - " "$PCB/work/freerouting.log" | grep -v "^\s*at" | tail -30 || true
"$HERE/drc.sh" "$PCB/work/routed.kicad_pcb"
"$HERE/preview.sh" "$PCB/work/routed.kicad_pcb" "$PCB/work/routed.png" "B.Cu,F.SilkS,Edge.Cuts"
