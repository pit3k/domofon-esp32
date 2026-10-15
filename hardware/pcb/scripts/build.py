#!/usr/bin/env python3
"""Build domofon single-sided PCB (KiCad 9) from footprints.py + netlist.py + PLACEMENT."""
import sys, json, math, os
import pcbnew
from pcbnew import VECTOR2I, FromMM, ToMM
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from footprints import FP
from netlist import NETS, PARTS, LINE_NETS, POWER_NETS
from placement import PLACEMENT, OUTLINE, BARRIER, EXTRA

# outputs go to hardware/pcb/work/ (scripts live in hardware/pcb/scripts/)
PCB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(PCB_DIR, 'work')
NAME = 'domofon'

def P(x, y): return VECTOR2I(FromMM(x), FromMM(y))

def lset(*layers):
    s = pcbnew.LSET()
    for l in layers: s.AddLayer(l)
    return s

def add_line(fp_or_board, layer, x1, y1, x2, y2, w=0.15, fp=None):
    sh = pcbnew.PCB_SHAPE(fp_or_board)
    sh.SetShape(pcbnew.SHAPE_T_SEGMENT)
    sh.SetStart(P(x1, y1)); sh.SetEnd(P(x2, y2))
    sh.SetLayer(layer); sh.SetWidth(FromMM(w))
    return sh

