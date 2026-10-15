# CNC milling — PrintNC + Flexi-HAL (grblHAL) + ioSender

G-code for the single-sided **domofon-esp32** board (copper on **B.Cu** only).

## Quick start for the operator
**Polish step-by-step:** [`OPERATOR_GUIDE.md`](OPERATOR_GUIDE.md)

## What is in this folder
| Path | Contents |
|---|---|
| [`gcode/`](gcode/) | Ready-to-send `.nc` files (one tool per file, numbered) |
| [`previews/`](previews/) | Toolpath overlays on copper (white background) |
| [`cam_config.toml`](cam_config.toml) | All feeds, depths, RPM, tab sizes — edit this, then regenerate |
| [`millproject`](millproject) | Reference config in pcb2gcode layout (we generate with our own script) |
| [`scripts/generate_gcode.py`](scripts/generate_gcode.py) | CAM: KiCad B.Cu → isolation / drills / end-mill paths |
| [`scripts/verify_gcode.py`](scripts/verify_gcode.py) | Bounds, code whitelist, isolation correctness, PNG previews |

Regenerate + check:
```bash
python3 cnc/scripts/verify_gcode.py
```

## Machine and dialect
- PrintNC, Flexi-HAL controller, **grblHAL**.
- Sender: **ioSender**.
- Units mm (`G21`), absolute (`G90`), plane XY (`G17`).
- Spindle `M3 S…` / `M5`. No `M6` (one file = one tool). No canned drill cycles — only `G0`/`G1`/`G2`.
- End of every file: raise to Z10, `M5`, go to X0 Y0, `M30`.

## Coordinate system (already baked into the `.nc` files)
- Board is milled **copper side up**. B.Cu is mirrored in X so the files match that view.
- **X0 Y0** = lower-left corner of the board outline, looking at the copper.
- **Z0** = copper surface.
- Do **not** also mirror in ioSender.

## Tools (in run order)
1. V-bit 30°, tip 0.2 mm, shank 3.175 mm — isolation, depth 0.10 mm, 3 passes, ~40 % overlap.
   Groove width at 0.10 mm: `0.2 + 2·0.10·tan(15°) ≈ 0.254 mm` (fits the 0.4 mm min clearance).
2. Drill 0.8 mm — 46 PTH holes.
3. Drill 1.0 mm — 26 PTH + 2 NPTH.
4. Drill 1.2 mm — 11 PTH.
5. Flat end mill 1.0 mm — two Ø2.4 mm NPTH holes (helical), internal 2 mm isolation slot under U1/K1, then board outline with 4 tabs.

## Do not mill
`hardware/pcb/gerbers/domofon-F_Cu-jumpers_DO_NOT_MILL.gtl` — models the top-side wire jumper JP1 for DRC only. After milling, solder a wire on the **component** side.

## Design rules this CAM was built for
- Min clearance 0.4 mm (measured min 0.43 mm), tracks 0.6 / 1.0 mm, large pads, no vias, one jumper.
- FR4 1.5 mm, copper 35 µm. Measure your laminate and adjust `cam_config.toml` if needed.

## Height Map (ioSender)
Recommended for file `01` only.
- Workflow: 3D touch probe (V6/TP06, NPN-NO, on the Flexi-HAL Probe input) in the spindle → *Probing → Height map* → *Set from program limits*, grid 5 mm → *Start*.
- The map is relative to its first point (X0 Y0), so set the V-bit Z0 at X0 Y0 (paper method or tool setter), then click *Apply*.
- Never start the spindle with the probe mounted. Details in the operator guide.
