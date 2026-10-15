#!/usr/bin/env python3
"""Verify cnc/gcode/*.nc against the PCB geometry and render cnc/previews/*.png.

Checks: XYZ bounds of every file, only whitelisted G/M codes, isolation grooves never cut into copper,
every pair of different copper islands is separated, every drill hits its pad, outline does not cut
into the board. Run after generate_gcode.py (it re-uses the geometry it computes)."""
import math, re, sys, subprocess, pickle, tomllib
from pathlib import Path
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
G = ROOT / "cnc/gcode"; P = ROOT / "cnc/previews"; P.mkdir(exist_ok=True)
CFG = tomllib.load(open(ROOT / "cnc/cam_config.toml", "rb"))
subprocess.run([sys.executable, str(ROOT / "cnc/scripts/generate_gcode.py")], check=True, stdout=subprocess.DEVNULL)
geo = pickle.load(open("/tmp/cam_geom.pkl", "rb"))
copper, outline, holes, groove, r_t = geo["copper"], geo["outline"], geo["holes"], geo["groove"], geo["r_t"]
ALLOWED = {"G0", "G1", "G2", "G3", "G4", "G17", "G21", "G90", "G94", "M3", "M5", "M30"}

def parse(path):
    """Return list of moves (kind, x0,y0,z0, x1,y1,z1, arc) ; arcs are linearised."""
    x = y = z = 0.0; mode = "G0"; moves = []; codes = set(); time_min = 0.0; feed = 100.0
    for raw in open(path):
        line = re.sub(r"\(.*?\)", "", raw).strip()
        if not line: continue
        words = dict(); gs = []
        for w, v in re.findall(r"([A-Z])(-?[\d.]+)", line):
            if w in "GM": gs.append(f"{w}{int(float(v))}")
            else: words[w] = float(v)
        codes.update(gs)
        for g in gs:
            if g in ("G0", "G1", "G2", "G3"): mode = g
        if "F" in words: feed = words["F"]
        if not any(k in words for k in "XYZ") or any(g == "G4" for g in gs): continue
        nx, ny, nz = words.get("X", x), words.get("Y", y), words.get("Z", z)
        if mode in ("G2", "G3"):
            cx, cy = x + words.get("I", 0), y + words.get("J", 0)
            r = math.hypot(x - cx, y - cy); a0 = math.atan2(y - cy, x - cx); a1 = math.atan2(ny - cy, nx - cx)
            sweep = a1 - a0
            if mode == "G2": sweep = sweep - 2*math.pi if sweep >= -1e-9 else sweep
            else: sweep = sweep + 2*math.pi if sweep <= 1e-9 else sweep
            n = 48; px, py, pz = x, y, z
            for i in range(1, n + 1):
                a = a0 + sweep * i / n
                qx, qy, qz = cx + r*math.cos(a), cy + r*math.sin(a), z + (nz - z) * i / n
                moves.append(("G1", px, py, pz, qx, qy, qz)); px, py, pz = qx, qy, qz
            time_min += abs(sweep) * r / feed
        else:
            moves.append((mode, x, y, z, nx, ny, nz))
            d = math.dist((x, y, z), (nx, ny, nz))
            time_min += d / (feed if mode == "G1" else 3000)
        x, y, z = nx, ny, nz
    return moves, codes, time_min

ok = True
def check(cond, msg):
    global ok
    print(("  OK   " if cond else "  FAIL ") + msg); ok &= bool(cond)

W, H = geo["W"], geo["H"]
report = {}
for f in sorted(G.glob("*.nc")):
    moves, codes, t = parse(f)
    xs = [m[4] for m in moves] + [m[1] for m in moves]; ys = [m[5] for m in moves] + [m[2] for m in moves]
    zs = [m[6] for m in moves]
    report[f.name] = (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), t, moves)
    print(f"{f.name}: X {min(xs):.2f}..{max(xs):.2f}  Y {min(ys):.2f}..{max(ys):.2f}  Z {min(zs):.3f}..{max(zs):.3f}  ~{t:.1f} min (feed moves + rapids @3000)")
    check(codes <= ALLOWED, f"only allowed codes {sorted(codes)}")
    check(min(xs) >= -1.5 and max(xs) <= W + 1.5 and min(ys) >= -1.5 and max(ys) <= H + 1.5, "XY inside board +1.5 mm margin")
    check(min(zs) >= -2.0, "Z not deeper than -2.0 mm")
    check(all(m[0] == "G1" or m[6] >= 0 for m in moves) and all(m[0] == "G1" or m[3] >= 0 or m[6] >= 0 for m in moves), "no rapid moves below Z0")

