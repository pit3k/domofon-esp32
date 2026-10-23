#!/usr/bin/env python3
"""Parametric 3D-printed wall enclosure for the domofon-esp32 PCB (CadQuery), layout v9.

Run:  python enclosure.py            (needs: pip install cadquery trimesh pyvista)
Out:  ../step/*.step, ../stl/*.stl, ../3mf/*.3mf, preview meshes, interference report on stdout

BOX COORDINATES = view from the room LOOKING TOWARD THE WALL:
  X right, Y up, Z out of the wall towards the viewer (Z=0 = back face glued to the wall).
  Origin = outer lower-left corner of the box (93 x 68 x 26 mm).
  The PCB is FLIPPED and shifted +25 mm right: components face the wall, the solder side faces the lid.
  Seen from the front this mirrors the KiCad layout left-right (no rotation):
    X = PCB_X0 + 55.5 - x_kicad ,  Y = PCB_Y0 + 45.9 - y_kicad
  -> J1 (RJ11) opens into the 25.3 mm left chamber; the plugged-in RJ11 modular plug sits inside the box,
     and its flat telephone cable exits through a 5.0 x 2.5 mm channel at the bottom of the left wall
     (Y = 11.75..16.75 mm, Z = 2.0..4.5 mm), sealed and pinched by a reinforced 5.0 mm thick plunger on the lid.
"""
import json, math, re, sys
from pathlib import Path
import cadquery as cq

HERE = Path(__file__).resolve().parent
ENC = HERE.parent
ROOT = ENC.parents[1]

# ============================================================== PARAMETERS
P = dict(
    width=93.0, height=68.0, depth=26.0,   # outer W x H x D (W = 68 + 25 = 93 mm)
    pcb_dx=25.0,             # PCB + USB-C shifted +25.0 mm right compared to v7
    wall=2.0,                # left / right / bottom walls
    back=2.0,                # back plate (glued to the wall)
    lid_t=3.0,               # lid plate (countersunk screw heads)
    clr=0.3,                 # PCB edge <-> wall / guide clearance
    pcb_w=55.5, pcb_h=45.9, pcb_t=1.5,
    air=1.4,                 # back plate -> top of the USB-C receptacle (axis exactly 5.0 mm from the wall)
    # ESP32-C3 SuperMini stack on female headers (measured from the PCB component face towards the wall)
    fheader_h=8.5, mheader_spacer=2.5, module_pcb=1.0, module_parts=1.5, usbc_h=3.2,
    # USB-C plug pocket in the top wall (overmold sits in it) and obround opening for the metal shell
    usb_open_w=9.25, usb_open_t=3.4,          # plug shell 8.25 x 2.40 + 0.5 per side
    pocket_w=13.0, pocket_t=8.0, pocket_r=2.0,
    plug_tip=6.6,            # metal shell length in front of the overmold (typ. 6.5-6.7 mm)
    insert_need=6.2,         # insertion for a fully mated plug (receptacle shell 6.20 mm)
    cup_floor=1.0, cup_wall=1.2,
    # wall cable hole (shifted +3 mm up from v8's 12.5 mm -> Y = 15.5 mm, X = 16.0 mm), 4 corner posts, screws
    wall_hole=(16.0, 15.5), wall_hole_d=12.0,
    posts=((6.0, 6.0), (87.0, 6.0), (87.0, 62.0), (6.0, 62.0)),
    post_d=7.5, insert_hole_d=4.0, insert_hole_depth=10.0,
    screw_clear=3.4, csk_d=6.8,              # M3 countersunk (ISO 10642 / DIN 7991), 90 deg
    # Left-wall flat telephone cable channel (5.0 x 2.5 mm, 2 mm above bottom-left post, right against back floor)
    # + reinforced 5.0 mm thick lid plunger with wide 45-deg gusseted root & side guide channel
    slot_y0=11.75, slot_y1=16.75,            # 5.0 mm wide in Y (center Y = 14.25 mm; 2.0 mm above post top Y = 9.75 mm)
    slot_z0=2.0, slot_z1=4.5,                # 2.5 mm window in Z right on the 2.0 mm back plate floor
    guide_x1=5.5, guide_wall_w=2.0,          # side guide walls X = 0..5.5 mm, Y = 9.75..11.75 and 16.75..18.75 mm
    plunger_x=5.0, plunger_y_clr=0.15,       # plunger shaft 5.0 mm thick in X, 4.70 mm wide in Y (11.90..16.60 mm)
    root_x=7.5, root_y0=10.00, root_y1=18.50, root_z0=19.50,  # wide reinforced root (7.5 x 8.5 mm) tapering to Z = 19.50 mm
    # PCB fixing
    support_d=3.0, pin_d=3.0, pin_gap=0.1, lip_h=2.0, lip_t=1.2, lip_clr=0.25,
)
# component heights (from the PCB component face towards the wall), simplified bodies
H = {"R0207_P7.62": 3.0, "R0207_P10.16": 3.0, "CFILM_P7.62": 11.0, "R0414_P15.24": 5.0, "DO34_P5.08": 2.2, "DO15_P5.08_V": 11.5,
     "CFILM_P5.08": 10.0, "CP_D5_P2.0": 12.0, "CA9V": 6.5, "DIP4": 4.5, "T1": 11.0, "MTJ642": 14.5,
     "XY308_2P": 10.0, "WIRE_P10.16": 2.5}
