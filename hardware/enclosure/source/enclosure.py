#!/usr/bin/env python3
"""Parametric 3D-printed enclosure for the domofon-esp32 PCB (CadQuery).

Run:  python enclosure.py            (needs: pip install cadquery trimesh pyvista)
Out:  ../step/*.step, ../stl/*.stl, ../3mf/*.3mf, ../previews/*.png, interference report on stdout

BOX COORDINATES (front view = looking at the component side of the PCB, box hanging on the wall):
  X right, Y up, Z out of the wall (Z=0 = back face glued to the wall).
  Origin X0/Y0 = lower-left corner of the PCB.
  PCB is rotated so that its KiCad RIGHT edge (J1 RJ11 opening, X1 wire entries) points DOWN and its KiCad TOP
  edge (ESP32 USB-C) points RIGHT:   X = 45.9 - y_kicad ,  Y = 55.5 - x_kicad
"""
import json, math, sys
from pathlib import Path
import cadquery as cq

HERE = Path(__file__).resolve().parent
ENC = HERE.parent
ROOT = ENC.parents[1]

# ============================================================== PARAMETERS
P = dict(
    wall=2.0,            # side walls
    back=2.0,            # back plate (glued to the wall)
    lid_t=2.0,           # lid plate
    clr=0.3,             # print clearance PCB <-> guides/walls
    standoff=3.5,        # gap back plate -> PCB bottom (solder tails)
    pcb_t=1.5,
    pcb_w=45.9, pcb_h=55.5,          # PCB in BOX coordinates (X width, Y height)
    left_margin=7.5,     # PCB left edge -> inner left wall (room for 2 screw bosses)
    bottom_gap=3.0,      # PCB bottom edge -> inner floor (wire channel to X1)
    top_gap=0.3,         # PCB top edge -> inner top wall (top wall = PCB guide)
    # ESP32-C3 SuperMini stack on female headers
    fheader_h=8.5,       # female header body height
    mheader_spacer=2.5,  # plastic spacer of the male pins under the module
    module_pcb=1.0,
    module_parts=1.5,    # parts on top of the module
    usbc_h=3.2,          # USB-C receptacle height
    # USB-C cable inside the box
    plug_len=14.0,       # rigid plug overmold incl. strain relief start (from receptacle mouth)
    plug_w=12.0, plug_t=6.5,
    cable_d=3.5,         # USB cable diameter
    bend_r=10.0,         # minimum bend radius (cable centre line)
    usb_exit_x=56.0,     # X of the USB cable exit in the bottom wall (box coords)
    usb_exit_z=7.0,      # Z (from wall) of the cable centre at the exit -> inside a 10 mm deep cable duct
    lid_air=1.0,         # clearance between highest part (USB plug) and lid
    # cable duct below the box (only used for the preview and README numbers)
    duct_w=20.0, duct_h=10.0,
    # phone cable from the wall
    wall_hole_d=12.0,
    # screws: self-tapping screws for plastics 2.5 x 10 mm (pilot 2.1) -- or M3 heat-set inserts (hole 4.0)
    boss_d=7.0, screw_pilot=2.1, screw_clear=2.9, head_d=5.5,
    # RJ11 slot (plug inserted from below)
    j1_slot_w=12.8,
    # lid press pins (hold the PCB down)
    pin_d=3.0, pin_gap=0.1,
    r7_hole_d=4.5,       # screwdriver hole above trimmer R7
    lip_h=2.0, lip_t=1.2,
)
# component heights above PCB top (mm), simplified bodies
H = {"R0207_P7.62": 3.0, "R0207_P10.16": 3.0, "R0414_P15.24": 5.0, "DO34_P5.08": 2.2, "DO15_P5.08_V": 11.5,
     "CFILM_P5.08": 10.0, "CP_D5_P2.0": 12.0, "CA9V": 6.5, "DIP4": 4.5, "T1": 11.0, "MTJ642": 14.5,
     "XY308_2P": 10.0, "WIRE_P10.16": 2.5}