# isolation
moves = report["01_isolation_vbit30.nc"][7]
cuts = [LineString([(m[1], m[2]), (m[4], m[5])]) for m in moves if m[0] == "G1" and m[3] < 0 and m[6] < 0 and (m[1], m[2]) != (m[4], m[5])]
swept = unary_union([c.buffer(groove / 2, quad_segs=8) for c in cuts])
over = swept.intersection(copper).area
check(over < 0.005, f"isolation cuts into copper: {over:.4f} mm2")
dmin = min(copper.distance(c) for c in cuts)
check(dmin >= groove / 2 - 0.01, f"min distance tool centre -> copper {dmin:.3f} mm (>= groove/2 {groove/2:.3f})")
islands = list(copper.geoms) if hasattr(copper, "geoms") else [copper]
remaining = outline.difference(swept)
rem = list(remaining.geoms) if hasattr(remaining, "geoms") else [remaining]
bad = 0
for r in rem:
    hit = [i for i, isl in enumerate(islands) if r.intersects(isl.buffer(-0.01))]
    if len(hit) > 1: bad += 1
check(bad == 0, f"{len(islands)} copper islands, all electrically separated by the grooves (shorts found: {bad})")

# drills
for f in [k for k in report if "_drill_" in k]:
    d = float(re.search(r"drill_([\d.]+)mm", f).group(1))
    pts = {(round(m[4], 3), round(m[5], 3)) for m in report[f][7] if m[6] < -1}
    exp = {(round(h[1], 3), round(h[2], 3)) for h in holes if abs(h[0] - d) < 1e-6}
    check(pts == exp, f"{f}: {len(pts)} holes = Excellon {len(exp)}")
    pth = [(h[1], h[2]) for h in holes if abs(h[0] - d) < 1e-6 and h[3] == "PTH"]
    inpad = sum(1 for x, y in pth if copper.contains(Point(x, y).buffer(d / 2 + 0.2)))
    check(inpad == len(pth), f"{f}: {inpad}/{len(pth)} PTH holes inside a pad with >=0.2 mm annular ring")

# outline / slot: tool must stay outside the board body
for f in [k for k in report if "outline" in k or "slot" in k]:
    cutm = [LineString([(m[1], m[2]), (m[4], m[5])]) for m in report[f][7] if m[0] == "G1" and m[6] < 0 and (m[1], m[2]) != (m[4], m[5])]
    sw = unary_union([c.buffer(r_t, quad_segs=8) for c in cutm])
    bad_area = sw.intersection(outline.buffer(-0.02)).area
    # 2.4 mm holes are allowed to be cut inside the board
    allowed = unary_union([Point(h[1], h[2]).buffer(h[0] / 2 + 0.03) for h in holes if h[0] > 2])
    check(sw.intersection(outline.buffer(-0.02)).difference(allowed).area < 0.01, f"{f}: end mill does not cut into the board ({bad_area:.3f} mm2 incl. 2.4 mm holes)")
    check(copper.distance(sw) > 0.2, f"{f}: >0.2 mm from copper ({copper.distance(sw):.2f} mm)")

# full-depth coverage: slot and 2.4 mm holes must be cut out completely, outline must keep board size
zbot = CFG["endmill"]["total_depth"]
for f in [k for k in report if "slot" in k]:
    deep = [LineString([(m[1], m[2]), (m[4], m[5])]) for m in report[f][7]
            if m[0] == "G1" and min(m[3], m[6]) <= zbot + 1e-3 and (m[1], m[2]) != (m[4], m[5])]
    sw = unary_union([c.buffer(r_t, quad_segs=16) for c in deep])
    slots = [Polygon(i) for p in (outline.geoms if hasattr(outline, "geoms") else [outline]) for i in p.interiors]
    left = sum(sl.difference(sw).area for sl in slots)
    check(left < 0.01, f"{f}: slot cut through on full width ({left:.4f} mm2 left)")
    hl = sum(Point(h[1], h[2]).buffer(h[0] / 2 - 0.01, quad_segs=32).difference(sw).area for h in holes if h[0] > 2)
    check(hl < 0.01, f"{f}: 2.4 mm holes fully cleared ({hl:.4f} mm2 left)")