data = json.loads((HERE / "board_components.json").read_text())
OVR = {"C8": dict(h=11.0, body=dict(type="rect", x0=38.0, y0=17.85, x1=48.0, y1=21.05)),   # 0.47 uF/250 V MKT
       "C5": dict(h=13.0, body=dict(type="rect", x0=46.6, y0=33.9, x1=53.8, y1=41.1))}     # WIMA MKS2 1 uF/100 V
for _c in data["components"]:
    if _c["ref"] in OVR:
        _c["bodies"] = [OVR[_c["ref"]]["body"]]; _c["h"] = OVR[_c["ref"]]["h"]
esp = next(c for c in data["components"] if c["ref"] == "ESP")
j1 = next(c for c in data["components"] if c["ref"] == "J1")

# ----------------------------------------------------------------- derived geometry
OW, OH, D, w = P["width"], P["height"], P["depth"], P["wall"]
Z_LID_IN = D - P["lid_t"]
ESP_STACK = P["fheader_h"] + P["mheader_spacer"] + P["module_pcb"] + P["usbc_h"]      # 15.2
Z_USB_TOP = P["back"] + P["air"]                     # receptacle face nearest to the wall
Z_USB_C = Z_USB_TOP + P["usbc_h"] / 2                # USB axis = 5.0 mm from the wall
Z_F = Z_USB_TOP + ESP_STACK                          # PCB component face (18.60 mm)
Z_S = Z_F + P["pcb_t"]                               # PCB solder face (20.10 mm)
PCB_X0 = w + P["clr"] + P["pcb_dx"]                  # 27.30 mm
# vertical position: the board top edge sits 'clr' under the inner face of the top wall
TOP_WALL = 1.39
Y_TOP_IN = OH - TOP_WALL
PCB_Y1 = Y_TOP_IN - P["clr"]                         # 66.31 mm
PCB_Y0 = PCB_Y1 - P["pcb_h"]                         # 20.41 mm
def k2b(x, y): return (PCB_X0 + P["pcb_w"] - x, PCB_Y0 + P["pcb_h"] - y)
USB_X, Y_MOUTH = k2b(*esp["usb_mouth"])
RECESS = OH - Y_MOUTH
# overmold pocket depth so that the plug reaches insert_need into the receptacle
POCKET_DEPTH = round(RECESS - (P["plug_tip"] - P["insert_need"]), 2)
Y_POCKET = OH - POCKET_DEPTH                         # pocket floor (overmold stop)
J1_Y = k2b(*j1["pos"])[1]
J1_Z0 = Z_F - H["MTJ642"]

def box(x0, y0, z0, x1, y1, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))
def cyl(x, y, z0, z1, d):
    return cq.Workplane("XY").circle(d / 2).extrude(z1 - z0).translate((x, y, z0))
def ybox_round(xc, zc, wx, tz, y0, y1, r):
    """rounded rectangle in the XZ plane, extruded along Y from y0 to y1"""
    r = min(r, tz / 2 - 1e-3, wx / 2 - 1e-3)
    s = cq.Workplane("XZ").center(xc, zc).rect(wx, tz).extrude(-(y1 - y0)).translate((0, y0, 0))
    return s.edges("|Y").fillet(r)