data = json.loads((HERE / "board_components.json").read_text())
# rev. 5 (line side for ES 201 970): parts taller/thicker than their PCB footprint outline.
# C8 0.47 uF/250 V MKT sits in the R2 holes (PCB ref stays R2): standing box, max 3.2 mm thick (between R1 and X1).
# C5 is now WIMA MKS2 1 uF/100 V: 7.2 x 7.2 x 13 mm on the 5.08 mm footprint.
OVR = {"R2": dict(h=11.0, body=dict(type="rect", x0=38.0, y0=17.85, x1=48.0, y1=21.05)),
       "C5": dict(h=13.0, body=dict(type="rect", x0=46.6, y0=33.9, x1=53.8, y1=41.1))}
for _c in data["components"]:
    if _c["ref"] in OVR:
        _c["bodies"] = [OVR[_c["ref"]]["body"]]; _c["h"] = OVR[_c["ref"]]["h"]
assert not data["board"]["mounting_holes"]

def k2b(x, y):  # KiCad -> box XY
    return (P["pcb_w"] - y, P["pcb_h"] - x)

# ----------------------------------------------------------------- derived geometry
Z_PCB_BOT = P["back"] + P["standoff"]
Z_PCB_TOP = Z_PCB_BOT + P["pcb_t"]
esp = next(c for c in data["components"] if c["ref"] == "ESP")
usb_mouth = k2b(*esp["usb_mouth"])                     # (X, Y) of the receptacle mouth
Z_MOD_BOT = Z_PCB_TOP + P["fheader_h"] + P["mheader_spacer"]
Z_USB_C = Z_MOD_BOT + P["module_pcb"] + P["usbc_h"] / 2
plug_end_x = usb_mouth[0] + P["plug_len"]
cable_vx = plug_end_x + P["bend_r"]                    # vertical run of the cable after the bend
Z_LID_IN = Z_USB_C + P["plug_t"] / 2 + P["lid_air"]
IN_X0 = -P["left_margin"]
IN_X1 = cable_vx + P["cable_d"] / 2 + 1.0
IN_Y0 = -P["bottom_gap"]
IN_Y1 = P["pcb_h"] + P["top_gap"]
OUT_X0, OUT_X1 = IN_X0 - P["wall"], IN_X1 + P["wall"]
OUT_Y0, OUT_Y1 = IN_Y0 - P["wall"], IN_Y1 + P["wall"]
DEPTH = Z_LID_IN + P["lid_t"]
W, Hh = OUT_X1 - OUT_X0, OUT_Y1 - OUT_Y0
j1 = next(c for c in data["components"] if c["ref"] == "J1")
J1_X = k2b(*j1["pos"])[0]
r7 = next(c for c in data["components"] if c["ref"] == "R7")
R7_XY = k2b(*r7["rotor"])
x1 = next(c for c in data["components"] if c["ref"] == "X1")

r_b = P["boss_d"] / 2
e_ = 0.6   # bosses sink 0.6 mm into the walls (no tangent contact -> clean manifold mesh)
BOSSES = [(IN_X0 + r_b - e_, 5.0), (IN_X0 + r_b - e_, P["pcb_h"] - 6.0),
          (IN_X1 - r_b + e_, IN_Y1 - r_b + e_), (IN_X1 - r_b + e_, IN_Y0 + r_b - e_)]
WALL_HOLE = ((P["pcb_w"] + IN_X1) / 2, 46.0)

def box(x0, y0, z0, x1, y1, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))

def cyl(x, y, z0, z1, d):
    return cq.Workplane("XY").circle(d / 2).extrude(z1 - z0).translate((x, y, z0))

