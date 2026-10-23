#!/usr/bin/env python3
"""Render PNG previews (white background) from the meshes written by enclosure.py (layout v9).
Box coordinates: X right, Y up, Z out of the wall (view from the room looking toward the wall)."""
import json
from pathlib import Path
import pyvista as pv

ENC = Path(__file__).resolve().parent.parent
M = ENC / "previews" / "_mesh"
OUT = ENC / "previews"
info = json.loads((M / "info.json").read_text())
W, H, D = info.get("W", info["S"]), info.get("H", info["S"]), info["D"]
def load(n): return pv.read(str(M / f"{n}.stl"))
base, lid, pcb, parts, usb, rj11 = (load(n) for n in ("base", "lid", "pcb", "parts", "usb", "rj11"))
wall = pv.Box(bounds=(-15, W + 15, -15, H + 25, -3, 0))
C = dict(base="#d9d9de", lid="#9ec3e6", pcb="#2e7d32", parts="#555555", usb="#222222", rj11="#1e88e5", wall="#f0f0f0")

def shot(name, meshes, cam, title, parallel=False, zoom=1.0):
    p = pv.Plotter(off_screen=True, window_size=(1400, 1050)); p.set_background("white")
    for m, col, op in meshes: p.add_mesh(m, color=col, opacity=op, specular=0.2)
    p.camera_position = cam
    if parallel: p.enable_parallel_projection()
    p.camera.zoom(zoom); p.add_text(title, font_size=11, color="black", position="upper_left")
    p.screenshot(str(OUT / name)); p.close(); print("wrote", name)

c = (W / 2, H / 2, D / 2); R = 250
tr = lambda m, dz: m.translate((0, 0, dz), inplace=False)
shot("assembly_front.png", [(base, C["base"], 1), (lid, C["lid"], 1), (usb, C["usb"], 1), (rj11, C["rj11"], 1), (wall, C["wall"], 1)],
     [(c[0] - 110, c[1] + 110, c[2] + 200), c, (0, 1, 0)], "Assembly on the wall (93 x 68 x 26 mm): USB-C top, 5x2.5 mm cable exit + reinforced plunger on the left")
shot("assembly_inside_no_lid.png", [(base, C["base"], 1), (pcb, C["pcb"], 0.35), (parts, C["parts"], 1), (usb, C["usb"], 1), (rj11, C["rj11"], 1)],
     [(c[0], c[1], R), c, (0, 1, 0)], "Looking toward the wall, lid removed (PCB shifted +25 mm right, RJ11 plug inside left chamber)", parallel=True, zoom=1.25)
shot("base_only.png", [(base, C["base"], 1)], [(c[0] + 70, c[1] - 90, c[2] + 200), c, (0, 1, 0)],
     "Base: 4 posts for M3 inserts, PCB supports/guides, USB cup, 5x2.5 mm left cable guide channel, Ø12 wall hole")
shot("exploded.png", [(base, C["base"], 1), (tr(pcb, 25), C["pcb"], 1), (tr(parts, 25), C["parts"], 1), (tr(rj11, 25), C["rj11"], 1), (tr(lid, 60), C["lid"], 1)],
     [(c[0] + 160, c[1] - 160, c[2] + 185), (c[0], c[1], c[2] + 30), (0, 1, 0)], "Exploded: base / PCB + RJ11 plug / lid with reinforced 5 mm cable plunger")
shot("top_view_usb_pocket.png", [(base, C["base"], 1), (lid, C["lid"], 1), (parts, C["parts"], 1)],
     [(c[0], H + R, c[2]), c, (0, 0, 1)], "Top view: USB-C pocket 13 x 8 mm + obround opening at X = 71.1 mm; wall at the bottom", parallel=True, zoom=1.25)
shot("back_view_wall_hole.png", [(base, C["base"], 1), (lid, C["lid"], 1)],
     [(c[0], c[1], -R), c, (0, 1, 0)], "Back (wall) side: Ø12 cable hole at (16.0; 15.5) seen from the room", parallel=True, zoom=1.25)
shot("front_view.png", [(base, C["base"], 1), (lid, C["lid"], 1)],
     [(c[0], c[1], R), c, (0, 1, 0)], "Front (lid): 4 countersunk M3 screws (93 x 68 mm)", parallel=True, zoom=1.25)
