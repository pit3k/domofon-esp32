# CNC milling (isolation routing)

**Status: TODO — G-code (`.nc`) files have not been generated yet.**
The input for CAM is the Gerber/Excellon set in [`../hardware/pcb/gerbers/`](../hardware/pcb/gerbers/).

## Machine
- **PrintNC** (steel-frame DIY CNC) with **Flexi-HAL** controller running **grblHAL**.
- G-code dialect: plain grbl/grblHAL (G0/G1/G2/G3, G20/G21, G90, M3/M5, S in RPM). No tool-change (M6) in one file — one file per tool.

## Tools
| Operation | Tool |
|---|---|
| Isolation (B.Cu) | V-bit, carbide, 30° tip angle, 0.2 mm tip, 3.175 mm (1/8") shank ("XCAN 30° × 0.2 mm") |
| Drilling | 0.8 / 1.0 / 1.2 mm PTH holes, 1.0 and 2.4 mm NPTH (J1 pegs) — drill bits or end mill helical interpolation for 2.4 mm |
| Board outline + slot under U1/K1 | end mill (e.g. 1.0–2.0 mm), outline from `domofon-Edge_Cuts.gm1` |

## Files to use
| File | Use |
|---|---|
| `domofon-B_Cu.gbl` | **mill this** — copper is on the bottom only (components on top) |
| `domofon-PTH.drl`, `domofon-NPTH.drl` | drilling (Excellon, mm, absolute origin) |
| `domofon-Edge_Cuts.gm1` | outline (rounded corners R1) + internal 2 mm isolation slot |
| `domofon-F_Cu-jumpers_DO_NOT_MILL.gtl` | **do not mill** — only models the top-side wire jumper JP1 for DRC |
| `domofon-F_Silkscreen.gto`, `domofon-F_Fab.gbr` | reference / assembly drawing only |

The bottom layer must be **mirrored** when the board is flipped for milling (see
[`../hardware/pcb/previews/bottom_copper_mirrored_for_milling.png`](../hardware/pcb/previews/bottom_copper_mirrored_for_milling.png)).
Mirror the copper and the drill files around the same axis.

## Design rules the PCB was made for
- Minimum clearance 0.4 mm (measured minimum 0.43 mm), signal tracks 0.6 mm, power and line tracks 1.0 mm.
- Large pads (≥ 1.7 mm), no vias, one wire jumper.
- With a 30° V-bit and 0.2 mm tip, cut width ≈ 0.2 + 2·depth·tan(15°) ≈ 0.2 + 0.536·depth.
  At 0.1 mm depth → ~0.25 mm; at 0.3 mm → ~0.36 mm, i.e. still below the 0.4 mm clearance.

## Planned CAM parameters (to be verified on scrap laminate)
- Tool: V 30° / 0.2 mm, isolation depth 0.08–0.12 mm (use height probing / autolevelling; grblHAL supports `G38.2` probing).
- 2–3 isolation passes, ~40 % overlap.
- Spindle ~12 000–20 000 RPM, feed ~150–300 mm/min, plunge ~50–100 mm/min.
- Candidate CAM tools: FlatCAM / FlatCAM Evo, pcb2gcode, or the KiCad → FlatCAM workflow; output with a grbl post-processor.
