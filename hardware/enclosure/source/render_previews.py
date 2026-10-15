#!/usr/bin/env python3
"""Render PNG previews (white background) from the meshes written by enclosure.py."""
import json
from pathlib import Path
import numpy as np
import pyvista as pv

ENC = Path(__file__).resolve().parent.parent
M = ENC / "previews" / "_mesh"
OUT = ENC / "previews"
info = json.loads((M / "info.json").read_text())
X0, Y0, X1, Y1 = info["OUT"]
duct_w, duct_h = info["duct"]
duct_cx = (info["J1_X"] + info["usb_exit_x"]) / 2

def load(n): return pv.read(str(M / f"{n}.stl"))
base, lid, pcb, parts, usb = (load(n) for n in ("base", "lid", "pcb", "parts", "usb"))
duct = pv.Box(bounds=(duct_cx - duct_w / 2, duct_cx + duct_w / 2, Y0 - 45, Y0 - 3, 0, duct_h))
wall = pv.Box(bounds=(X0 - 15, X1 + 15, Y0 - 50, Y1 + 15, -3, 0))
C = dict(base="#d9d9de", lid="#9ec3e6", pcb="#2e7d32", parts="#444444", usb="#111111", duct="#f5deb3", wall="#eeeeee")

def shot(name, meshes, cam, title, size=(1400, 1050), parallel=False, zoom=1.0):
    p = pv.Plotter(off_screen=True, window_size=size)
    p.set_background("white")
    for m, col, op in meshes:
        p.add_mesh(m, color=col, opacity=op, smooth_shading=False, show_edges=False, specular=0.2)
    p.camera_position = cam
    if parallel: p.enable_parallel_projection()
    p.camera.zoom(zoom)
    p.add_text(title, font_size=11, color="black", position="upper_left")
    p.screenshot(str(OUT / name)); p.close(); print("wrote", name)

cx, cy, cz = (X0 + X1) / 2, (Y0 + Y1) / 2, info["D"] / 2
D = 230
shot("assembly_front.png", [(base, C["base"], 1), (lid, C["lid"], 1), (usb, C["usb"], 1), (duct, C["duct"], 0.6), (wall, C["wall"], 1)],
     [(cx + 90, cy - 120, cz + 190), (cx, cy - 10, cz), (0, 0, 1)], "Assembly (wall side = Z0), cable duct below (example 20x10 mm)")
shot("assembly_inside_no_lid.png", [(base, C["base"], 1), (pcb, C["pcb"], 1), (parts, C["parts"], 1), (usb, C["usb"], 1)],
     [(cx, cy - 60, cz + 200), (cx, cy, cz), (0, 1, 0)], "Base + PCB + USB-C plug/cable (lid removed)", zoom=1.1)
tr = lambda m, dz: m.translate((0, 0, dz), inplace=False)
shot("exploded.png", [(base, C["base"], 1), (tr(pcb, 25), C["pcb"], 1), (tr(parts, 25), C["parts"], 1), (tr(lid, 60), C["lid"], 1)],
     [(cx + 150, cy - 170, cz + 170), (cx, cy, cz + 30), (0, 0, 1)], "Exploded: base / PCB / lid")
shot("bottom_view_cable_exits.png", [(base, C["base"], 1), (lid, C["lid"], 1), (pcb, C["pcb"], 1), (parts, C["parts"], 1), (usb, C["usb"], 1)],
     [(cx, Y0 - D, cz), (cx, cy, cz), (0, 0, 1)], "Bottom view: RJ11 (J1) slot left, USB-C cable exit right; wall at the bottom of the image", parallel=True, zoom=1.3)
shot("back_view_wall_hole.png", [(base, C["base"], 1), (lid, C["lid"], 1), (pcb, C["pcb"], 1), (parts, C["parts"], 1)],
     [(cx, cy, -D), (cx, cy, cz), (0, 1, 0)], "Back (wall) side: hole for the phone cable from the wall", parallel=True, zoom=1.3)
shot("front_view.png", [(base, C["base"], 1), (lid, C["lid"], 1)],
     [(cx, cy, D + 40), (cx, cy, cz), (0, 1, 0)], "Front (lid): R7 trimmer hole, vents, 4 screws", parallel=True, zoom=1.3)