def loft_rect(x0a, y0a, x1a, y1a, za, x0b, y0b, x1b, y1b, zb):
    """ruled loft between two axis-aligned XY rectangles at Z=za and Z=zb"""
    wa = cq.Workplane("XY").workplane(offset=za).moveTo(x0a, y0a).lineTo(x1a, y0a).lineTo(x1a, y1a).lineTo(x0a, y1a).close().wire().val()
    wb = cq.Workplane("XY").workplane(offset=zb).moveTo(x0b, y0b).lineTo(x1b, y0b).lineTo(x1b, y1b).lineTo(x0b, y1b).close().wire().val()
    return cq.Workplane("XY").add(cq.Solid.makeLoft([wa, wb], True))

# ============================================================== PCB ASSEMBLY (interference model)
def pcb_assembly():
    parts = {"PCB": box(PCB_X0, PCB_Y0, Z_F, PCB_X0 + P["pcb_w"], PCB_Y1, Z_S)}
    for c in data["components"]:
        if c["fp"] == "ESP": continue
        h = c.get("h", H.get(c["fp"], 5.0)); sol = []
        for b in c["bodies"]:
            if b["type"] == "rect":
                (xa, ya), (xb, yb) = k2b(b["x0"], b["y0"]), k2b(b["x1"], b["y1"])
                sol.append(box(min(xa, xb), min(ya, yb), Z_F - h, max(xa, xb), max(ya, yb), Z_F))
            else:
                x, y = k2b(*b["c"]); sol.append(cyl(x, y, Z_F - h, Z_F, 2 * b["r"]))
        if sol:
            s = sol[0]
            for o in sol[1:]: s = s.union(o)
            parts[c["ref"]] = s
    ex, ey = esp["pos"]
    def lb(x0, y0, x1, y1, z0, z1):
        (xa, ya), (xb, yb) = k2b(ex + x0, ey + y0), k2b(ex + x1, ey + y1)
        return box(min(xa, xb), min(ya, yb), z0, max(xa, xb), max(ya, yb), z1)
    zm = Z_F - P["fheader_h"] - P["mheader_spacer"]          # module PCB (side facing the board)
    e = lb(-8.89, -10.16, -6.35, 10.16, zm, Z_F).union(lb(6.35, -10.16, 8.89, 10.16, zm, Z_F))
    e = e.union(lb(-9.0, -10.16, 9.0, 12.36, zm - P["module_pcb"], zm))
    e = e.union(lb(-8.0, -9.0, 8.0, 11.5, zm - P["module_pcb"] - P["module_parts"], zm - P["module_pcb"]))
    # USB-C receptacle: obround shell 8.94 x 3.2 mm (rounded ends), mouth at usb_mouth
    e = e.union(ybox_round(USB_X, Z_USB_C, 8.94, P["usbc_h"], k2b(ex, ey - 4.9)[1], Y_MOUTH, 1.55))
    parts["ESP"] = e
    return parts

def usb_plug():
    """plug inserted from above: metal shell 8.25 x 2.4 + overmold 12 x 6.5 sitting on the pocket floor"""
    shell = ybox_round(USB_X, Z_USB_C, 8.25, 2.4, Y_POCKET - P["plug_tip"], Y_POCKET, 1.2)
    over = ybox_round(USB_X, Z_USB_C, 12.0, 6.5, Y_POCKET, Y_POCKET + 20, 2.0)
    return shell, over