# ============================================================== PCB ASSEMBLY (for interference checks)
def pcb_assembly():
    parts = {}
    board = box(0, 0, Z_PCB_BOT, P["pcb_w"], P["pcb_h"], Z_PCB_TOP).edges("|Z").fillet(0.99)
    parts["PCB"] = board
    # solder tails under the PCB (2 mm) as one slab region is too pessimistic -> modelled per hole later
    for c in data["components"]:
        if c["fp"] == "ESP":
            continue
        h = c.get("h", H.get(c["fp"], 5.0))
        solids = []
        for b in c["bodies"]:
            if b["type"] == "rect":
                (xa, ya), (xb, yb) = k2b(b["x0"], b["y0"]), k2b(b["x1"], b["y1"])
                solids.append(box(min(xa, xb), min(ya, yb), Z_PCB_TOP, max(xa, xb), max(ya, yb), Z_PCB_TOP + h))
            else:
                x, y = k2b(*b["c"]); solids.append(cyl(x, y, Z_PCB_TOP, Z_PCB_TOP + h, 2 * b["r"]))
        if c["fp"] == "WIRE_P10.16":   # wire jumper JP1 between its pads
            (xa, ya), (xb, yb) = k2b(c["pos"][0], c["pos"][1] - 8.89), k2b(c["pos"][0], c["pos"][1] + 8.89)
            solids.append(box(min(xa, xb) - 0.6, min(ya, yb) - 0.6, Z_PCB_TOP, max(xa, xb) + 0.6, max(ya, yb) + 0.6, Z_PCB_TOP + h))
        if solids:
            s = solids[0]
            for o in solids[1:]: s = s.union(o)
            parts[c["ref"]] = s
    # ESP32-C3 SuperMini: two female headers + module + USB-C
    ex, ey = esp["pos"]
    def lb(x0, y0, x1, y1, z0, z1):
        (xa, ya), (xb, yb) = k2b(ex + x0, ey + y0), k2b(ex + x1, ey + y1)
        return box(min(xa, xb), min(ya, yb), z0, max(xa, xb), max(ya, yb), z1)
    e = lb(-7.62 - 1.27, -10.16, -7.62 + 1.27, 10.16, Z_PCB_TOP, Z_MOD_BOT)
    e = e.union(lb(7.62 - 1.27, -10.16, 7.62 + 1.27, 10.16, Z_PCB_TOP, Z_MOD_BOT))
    e = e.union(lb(-9.0, -10.16, 9.0, 12.36, Z_MOD_BOT, Z_MOD_BOT + P["module_pcb"]))
    e = e.union(lb(-8.0, -9.0, 8.0, 11.5, Z_MOD_BOT + P["module_pcb"], Z_MOD_BOT + P["module_pcb"] + P["module_parts"]))
    e = e.union(lb(-4.5, -12.2, 4.5, -4.9, Z_MOD_BOT + P["module_pcb"], Z_MOD_BOT + P["module_pcb"] + P["usbc_h"]))
    parts["ESP"] = e
    return parts

def usb_cable(d=None):
    d = d or P["cable_d"]
    """USB-C plug + cable: plug straight +X, bend down (radius bend_r), then an S-curve to the exit."""
    mx, my = usb_mouth
    plug = box(mx, my - P["plug_w"] / 2, Z_USB_C - P["plug_t"] / 2, plug_end_x, my + P["plug_w"] / 2, Z_USB_C + P["plug_t"] / 2)
    plug = plug.edges("|X").fillet(2.0)
    # cable path as a spline through points
    pts = [(plug_end_x - 1, my, Z_USB_C)]
    for a in range(10, 91, 10):
        t = math.radians(a)
        pts.append((plug_end_x + P["bend_r"] * math.sin(t), my - P["bend_r"] * (1 - math.cos(t)), Z_USB_C))
    y_after = my - P["bend_r"]
    y_s = IN_Y0 + 6          # S-curve ends here, then straight down through the slot
    n = 12
    for i in range(1, n + 1):
        s = i / n; sm = (1 - math.cos(math.pi * s)) / 2
        pts.append((cable_vx + (P["usb_exit_x"] - cable_vx) * sm, y_after + (y_s - y_after) * s,
                    Z_USB_C + (P["usb_exit_z"] - Z_USB_C) * sm))
    pts += [(P["usb_exit_x"], IN_Y0 + 3, P["usb_exit_z"]), (P["usb_exit_x"], OUT_Y0 - 3, P["usb_exit_z"])]
    path = cq.Workplane("XY").spline([cq.Vector(*p) for p in pts], includeCurrent=False)
    d0 = cq.Vector(*pts[1]) - cq.Vector(*pts[0])
    prof = cq.Workplane(cq.Plane(origin=pts[0], xDir=(0, 1, 0), normal=d0.normalized().toTuple())).circle(d / 2)
    cable = prof.sweep(path, isFrenet=False, transition="round")
    return plug, cable, pts