def build(placement=PLACEMENT):
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    board.SetCopperLayerCount(2)
    # nets
    netobj = {}
    for n in NETS:
        ni = pcbnew.NETINFO_ITEM(board, n)
        board.Add(ni); netobj[n] = ni
    pin2net = {}
    for n, pins in NETS.items():
        for r, p in pins: pin2net[(r, p)] = n
    fps = {}
    for ref, (fpname, value) in PARTS.items():
        g = FP[fpname]
        fp = pcbnew.FOOTPRINT(board)
        fp.SetReference(ref); fp.SetValue(value)
        fp.SetFPID(pcbnew.LIB_ID('domofon', fpname))
        fp.SetAttributes(pcbnew.FP_THROUGH_HOLE)
        for (num, x, y, shp, sx, sy, d) in g['pads']:
            pad = pcbnew.PAD(fp)
            pad.SetNumber(num)
            pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
            pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE if shp == 'C' else pcbnew.PAD_SHAPE_OVAL)
            pad.SetSize(P(sx, sy))
            pad.SetDrillSize(P(d, d))
            pad.SetLayerSet(lset(pcbnew.B_Cu, pcbnew.B_Mask))
            pad.SetFPRelativePosition(P(x, y))
            if (ref, num) in pin2net:
                pad.SetNet(netobj[pin2net[(ref, num)]])
            fp.Add(pad)
        for (x, y, d) in g.get('npth', []):
            pad = pcbnew.PAD(fp)
            pad.SetNumber('')
            pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
            pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
            pad.SetSize(P(d, d)); pad.SetDrillSize(P(d, d))
            pad.SetLayerSet(lset(pcbnew.B_Cu, pcbnew.B_Mask))
            pad.SetFPRelativePosition(P(x, y))
            fp.Add(pad)
        # body outline on F.SilkS + courtyard
        for b in g['body']:
            if b[0] == 'c':
                _, cx, cy, r = b
                for layer in (pcbnew.F_SilkS, pcbnew.F_CrtYd):
                    sh = pcbnew.PCB_SHAPE(fp); sh.SetShape(pcbnew.SHAPE_T_CIRCLE)
                    sh.SetCenter(P(cx, cy)); sh.SetEnd(P(cx + r + (0.25 if layer == pcbnew.F_CrtYd else 0), cy))
                    sh.SetLayer(layer); sh.SetWidth(FromMM(0.12 if layer == pcbnew.F_SilkS else 0.05))
                    fp.Add(sh)
            else:
                x1, y1, x2, y2 = b
                cm = 0.05 if fpname.startswith('R0207') else 0.25
                for layer, m, w in ((pcbnew.F_SilkS, 0, 0.12), (pcbnew.F_CrtYd, cm, 0.05)):
                    if fpname == 'ESP' and layer == pcbnew.F_CrtYd: continue  # ESP sits above other parts on headers
                    pts = [(x1-m, y1-m), (x2+m, y1-m), (x2+m, y2+m), (x1-m, y2+m)]
                    for i in range(4):
                        a, c = pts[i], pts[(i+1) % 4]
                        sh = add_line(fp, layer, a[0], a[1], c[0], c[1], w)
                        sh.SetParent(fp)
                        fp.Add(sh)
        if g.get('wire'):
            sh = add_line(fp, pcbnew.F_SilkS, -7.6, 0, 7.6, 0, 0.3); sh.SetParent(fp); fp.Add(sh)
        if g.get('pin1mark'):
            mx, my = g['pin1mark']
            sh = pcbnew.PCB_SHAPE(fp); sh.SetShape(pcbnew.SHAPE_T_CIRCLE)
            sh.SetCenter(P(mx, my)); sh.SetEnd(P(mx + 0.35, my)); sh.SetLayer(pcbnew.F_SilkS)
            sh.SetWidth(FromMM(0.2)); sh.SetFilled(True); fp.Add(sh)
        x, y, rot = placement[ref]
        board.Add(fp)
        fp.SetPosition(P(x, y))
        fp.SetOrientationDegrees(rot)
        # reference text on silk, value on fab
        fp.Reference().SetLayer(pcbnew.F_SilkS)
        fp.Reference().SetTextSize(P(1.0, 1.0)); fp.Reference().SetTextThickness(FromMM(0.15))
        fp.Reference().SetPosition(P(x, y)); fp.Reference().SetTextAngleDegrees(0)
        fp.Value().SetLayer(pcbnew.F_Fab)
        fp.Value().SetPosition(P(x, y + 1.2)); fp.Value().SetTextAngleDegrees(0)
        fps[ref] = fp
    # board outline
    x1, y1, x2, y2, r = OUTLINE
    def edge(a, b, c, d):
        sh = add_line(board, pcbnew.Edge_Cuts, a, b, c, d, 0.1); board.Add(sh)
    if r <= 0:
        edge(x1, y1, x2, y1); edge(x2, y1, x2, y2); edge(x2, y2, x1, y2); edge(x1, y2, x1, y1)
    else:
        edge(x1+r, y1, x2-r, y1); edge(x2, y1+r, x2, y2-r); edge(x2-r, y2, x1+r, y2); edge(x1, y2-r, x1, y1+r)
        for (cx, cy, sa) in ((x1+r, y1+r, 180), (x2-r, y1+r, 270), (x2-r, y2-r, 0), (x1+r, y2-r, 90)):
            arc = pcbnew.PCB_SHAPE(board); arc.SetShape(pcbnew.SHAPE_T_ARC)
            arc.SetCenter(P(cx, cy))
            sa_r = math.radians(sa)
            arc.SetStart(P(cx + r*math.cos(sa_r), cy + r*math.sin(sa_r)))
            arc.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T), True)
            arc.SetLayer(pcbnew.Edge_Cuts); arc.SetWidth(FromMM(0.1)); board.Add(arc)
    # internal slots (milled) under optocouplers - Edge.Cuts closed rectangles with round ends
    for (sx1, sy1, sx2, sy2) in EXTRA.get('slots', []):
        w = sx2 - sx1; h = sy2 - sy1
        if h >= w:  # vertical slot
            rr = w/2; cx = (sx1+sx2)/2
            edge(sx1, sy1+rr, sx1, sy2-rr); edge(sx2, sy1+rr, sx2, sy2-rr)
            for (cy, st) in ((sy1+rr, 180), (sy2-rr, 0)):
                arc = pcbnew.PCB_SHAPE(board); arc.SetShape(pcbnew.SHAPE_T_ARC)
                arc.SetCenter(P(cx, cy)); a = math.radians(st)
                arc.SetStart(P(cx + rr*math.cos(a), cy + rr*math.sin(a)))
                arc.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(180, pcbnew.DEGREES_T), True)
                arc.SetLayer(pcbnew.Edge_Cuts); arc.SetWidth(FromMM(0.1)); board.Add(arc)
    # silkscreen: isolation barrier marker + labels
    for (a, b, c, d) in BARRIER['silk']:
        board.Add(add_line(board, pcbnew.F_SilkS, a, b, c, d, 0.2))
    for (txt, x, y, sz) in EXTRA.get('texts', []):
        t = pcbnew.PCB_TEXT(board); t.SetText(txt); t.SetPosition(P(x, y)); t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(P(sz, sz)); t.SetTextThickness(FromMM(0.15)); board.Add(t)
    # design settings
    ds.m_TrackMinWidth = FromMM(0.6)
    ds.m_MinClearance = FromMM(0.4)
    ds.m_ViasMinSize = FromMM(1.6)
    ds.m_MinThroughDrill = FromMM(0.8)
    ds.m_HoleClearance = FromMM(0.25)
    ds.m_CopperEdgeClearance = FromMM(0.5)
    return board, fps, netobj

def pad_report(board):
    out = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            p = pad.GetPosition()
            out.append((fp.GetReference(), pad.GetNumber(), round(ToMM(p.x), 2), round(ToMM(p.y), 2), pad.GetNetname()))
    return out

if __name__ == '__main__':
    board, fps, nets = build()
    os.makedirs(OUT, exist_ok=True)
    fn = os.path.join(OUT, NAME + '_unrouted.kicad_pcb')
    board.Save(fn)
    for r in pad_report(board): print(*r)