def rj11_plug_and_cable():
    """Plugged-in 6P4C RJ11 modular plug inside J1 (in the left chamber) + flat telephone cable
    routing down the left chamber and exiting through the 5.0 x 2.5 mm floor slot (Y=11.75..16.75, Z=2.0..4.5)."""
    plug_body = box(23.0, J1_Y - 4.825, 7.5, 30.6, J1_Y + 4.825, 14.1)
    boot = box(19.5, J1_Y - 3.2, 8.2, 23.0, J1_Y + 3.2, 13.4)
    # Flat cable (4.5 mm wide x 2.1 mm thick, Z = 2.15..4.25 mm on the back floor)
    slot_yc = (P["slot_y0"] + P["slot_y1"]) / 2.0   # 14.25 mm
    cw_h = 2.25
    # Horizontal exit run through the 5.0 x 2.5 mm slot (X = -8.0 .. 9.6 mm)
    c_exit = box(-8.0, slot_yc - cw_h, 2.15, 9.6, slot_yc + cw_h, 4.25)
    # Vertical run in the left chamber (X = 5.8 .. 9.8 mm, Y = 12.0 .. 46.0 mm, clear of wall hole X=10..22)
    c_vert = box(5.8, slot_yc - cw_h, 2.15, 9.8, 46.0, 4.25)
    # Diagonal run from (X=5.8..9.8, Y=46.0) to (X=11.5..15.5, Y=J1_Y), passing well to the right of top-left post (6, 62)
    w_a = cq.Workplane("YZ").workplane(offset=5.8).moveTo(46.0 - cw_h, 2.15).lineTo(46.0 + cw_h, 2.15).lineTo(46.0 + cw_h, 4.25).lineTo(46.0 - cw_h, 4.25).close().wire().val()
    w_b = cq.Workplane("YZ").workplane(offset=12.5).moveTo(J1_Y - cw_h, 2.15).lineTo(J1_Y + cw_h, 2.15).lineTo(J1_Y + cw_h, 4.25).lineTo(J1_Y - cw_h, 4.25).close().wire().val()
    c_diag = cq.Workplane("XY").add(cq.Solid.makeLoft([w_a, w_b], True))
    # Upper horizontal segment into the RJ11 boot (X = 12.0 .. 15.5 mm at Y = J1_Y, rising smoothly to boot Z)
    c_top = box(12.0, J1_Y - cw_h, 2.15, 15.5, J1_Y + cw_h, 4.25)
    c_rise = loft_rect(14.5, J1_Y - cw_h, 16.5, J1_Y + cw_h, 2.15,
                       18.5, J1_Y - cw_h, 20.0, J1_Y + cw_h, 9.5)
    return plug_body.union(boot).union(c_exit).union(c_vert).union(c_diag).union(c_top).union(c_rise)

# ============================================================== placement of PCB supports / lid pins
def holes_box():
    out = []
    for f in ("domofon-PTH.drl", "domofon-NPTH.drl"):
        tools, cur = {}, None
        p = ROOT / "hardware/pcb/gerbers" / f
        if not p.exists(): continue
        for line in open(p):
            line = line.strip()
            m = re.match(r"^T(\d+)C([\d.]+)", line)
            if m: tools[m.group(1)] = float(m.group(2)); continue
            m = re.match(r"^T(\d+)$", line)
            if m: cur = m.group(1); continue
            m = re.match(r"^X(-?[\d.]+)Y(-?[\d.]+)", line)
            if m and cur: out.append((*k2b(float(m.group(1)), -float(m.group(2))), tools[cur]))
    return out
HOLES = holes_box()

def body_rects():
    rs = []
    for c in data["components"]:
        for b in c["bodies"]:
            if b["type"] == "rect":
                (xa, ya), (xb, yb) = k2b(b["x0"], b["y0"]), k2b(b["x1"], b["y1"])
                rs.append((min(xa, xb), min(ya, yb), max(xa, xb), max(ya, yb)))
            else:
                x, y = k2b(*b["c"]); rs.append((x - b["r"], y - b["r"], x + b["r"], y + b["r"]))
    ex, ey = esp["pos"]
    (xa, ya), (xb, yb) = k2b(ex - 9.5, ey - 12.5), k2b(ex + 9.5, ey + 12.6)
    rs.append((min(xa, xb), min(ya, yb), max(xa, xb), max(ya, yb)))
    j = next(c for c in data["components"] if c["ref"] == "JP1")
    (xa, ya), (xb, yb) = k2b(j["pos"][0], j["pos"][1] - 8.89), k2b(j["pos"][0], j["pos"][1] + 8.89)
    rs.append((min(xa, xb) - 0.8, min(ya, yb) - 0.8, max(xa, xb) + 0.8, max(ya, yb) + 0.8))
    return rs
RECTS = body_rects()

def free(x, y, r):
    if any(x + r + 0.8 > a and x - r - 0.8 < c and y + r + 0.8 > b and y - r - 0.8 < d for a, b, c, d in RECTS): return False
    if any(math.dist((x, y), (hx, hy)) < hd / 2 + r + 1.2 for hx, hy, hd in HOLES): return False
    return True

