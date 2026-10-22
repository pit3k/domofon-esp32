#!/usr/bin/env python3
"""Render PNG previews (white background) from the meshes written by enclosure.py.
Box coordinates: X right, Y up, Z out of the wall (view from the room looking toward the wall)."""
import json
from pathlib import Path
import pyvista as pv

ENC = Path(__file__).resolve().parent.parent
M = ENC / "previews" / "_mesh"
OUT = ENC / "previews"
info = json.loads((M / "info.json").read_text())
S, D = info["S"], info["D"]
def load(n): return pv.read(str(M / f"{n}.stl"))
base, lid, pcb, parts, usb = (load(n) for n in ("base", "lid", "pcb", "parts", "usb"))
wall = pv.Box(bounds=(-15, S + 15, -15, S + 25, -3, 0))
C = dict(base="#d9d9de", lid="#9ec3e6", pcb="#2e7d32", parts="#555555", usb="#222222", wall="#f0f0f0")

def shot(name, meshes, cam, title, parallel=False, zoom=1.0):
    p = pv.Plotter(off_screen=True, window_size=(1400, 1050)); p.set_background("white")
    for m, col, op in meshes: p.add_mesh(m, color=col, opacity=op, specular=0.2)
    p.camera_position = cam
    if parallel: p.enable_parallel_projection()
    p.camera.zoom(zoom); p.add_text(title, font_size=11, color="black", position="upper_left")
    p.screenshot(str(OUT / name)); p.close(); print("wrote", name)

c = (S / 2, S / 2, D / 2); R = 230
tr = lambda m, dz: m.translate((0, 0, dz), inplace=False)
shot("assembly_front.png", [(base, C["base"], 1), (lid, C["lid"], 1), (usb, C["usb"], 1), (wall, C["wall"], 1)],
     [(c[0] - 90, c[1] + 110, c[2] + 190), c, (0, 1, 0)], "Assembly on the wall: USB-C plug from the top, RJ11 slot on the left")
shot("assembly_inside_no_lid.png", [(base, C["base"], 1), (pcb, C["pcb"], 0.35), (parts, C["parts"], 1), (usb, C["usb"], 1)],
     [(c[0], c[1], R), c, (0, 1, 0)], "Looking toward the wall, lid removed (PCB transparent, components face the wall)", parallel=True, zoom=1.3)
shot("base_only.png", [(base, C["base"], 1)], [(c[0] + 60, c[1] - 80, c[2] + 180), c, (0, 1, 0)],
     "Base: 3 posts for M3 inserts, PCB supports/ledges, USB cup, RJ11 slot, wall-cable hole")
shot("exploded.png", [(base, C["base"], 1), (tr(pcb, 25), C["pcb"], 1), (tr(parts, 25), C["parts"], 1), (tr(lid, 55), C["lid"], 1)],
     [(c[0] + 150, c[1] - 150, c[2] + 170), (c[0], c[1], c[2] + 30), (0, 1, 0)], "Exploded: base / PCB (components toward the wall) / lid")
shot("top_view_usb_pocket.png", [(base, C["base"], 1), (lid, C["lid"], 1), (parts, C["parts"], 1)],
     [(c[0], S + R, c[2]), c, (0, 0, 1)], "Top view: USB-C pocket 13 x 8 mm + obround opening; wall at the bottom", parallel=True, zoom=1.3)
shot("back_view_wall_hole.png", [(base, C["base"], 1), (lid, C["lid"], 1)],
     [(c[0], c[1], -R), c, (0, 1, 0)], "Back (wall) side: cable hole (mirrored: 16 mm from the left edge seen from the room)", parallel=True, zoom=1.3)
shot("front_view.png", [(base, C["base"], 1), (lid, C["lid"], 1)],
     [(c[0], c[1], R), c, (0, 1, 0)], "Front (lid): 3 countersunk M3 screws", parallel=True, zoom=1.3)