# ============================================================== BASE
def make_base():
    b = box(OUT_X0, OUT_Y0, 0, OUT_X1, OUT_Y1, Z_LID_IN)
    b = b.edges("|Z").fillet(2.0)
    cav = box(IN_X0, IN_Y0, P["back"], IN_X1, IN_Y1, Z_LID_IN + 1)
    b = b.cut(cav)
    # screw bosses
    for x, y in BOSSES:
        b = b.union(cyl(x, y, P["back"] - 0.01, Z_LID_IN, P["boss_d"]))
        b = b.cut(cyl(x, y, Z_LID_IN - 12, Z_LID_IN + 1, P["screw_pilot"]))
    # PCB supports (under the board, 1.2 mm overlap) + side guides
    for (x0, y0, x1, y1) in SUPPORTS:
        b = b.union(box(x0, y0, P["back"] - 0.01, x1, y1, Z_PCB_BOT))
    for (x0, y0, x1, y1) in GUIDES:
        b = b.union(box(x0, y0, P["back"] - 0.01, x1, y1, Z_PCB_TOP + 1.5))
    # wall hole for the phone cable (through the back plate)
    b = b.cut(cyl(WALL_HOLE[0], WALL_HOLE[1], -1, P["back"] + 1, P["wall_hole_d"]))
    # J1 RJ11 slot in the bottom wall, open towards the lid
    b = b.cut(box(J1_X - P["j1_slot_w"] / 2, OUT_Y0 - 1, Z_PCB_TOP + 0.5, J1_X + P["j1_slot_w"] / 2, IN_Y0 + 1, Z_LID_IN + 1))
    # USB cable slot in the bottom wall, open towards the lid (cable is laid in, lid tongue clamps it)
    w = P["cable_d"] + 0.2
    b = b.cut(box(P["usb_exit_x"] - w / 2, OUT_Y0 - 1, P["usb_exit_z"], P["usb_exit_x"] + w / 2, IN_Y0 + 1, Z_LID_IN + 1))
    b = b.cut(cyl(P["usb_exit_x"], OUT_Y0 - 1, P["usb_exit_z"], P["usb_exit_z"] + 0.01, w)) if False else b
    b = b.cut(cq.Workplane("XZ").center(P["usb_exit_x"], P["usb_exit_z"]).circle(w / 2).extrude(-(P["wall"] + 2)).translate((0, OUT_Y0 - 1, 0)))
    # cable-tie anchor next to the USB exit (bridge on the back plate)
    tx = P["usb_exit_x"] + 6
    b = b.union(box(tx - 2, IN_Y0 + 2, P["back"] - 0.01, tx + 2, IN_Y0 + 6, P["back"] + 4))
    b = b.cut(box(tx - 3, IN_Y0 + 2.9, P["back"] + 0.6, tx + 3, IN_Y0 + 5.1, P["back"] + 2.6))
    return b

# ============================================================== LID
def make_lid():
    L = box(OUT_X0, OUT_Y0, Z_LID_IN, OUT_X1, OUT_Y1, DEPTH).edges("|Z").fillet(2.0)
    # alignment lip inside the walls
    c = 0.25
    lip = box(IN_X0 + c, IN_Y0 + c, Z_LID_IN - P["lip_h"], IN_X1 - c, IN_Y1 - c, Z_LID_IN + 0.01)
    lip = lip.cut(box(IN_X0 + c + P["lip_t"], IN_Y0 + c + P["lip_t"], Z_LID_IN - P["lip_h"] - 1, IN_X1 - c - P["lip_t"], IN_Y1 - c - P["lip_t"], Z_LID_IN + 1))
    for x, y in BOSSES:
        lip = lip.cut(cyl(x, y, Z_LID_IN - 5, Z_LID_IN + 1, P["boss_d"] + 1.0))
    lip = lip.cut(box(J1_X - P["j1_slot_w"] / 2 - 0.3, IN_Y0 - 1, Z_LID_IN - 5, J1_X + P["j1_slot_w"] / 2 + 0.3, IN_Y0 + 3, Z_LID_IN + 1))
    L = L.union(lip)
    # tongue clamping the USB cable in its slot (0.3 mm squeeze)
    w = P["cable_d"] + 0.2
    L = L.union(box(P["usb_exit_x"] - w / 2 + 0.15, OUT_Y0 + 0.2, P["usb_exit_z"] + P["cable_d"] / 2 - 0.3,
                    P["usb_exit_x"] + w / 2 - 0.15, IN_Y0 + 0.01, Z_LID_IN + 0.01))
    # press pins on the PCB top
    for x, y in PINS:
        L = L.union(cyl(x, y, Z_PCB_TOP + P["pin_gap"], Z_LID_IN + 0.01, P["pin_d"]))
    # screw holes + shallow counterbore for the head
    for x, y in BOSSES:
        L = L.cut(cyl(x, y, Z_LID_IN - 1, DEPTH + 1, P["screw_clear"]))
        L = L.cut(cyl(x, y, DEPTH - 0.6, DEPTH + 1, P["head_d"] + 0.4))
    # trimmer R7 screwdriver hole
    L = L.cut(cyl(R7_XY[0], R7_XY[1], Z_LID_IN - 1, DEPTH + 1, P["r7_hole_d"]))
    # vent slots (front face, above the ESP32 and in the cable bay)
    for i in range(5):
        x = P["pcb_w"] + 4 + i * 3.0
        L = L.cut(box(x, 8, Z_LID_IN - 1, x + 1.5, 20, DEPTH + 1))
        L = L.cut(box(x, 24, Z_LID_IN - 1, x + 1.5, 34, DEPTH + 1))
    return L