def pick(target, r):
    best = None
    for i in range(0, 280):
        for j in range(0, 230):
            x, y = PCB_X0 + 1.8 + i * 0.2, PCB_Y0 + 1.8 + j * 0.2
            if x > PCB_X0 + P["pcb_w"] - 1.8 or y > PCB_Y1 - 1.8 or not free(x, y, r): continue
            dd = math.dist((x, y), target)
            if best is None or dd < best[0]: best = (dd, (round(x, 2), round(y, 2)))
    return best[1]
X1_, Y1_ = PCB_X0 + P["pcb_w"], PCB_Y1
SPOTS = []   # free spots (no component body, >= 1.2 mm from any drilled hole); the right half of the board is full
for t in [(PCB_X0, PCB_Y0), (PCB_X0, Y1_), (X1_, Y1_), ((PCB_X0 + X1_) / 2, (PCB_Y0 + Y1_) / 2)]:
    p = pick(t, P["support_d"] / 2)
    if all(math.dist(p, q) > 5 for q in SPOTS): SPOTS.append(p)
c_ = P["clr"]
GUIDES = [  # (x0, y0, x1, y1) ribs from the back plate up to 1.5 mm above the PCB solder face, outside the board outline
    # Right edge guides
    (X1_ + c_, PCB_Y0 + 4.0, X1_ + c_ + 1.5, PCB_Y0 + 10.0),
    (X1_ + c_, PCB_Y0 + 26.0, X1_ + c_ + 1.5, PCB_Y0 + 32.0),
    # Left edge guides (inside the chamber at X = 25.5..27.0, avoiding X1 wires at Y=40..45 and RJ11 at Y=52..64)
    (PCB_X0 - c_ - 1.5, PCB_Y0 + 3.0, PCB_X0 - c_, PCB_Y0 + 9.0),
    (PCB_X0 - c_ - 1.5, PCB_Y0 + 25.5, PCB_X0 - c_, PCB_Y0 + 30.5),
    # Bottom edge guides (shifted +25 mm right with the PCB)
    (8.0 + P["pcb_dx"], PCB_Y0 - c_ - 1.5, 14.0 + P["pcb_dx"], PCB_Y0 - c_),
    (50.0 + P["pcb_dx"], PCB_Y0 - c_ - 1.5, 56.0 + P["pcb_dx"], PCB_Y0 - c_),
]

