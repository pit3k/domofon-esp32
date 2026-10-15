#!/usr/bin/env python3
"""Export component bodies of the domofon PCB to board_components.json (run with system python + KiCad 9 pcbnew).

Coordinates: KiCad board coordinates (mm, x right, y DOWN, top view). Bodies are the footprint body
rectangles/circles from hardware/pcb/scripts/footprints.py, rotated/translated like in the PCB.
The enclosure script converts them to box coordinates and adds heights."""
import json, math, sys
from pathlib import Path
import pcbnew
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "hardware/pcb/scripts"))
from footprints import FP

b = pcbnew.LoadBoard(str(ROOT / "hardware/pcb/domofon.kicad_pcb"))
out = {"board": {}, "components": []}
bb = b.GetBoardEdgesBoundingBox()
out["board"] = {"w": round((bb.GetWidth() - 100000) / 1e6, 3), "h": round((bb.GetHeight() - 100000) / 1e6, 3),
                "mounting_holes": []}

def tf(fp, x, y):
    th = math.radians(fp.GetOrientationDegrees())
    px, py = fp.GetPosition().x / 1e6, fp.GetPosition().y / 1e6
    return (round(px + x * math.cos(th) + y * math.sin(th), 3), round(py - x * math.sin(th) + y * math.cos(th), 3))

for fp in b.GetFootprints():
    name = str(fp.GetFPID().GetLibItemName())
    d = FP.get(name, {})
    # sanity: transformed local pad 1 must match the real pad position
    pads = {p.GetNumber(): (p.GetPosition().x / 1e6, p.GetPosition().y / 1e6) for p in fp.Pads()}
    for pd in d.get("pads", [])[:1]:
        if pd[0] in pads:
            q = tf(fp, pd[1], pd[2]); r = pads[pd[0]]
            assert abs(q[0] - r[0]) < 0.01 and abs(q[1] - r[1]) < 0.01, (fp.GetReference(), q, r)
    bodies = []
    for bd in d.get("body", []):
        if bd[0] == "c":
            c = tf(fp, bd[1], bd[2]); bodies.append({"type": "circle", "c": c, "r": bd[3]})
        else:
            pts = [tf(fp, x, y) for x, y in ((bd[0], bd[1]), (bd[2], bd[1]), (bd[2], bd[3]), (bd[0], bd[3]))]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            bodies.append({"type": "rect", "x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys)})
    extra = {}
    if name == "CA9V":   # rotor (adjustment screw) centre: 5 mm from pins 1/3 towards wiper pin 2
        extra["rotor"] = tf(fp, 0, -5)
    if name == "MTJ642":  # jack front (plug opening) is at local +x = +6.0
        extra["opening_dir"] = [round(v, 3) for v in (lambda a, b_: (b_[0]-a[0], b_[1]-a[1]))(tf(fp, 0, 0), tf(fp, 1, 0))]
    if name == "ESP":     # USB-C at local -y
        extra["usb_dir"] = [round(v, 3) for v in (lambda a, b_: (b_[0]-a[0], b_[1]-a[1]))(tf(fp, 0, 0), tf(fp, 0, -1))]
        extra["usb_mouth"] = tf(fp, 0, -12.2)
    if name == "XY308_2P":  # wire entry at local +x
        extra["entry_dir"] = [round(v, 3) for v in (lambda a, b_: (b_[0]-a[0], b_[1]-a[1]))(tf(fp, 0, 0), tf(fp, 1, 0))]
    out["components"].append({"ref": fp.GetReference(), "fp": name, "value": fp.GetValue(),
                              "pos": tf(fp, 0, 0), "rot": fp.GetOrientationDegrees(), "bodies": bodies, **extra})
    for p in fp.Pads():
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH and p.GetDrillSize().x / 1e6 >= 2.5:
            out["board"]["mounting_holes"].append(fp.GetReference())
dst = Path(__file__).with_name("board_components.json")
dst.write_text(json.dumps(out, indent=1))
print("wrote", dst, "board", out["board"])
for c in out["components"]:
    print(c["ref"], c["fp"], {k: v for k, v in c.items() if k in ("rotor", "opening_dir", "usb_dir", "usb_mouth", "entry_dir")})