for f in [k for k in report if "outline" in k]:
    pts = [(m[4], m[5]) for m in report[f][7] if m[0] == "G1" and m[6] <= zbot + 1e-3]
    ext = Polygon(outline.exterior.coords) if not hasattr(outline, "geoms") else Polygon(outline.geoms[0].exterior.coords)
    ds = [ext.exterior.distance(Point(q)) for q in pts]
    check(abs(min(ds) - r_t) < 0.01 and max(ds) < r_t + 0.02, f"{f}: tool centre {min(ds):.3f}..{max(ds):.3f} mm from edge (r={r_t}) -> board keeps {W:.2f} x {H:.2f}")

# ---------- render
def draw(ax, show_iso=True, show_all=True):
    for isl in islands:
        ax.fill(*isl.exterior.xy, color="#d9a441", lw=0)
        for i in isl.interiors: ax.fill(*i.xy, color="white", lw=0)
    for p in (outline.geoms if hasattr(outline, "geoms") else [outline]):
        ax.plot(*p.exterior.xy, color="black", lw=0.6)
        for i in p.interiors: ax.plot(*i.xy, color="black", lw=0.6)
    if show_iso:
        for g in (swept.geoms if hasattr(swept, "geoms") else [swept]):
            ax.fill(*g.exterior.xy, color="#1f5fbf", alpha=0.55, lw=0)
            for i in g.interiors: ax.fill(*i.xy, color="white", lw=0, alpha=0)
    if show_all:
        cols = {"0.8": "#c00000", "1.0": "#008000", "1.2": "#8000a0"}
        for h in holes:
            c = cols.get(f"{h[0]:.1f}", "#ff6000")
            ax.add_patch(plt.Circle((h[1], h[2]), h[0] / 2, fill=False, color=c, lw=0.8))
        for f in [k for k in report if "outline" in k or "slot" in k]:
            for m in report[f][7]:
                if m[0] == "G1" and m[6] < -1.0:
                    ax.plot([m[1], m[4]], [m[2], m[5]], color="#ff6000", lw=0.5)
                elif m[0] == "G1" and m[6] < 0:
                    ax.plot([m[1], m[4]], [m[2], m[5]], color="#00a0a0", lw=1.2)
    ax.set_aspect("equal"); ax.set_xlim(-2.5, W + 2.5); ax.set_ylim(-2.5, H + 2.5)
    ax.plot([0], [0], "k+", ms=14, mew=1.5); ax.annotate("X0 Y0", (0, 0), (1.2, -2.2), fontsize=8)
    ax.grid(True, lw=0.2); ax.set_xlabel("X [mm]"); ax.set_ylabel("Y [mm]")

fig, ax = plt.subplots(figsize=(11, 9.5), dpi=150); fig.patch.set_facecolor("white")
draw(ax)
ax.set_title("domofon-esp32 – toolpaths, COPPER SIDE UP (mirrored)\n"
             "copper = gold, isolation grooves = blue, drills: 0.8 red / 1.0 green / 1.2 purple / 2.4 orange,\n"
             "end mill outline = orange, tabs = teal (Z above board bottom)", fontsize=9)
fig.tight_layout(); fig.savefig(P / "toolpaths_overview.png", facecolor="white")
fig, ax = plt.subplots(figsize=(10, 10), dpi=200); draw(ax)
ax.set_xlim(20, 42); ax.set_ylim(10, 32); ax.set_title("zoom: isolation detail (X20-42, Y10-32)", fontsize=9)
fig.tight_layout(); fig.savefig(P / "toolpaths_zoom_isolation.png", facecolor="white")
print("\nRESULT:", "ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
sys.exit(0 if ok else 1)