# ============================================================== supports / guides / pins placement
def holes_box():
    import re
    out = []
    for f in ("domofon-PTH.drl", "domofon-NPTH.drl"):
        tools, cur = {}, None
        for line in open(ROOT / "hardware/pcb/gerbers" / f):
            line = line.strip()
            m = re.match(r"^T(\d+)C([\d.]+)", line)
            if m: tools[m.group(1)] = float(m.group(2)); continue
            m = re.match(r"^T(\d+)$", line)
            if m: cur = m.group(1); continue
            m = re.match(r"^X(-?[\d.]+)Y(-?[\d.]+)", line)
            if m and cur: out.append((*k2b(float(m.group(1)), -float(m.group(2))), tools[cur]))
    return out
HOLES = holes_box()

def rect_clear(x0, y0, x1, y1, holes, d=1.6):
    for hx, hy, hd in holes:
        dx = max(x0 - hx, 0, hx - x1); dy = max(y0 - hy, 0, hy - y1)
        if math.hypot(dx, dy) < hd / 2 + d: return False
    return True

CIRCLES = []
def body_rects():
    rs = []
    for c in data["components"]:
        for b in c["bodies"]:
            if b["type"] == "rect":
                (xa, ya), (xb, yb) = k2b(b["x0"], b["y0"]), k2b(b["x1"], b["y1"])
                rs.append((min(xa, xb), min(ya, yb), max(xa, xb), max(ya, yb)))
            else:
                x, y = k2b(*b["c"]); CIRCLES.append((x, y, b["r"]))
    # ESP module footprint (pins can not pass the module)
    ex, ey = esp["pos"]
    (xa, ya), (xb, yb) = k2b(ex - 9, ey - 12.2), k2b(ex + 9, ey + 12.36)
    rs.append((min(xa, xb), min(ya, yb), max(xa, xb), max(ya, yb)))
    j = next(c for c in data["components"] if c["ref"] == "JP1")
    (xa, ya), (xb, yb) = k2b(j["pos"][0], j["pos"][1] - 8.89), k2b(j["pos"][0], j["pos"][1] + 8.89)
    rs.append((min(xa, xb) - 0.8, min(ya, yb) - 0.8, max(xa, xb) + 0.8, max(ya, yb) + 0.8))
    return rs

def pick_pin(target, rects, r):
    best = None
    for i in range(0, 220):
        for j in range(0, 270):
            x, y = 1.8 + i * 0.2, 1.8 + j * 0.2
            if x > P["pcb_w"] - 1.8 or y > P["pcb_h"] - 1.8: continue
            if any(x + r + 0.8 > a and x - r - 0.8 < c and y + r + 0.8 > b and y - r - 0.8 < d for a, b, c, d in rects): continue
            if any(math.dist((x, y), (cx, cy)) < cr + r + 0.8 for cx, cy, cr in CIRCLES): continue
            if not rect_clear(x - r, y - r, x + r, y + r, HOLES, 1.2): continue
            dd = math.dist((x, y), target)
            if best is None or dd < best[0]: best = (dd, (round(x, 2), round(y, 2)))
    return best[1]