# ============================================================== BASE
def make_base():
    b = box(0, 0, 0, OW, OH, Z_LID_IN).edges("|Z").fillet(2.0)
    b = b.cut(box(w, w, P["back"], OW - w, Y_TOP_IN, Z_LID_IN + 1))
    # 4 corner posts + corner gussets (posts merge into the walls)
    for x, y in P["posts"]:
        gx = (w - 0.01, x) if x < OW / 2 else (x, OW - w + 0.01)
        gy = (w - 0.01, y) if y < OH / 2 else (y, Y_TOP_IN + 0.01)
        b = b.union(box(gx[0], gy[0], P["back"] - 0.01, gx[1], gy[1], Z_LID_IN))
        b = b.union(cyl(x, y, P["back"] - 0.01, Z_LID_IN, P["post_d"]))
        b = b.cut(cyl(x, y, Z_LID_IN - P["insert_hole_depth"], Z_LID_IN + 1, P["insert_hole_d"]))
    # PCB supports (back plate -> PCB component face) and edge guides
    for x, y in SPOTS:
        b = b.union(cyl(x, y, P["back"] - 0.01, Z_F, P["support_d"]))
    for (x0, y0, x1, y1) in GUIDES:
        b = b.union(box(x0, y0, P["back"] - 0.01, x1, y1, Z_S + 1.5))
        # 1 mm ledge under the board edge (the board rests on it with its component face)
        if x0 > X1_:
            b = b.union(box(X1_ - 1.0, y0, P["back"] - 0.01, x0 + 0.01, y1, Z_F))
        elif x1 < PCB_X0:
            b = b.union(box(x1 - 0.01, y0, P["back"] - 0.01, PCB_X0 + 1.0, y1, Z_F))
        else:
            b = b.union(box(x0, y1 - 0.01, P["back"] - 0.01, x1, PCB_Y0 + 1.0, Z_F))
    # USB-C: cup under the pocket (floor carries the obround opening), pocket for the overmold, opening
    pw, pt, cw = P["pocket_w"], P["pocket_t"], P["cup_wall"]
    if Y_POCKET < Y_TOP_IN:   # pocket floor is below the inner face of the top wall -> cup hangs into the box
        cup = ybox_round(USB_X, Z_USB_C, pw + 2 * cw, pt + 2 * cw, Y_POCKET - P["cup_floor"], Y_TOP_IN + 0.01, P["pocket_r"] + cw)
        cup = cup.cut(box(0, 0, -5, OW, OH, P["back"] - 0.01))       # do not stick out of the back face
        b = b.union(cup)
    b = b.cut(ybox_round(USB_X, Z_USB_C, pw, pt, Y_POCKET, OH + 1, P["pocket_r"]))
    b = b.cut(ybox_round(USB_X, Z_USB_C, P["usb_open_w"], P["usb_open_t"], Y_POCKET - P["cup_floor"] - 2, Y_POCKET + 0.01, P["usb_open_t"] / 2))
    # Wall cable hole (Ø12 mm at X=16.0, Y=15.5)
    b = b.cut(cyl(*P["wall_hole"], -1, P["back"] + 1, P["wall_hole_d"]))
    # Left-wall guide block (X = 2.0..5.5 mm, Y = 9.75..18.75 mm, Z = 2.0..19.35 mm) + U-slot cut + 45-deg flared V-seat
    sy0, sy1, gw = P["slot_y0"], P["slot_y1"], P["guide_wall_w"]
    z_seat = P["root_z0"] - 0.15   # 19.35 mm (0.15 mm below plunger gusset bottom)
    b = b.union(box(w - 0.01, sy0 - gw, P["back"] - 0.01, P["guide_x1"], sy1 + gw, z_seat))
    # Cut the 5.0 mm wide U-slot from Z = back (2.0 mm) all the way up through Z_LID_IN
    b = b.cut(box(-1.0, sy0, P["back"], P["guide_x1"] + 0.5, sy1, Z_LID_IN + 1.0))
    # Cut 45-deg flared upper V-seat (Z = 19.35 .. 23.00 mm) in the outer left wall to receive the plunger's wide root
    v_seat = loft_rect(-1.0, sy0, P["root_x"] + 0.25, sy1, z_seat,
                       -1.0, P["root_y0"] - 0.15, P["root_x"] + 0.25, P["root_y1"] + 0.15, Z_LID_IN + 0.01)
    b = b.cut(v_seat).cut(box(-1.0, P["root_y0"] - 0.15, Z_LID_IN, P["root_x"] + 0.25, P["root_y1"] + 0.15, Z_LID_IN + 1.0))
    return b

# ============================================================== LID
def make_lid():
    L = box(0, 0, Z_LID_IN, OW, OH, D).edges("|Z").fillet(2.0)
    lc, lt = P["lip_clr"], P["lip_t"]
    x0, y0, x1, y1 = w + lc, w + lc, OW - w - lc, Y_TOP_IN - lc
    lip = box(x0, y0, Z_LID_IN - P["lip_h"], x1, y1, Z_LID_IN + 0.01)
    lip = lip.cut(box(x0 + lt, y0 + lt, Z_LID_IN - 5, x1 - lt, y1 - lt, Z_LID_IN + 1))
    for x, y in P["posts"]:
        lip = lip.cut(cyl(x, y, Z_LID_IN - 5, Z_LID_IN + 1, P["post_d"] + 1.0))
        gx = (0, x + 4.5) if x < OW / 2 else (x - 4.5, OW)
        gy = (0, y + 4.5) if y < OH / 2 else (y - 4.5, OH)
        lip = lip.cut(box(gx[0], gy[0], Z_LID_IN - 5, gx[1], gy[1], Z_LID_IN + 1))
    for (gx0, gy0, gx1, gy1) in GUIDES:
        lip = lip.cut(box(gx0 - 0.5, gy0 - 0.5, Z_LID_IN - 5, gx1 + 0.5, gy1 + 0.5, Z_LID_IN + 1))
    # Interrupt lip around the left-wall plunger / guide channel
    lip = lip.cut(box(0, P["slot_y0"] - P["guide_wall_w"] - 0.5, Z_LID_IN - 5, P["root_x"] + 1.0, P["slot_y1"] + P["guide_wall_w"] + 0.5, Z_LID_IN + 1))
    L = L.union(lip)
    # Reinforced thick plunger (X = 0..5.0 mm, Y = 11.90..16.60 mm, Z = 4.50..23.00 mm)
    # + wide 45-deg gusseted root base (X = 0..7.5 mm, Y = 10.00..18.50 mm at Z = 23.00 mm -> tapering to Z = 19.50 mm)
    py0 = P["slot_y0"] + P["plunger_y_clr"]   # 11.90 mm
    py1 = P["slot_y1"] - P["plunger_y_clr"]   # 16.60 mm
    px1 = P["plunger_x"]                      # 5.00 mm
    shaft = box(0.0, py0, P["slot_z1"], px1, py1, Z_LID_IN + 0.1)
    gusset = loft_rect(0.0, py0, px1, py1, P["root_z0"],
                       0.0, P["root_y0"], P["root_x"], P["root_y1"], Z_LID_IN)
    gusset_pad = box(0.0, P["root_y0"], Z_LID_IN - 0.01, P["root_x"], P["root_y1"], Z_LID_IN + 0.2)
    L = L.union(shaft).union(gusset).union(gusset_pad)
    for x, y in SPOTS:   # press pins on the PCB solder face, coaxial with the supports
        L = L.union(cyl(x, y, Z_S + P["pin_gap"], Z_LID_IN + 0.01, P["pin_d"]))
    for x, y in P["posts"]:
        L = L.cut(cyl(x, y, Z_LID_IN - 6, D + 1, P["screw_clear"]))
        h = (P["csk_d"] - P["screw_clear"]) / 2     # 90 deg cone
        cone = cq.Workplane("XY").add(cq.Solid.makeCone(P["screw_clear"] / 2, P["csk_d"] / 2 + 0.5, h + 0.5,
                                                        pnt=cq.Vector(x, y, D - h), dir=cq.Vector(0, 0, 1)))
        L = L.cut(cone)
    return L