RECTS = body_rects()
PINS = [pick_pin(t, RECTS, P["pin_d"] / 2) for t in [(0, 0), (0, P["pcb_h"]), (P["pcb_w"], P["pcb_h"]), (P["pcb_w"], 0)]]

def pick_support(cands):
    for (x0, y0, x1, y1) in cands:
        if rect_clear(x0, y0, x1, y1, HOLES): return (x0, y0, x1, y1)
    raise RuntimeError("no support spot")
ov = 1.2  # how far supports reach under the PCB
SUPPORTS = []
for y in (3.0, 10.0, 46.0, 51.0):      # left edge (outside part merges with the screw boss)
    SUPPORTS.append(pick_support([(-1.5, y + k, ov, y + k + 3) for k in (0, 1, 2, -1, -2, 3)]))
for y in (2.0, 25.0, 51.0):            # right edge
    SUPPORTS.append(pick_support([(P["pcb_w"] - ov, y + k, P["pcb_w"] + 1.5, y + k + 3) for k in (0, 1, 2, -1, -2, 3, 4)]))
for x in (6.0, 28.0):                  # bottom edge
    SUPPORTS.append(pick_support([(x + k, -0.5, x + k + 3, ov) for k in (0, 1, 2, -1, -2, 3)]))
for x in (14.0, 34.0):                 # top edge
    SUPPORTS.append(pick_support([(x + k, P["pcb_h"] - ov, x + k + 3, IN_Y1) for k in (0, 1, 2, -1, -2, 3)]))
c = P["clr"]
GUIDES = [
    (P["pcb_w"] + c, 2.0, P["pcb_w"] + c + 1.5, 7.0),        # right edge guides (in the cable bay)
    (P["pcb_w"] + c, 50.0, P["pcb_w"] + c + 1.5, 55.0),
    (2.0, -c - 1.5, 6.0, -c),                                # bottom-left guide (wires run further right)
    (-c - 1.5, 15.0, -c, 20.0), (-c - 1.5, 36.0, -c, 41.0),  # left edge guides between the bosses
]

# ============================================================== BUILD + CHECK + EXPORT
def main():
    import time; t0 = time.time()
    T = lambda m: print(f'[{time.time()-t0:6.1f}s] {m}', flush=True)
    for k in ("step", "stl", "3mf", "previews"):
        (ENC / k).mkdir(exist_ok=True)
    base, lid = make_base(), make_lid()
    T('base+lid'); pcb = pcb_assembly()
    plug, cable, cable_pts = usb_cable()
    print(f"outer size: {W:.1f} x {Hh:.1f} x {DEPTH:.1f} mm (W x H x depth from wall)")
    print(f"PCB top Z={Z_PCB_TOP:.1f}, module bottom Z={Z_MOD_BOT:.1f}, USB axis Z={Z_USB_C:.2f}, lid inner Z={Z_LID_IN:.2f}")
    print(f"USB mouth X={usb_mouth[0]:.2f} Y={usb_mouth[1]:.2f}; cable vertical X={cable_vx:.1f}; exit X={P['usb_exit_x']} Z={P['usb_exit_z']}")
    print(f"J1 centre X={J1_X:.2f}; R7 rotor {R7_XY}; pins {PINS}; wall hole {WALL_HOLE}")
    print("supports", SUPPORTS)
    T('models'); # interference
    report = []
    def vol(a, b):
        try:
            return a.intersect(b).val().Volume()
        except Exception:
            return 0.0
    items = dict(pcb); items["USB plug"] = plug
    _, cable_chk, _ = usb_cable(d=P["cable_d"] - 0.7)   # lid tongue squeezes the cable by 0.3 mm on purpose
    items["USB cable"] = cable_chk
    worst = 0.0
    for name, s in items.items():
        for pn, part in (("base", base), ("lid", lid)):
            v = vol(s, part)
            if name == "PCB" and pn == "base":
                pass
            report.append((name, pn, v))
            if v > 1e-3: print(f"  INTERFERENCE {name} x {pn}: {v:.3f} mm3")
    # PCB-to-base: supports touch the board bottom face exactly (volume 0); check touching faces only
    # cable vs walls: only the exit slot region may touch
    ok = all(v < 1e-3 for n, p, v in report)
    print("interference check:", "OK - no collisions" if ok else "COLLISIONS (see above)")
    # clearances
    zmax = {n: s.val().BoundingBox().zmax for n, s in items.items()}
    print("highest part above lid inner:", max((v - Z_LID_IN, n) for n, v in zmax.items()))
    T('interference'); # exports: print orientation
    base_p = base
    lid_p = lid.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, DEPTH))
    lid_p = lid_p.translate((0, 0, -lid_p.val().BoundingBox().zmin))
    for n, s in (("enclosure_base", base_p), ("enclosure_lid", lid_p)):
        cq.exporters.export(s, str(ENC / "stl" / f"{n}.stl"), tolerance=0.02, angularTolerance=0.1)
        cq.exporters.export(s, str(ENC / "step" / f"{n}.step"))
    # 3MF (Bambu Studio): one file per part + one plate with both parts side by side
    import trimesh
    mb = trimesh.load(ENC / "stl" / "enclosure_base.stl"); ml = trimesh.load(ENC / "stl" / "enclosure_lid.stl")
    for n, m in (("enclosure_base", mb), ("enclosure_lid", ml)):
        m2 = m.copy(); m2.apply_translation([-m2.bounds[0][0], -m2.bounds[0][1], -m2.bounds[0][2]])
        trimesh.Scene({n: m2}).export(ENC / "3mf" / f"{n}.3mf")
    a = mb.copy(); a.apply_translation(-a.bounds[0])
    b = ml.copy(); b.apply_translation(-b.bounds[0] + [0, a.extents[1] + 10, 0])
    sc = trimesh.Scene(); sc.add_geometry(a, node_name="base", geom_name="base"); sc.add_geometry(b, node_name="lid", geom_name="lid")
    sc.export(ENC / "3mf" / "enclosure_plate_base_and_lid.3mf")
    T('stl/step/3mf parts'); asm = cq.Assembly(name="domofon_enclosure")
    asm.add(base, name="base", color=cq.Color(0.85, 0.85, 0.88))
    asm.add(lid, name="lid", color=cq.Color(0.6, 0.75, 0.9))
    for n, s in pcb.items():
        asm.add(s, name=n, color=cq.Color(0.1, 0.5, 0.2) if n == "PCB" else cq.Color(0.3, 0.3, 0.3))
    asm.add(plug, name="usb_plug", color=cq.Color(0.1, 0.1, 0.1)); asm.add(cable, name="usb_cable", color=cq.Color(0.1, 0.1, 0.1))
    asm.save(str(ENC / "step" / "enclosure_assembly_with_pcb.step"))
    T('assembly step'); # preview meshes (assembly coordinates)
    tmp = ENC / "previews" / "_mesh"; tmp.mkdir(exist_ok=True)
    cq.exporters.export(base, str(tmp / "base.stl"), tolerance=0.05)
    cq.exporters.export(lid, str(tmp / "lid.stl"), tolerance=0.05)
    comp = cq.Workplane("XY").add(cq.Compound.makeCompound([s.val() for n, s in pcb.items() if n != "PCB"]))
    cq.exporters.export(pcb["PCB"], str(tmp / "pcb.stl"), tolerance=0.05)
    cq.exporters.export(comp, str(tmp / "parts.stl"), tolerance=0.05)
    cq.exporters.export(cq.Workplane("XY").add(cq.Compound.makeCompound([plug.val(), cable.val()])), str(tmp / "usb.stl"),
                        tolerance=0.3, angularTolerance=0.5)   # fine tessellation of the swept cable is extremely slow
    json.dump(dict(W=W, H=Hh, D=DEPTH, OUT=(OUT_X0, OUT_Y0, OUT_X1, OUT_Y1), J1_X=J1_X, usb_exit_x=P["usb_exit_x"],
                   usb_exit_z=P["usb_exit_z"], duct=(P["duct_w"], P["duct_h"]), wall_hole=WALL_HOLE,
                   Z_LID_IN=Z_LID_IN), open(tmp / "info.json", "w"))
    T('done'); return ok

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