# ============================================================== BUILD + CHECK + EXPORT
def main():
    for k in ("step", "stl", "3mf", "previews"):
        (ENC / k).mkdir(exist_ok=True)
    base, lid = make_base(), make_lid()
    pcb = pcb_assembly(); shell, over = usb_plug(); rj11 = rj11_plug_and_cable()
    print(f"outer size: {OW:.0f} x {OH:.0f} x {D:.0f} mm; top wall {TOP_WALL} mm; lid {P['lid_t']} mm")
    print(f"PCB X {PCB_X0:.2f}..{PCB_X0+P['pcb_w']:.2f}, Y {PCB_Y0:.2f}..{PCB_Y1:.2f}, component face Z={Z_F:.2f}, solder face Z={Z_S:.2f}")
    print(f"USB-C axis X={USB_X:.2f} Z={Z_USB_C:.2f} (from wall); mouth Y={Y_MOUTH:.2f} -> {RECESS:.2f} mm below the top surface")
    print(f"pocket {P['pocket_w']}x{P['pocket_t']} R{P['pocket_r']}, depth {POCKET_DEPTH:.2f} mm (floor Y={Y_POCKET:.2f}); "
          f"plug insertion = {P['plug_tip'] - (Y_POCKET - Y_MOUTH):.2f} mm (tip {P['plug_tip']} mm)")
    print(f"J1 centre Y={J1_Y:.2f} (plug inside left chamber); left cable slot Y={P['slot_y0']}..{P['slot_y1']}, Z={P['slot_z0']}..{P['slot_z1']}; "
          f"plunger X=0..{P['plunger_x']} (root X=0..{P['root_x']}, Y={P['root_y0']}..{P['root_y1']}); supports/pins at {SPOTS}")
    ok = True
    def vol(a, b):
        try: return a.intersect(b).val().Volume()
        except Exception: return 0.0
    items = dict(pcb); items["USB shell"] = shell; items["USB overmold"] = over; items["RJ11 plug+cable"] = rj11
    for name, s in items.items():
        for pn, part in (("base", base), ("lid", lid)):
            v = vol(s, part)
            if v > 1e-3: ok = False; print(f"  INTERFERENCE {name} x {pn}: {v:.3f} mm3")
    v = vol(base, lid)
    if v > 1e-3: ok = False; print(f"  INTERFERENCE base x lid: {v:.3f} mm3")
    else: print(f"  base x lid intersect volume: {v:.6f} mm3")
    zmin = min(s.val().BoundingBox().zmin for n, s in pcb.items())
    print(f"lowest component Z={zmin:.2f} (back plate inner face Z={P['back']}); highest solder side Z={Z_S:.2f} < lid lip {Z_LID_IN-P['lip_h']:.1f}")
    for x, y in P["posts"]:
        dmin = math.dist((x, y), P["wall_hole"]) - P["wall_hole_d"] / 2 - P["post_d"] / 2
        print(f"  post {x,y}: clearance to wall hole {dmin:.2f} mm")
    print(f"  wall hole X={P['wall_hole'][0]-P['wall_hole_d']/2:.1f}..{P['wall_hole'][0]+P['wall_hole_d']/2:.1f} vs PCB left edge X={PCB_X0:.2f} "
          f"(clearance {PCB_X0 - (P['wall_hole'][0]+P['wall_hole_d']/2):.2f} mm)")
    print("interference check:", "OK - no collisions" if ok else "COLLISIONS (see above)")
    # print orientation: base on its back, lid outer face down
    lid_p = lid.rotate((0, 0, 0), (1, 0, 0), 180)
    lid_p = lid_p.translate((0, 0, -lid_p.val().BoundingBox().zmin))
    for n, s in (("enclosure_base", base), ("enclosure_lid", lid_p)):
        cq.exporters.export(s, str(ENC / "stl" / f"{n}.stl"), tolerance=0.02, angularTolerance=0.1)
        cq.exporters.export(s, str(ENC / "step" / f"{n}.step"))
    import trimesh
    mb = trimesh.load(ENC / "stl" / "enclosure_base.stl"); ml = trimesh.load(ENC / "stl" / "enclosure_lid.stl")
    print("watertight:", mb.is_watertight, ml.is_watertight)
    for n, m in (("enclosure_base", mb), ("enclosure_lid", ml)):
        m2 = m.copy(); m2.apply_translation(-m2.bounds[0]); trimesh.Scene({n: m2}).export(ENC / "3mf" / f"{n}.3mf")
    a = mb.copy(); a.apply_translation(-a.bounds[0]); bb = ml.copy(); bb.apply_translation(-bb.bounds[0] + [a.extents[0] + 10, 0, 0])
    sc = trimesh.Scene(); sc.add_geometry(a, node_name="base", geom_name="base"); sc.add_geometry(bb, node_name="lid", geom_name="lid")
    sc.export(ENC / "3mf" / "enclosure_plate_base_and_lid.3mf")
    asm = cq.Assembly(name="domofon_enclosure")
    asm.add(base, name="base", color=cq.Color(0.85, 0.85, 0.88)); asm.add(lid, name="lid", color=cq.Color(0.6, 0.75, 0.9))
    for n, s in pcb.items():
        asm.add(s, name=n, color=cq.Color(0.1, 0.5, 0.2) if n == "PCB" else cq.Color(0.3, 0.3, 0.3))
    asm.add(shell, name="usb_shell", color=cq.Color(0.7, 0.7, 0.7)); asm.add(over, name="usb_overmold", color=cq.Color(0.1, 0.1, 0.1))
    asm.add(rj11, name="rj11_plug_cable", color=cq.Color(0.2, 0.5, 0.85))
    asm.save(str(ENC / "step" / "enclosure_assembly_with_pcb.step"))
    tmp = ENC / "previews" / "_mesh"; tmp.mkdir(exist_ok=True)
    cq.exporters.export(base, str(tmp / "base.stl"), tolerance=0.05)
    cq.exporters.export(lid, str(tmp / "lid.stl"), tolerance=0.05)
    cq.exporters.export(pcb["PCB"], str(tmp / "pcb.stl"), tolerance=0.05)
    cq.exporters.export(cq.Workplane("XY").add(cq.Compound.makeCompound([s.val() for n, s in pcb.items() if n != "PCB"])), str(tmp / "parts.stl"), tolerance=0.05)
    cq.exporters.export(cq.Workplane("XY").add(cq.Compound.makeCompound([shell.val(), over.val()])), str(tmp / "usb.stl"), tolerance=0.05)
    cq.exporters.export(rj11, str(tmp / "rj11.stl"), tolerance=0.05)
    json.dump(dict(W=OW, H=OH, S=OH, D=D, wall_hole=P["wall_hole"], usb_x=USB_X), open(tmp / "info.json", "w"))
    return ok

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
