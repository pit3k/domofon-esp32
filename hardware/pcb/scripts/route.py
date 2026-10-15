#!/usr/bin/env python3
"""Export DSN (single layer B.Cu), autoroute with Freerouting CLI, import SES.

usage: route.py <unrouted.kicad_pcb> <routed.kicad_pcb> [passes]
"""
import re, subprocess, sys, os
import pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netlist import LINE_NETS, POWER_NETS, NETS
from placement import BARRIER

PCB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = PCB_DIR  # intermediate files in hardware/pcb/work/ (git-ignored)
# Freerouting 2.x jar + Java 21+ runtime; override with env vars
FR_JAR = os.environ.get('FREEROUTING_JAR', 'freerouting.jar')
JAVA = os.environ.get('JAVA', 'java')

def postprocess(dsn_in, dsn_out):
    s = open(dsn_in).read()
    # single routing layer: drop F.Cu
    s = re.sub(r'\(layer F\.Cu\s*\(type signal\)\s*\(property\s*\(index 0\)\s*\)\s*\)', '', s)
    s = re.sub(r'\s*\(keepout "" \(circle F\.Cu [^)]*\)\)', '', s)
    # global rule
    s = s.replace('(rule\n      (width 200)\n      (clearance 200)\n      (clearance 50 (type smd_smd))\n    )',
                  '(rule\n      (width 600)\n      (clearance 500)\n      (clearance 500 (type smd_smd))\n    )')
    # barrier keepouts (y negated in DSN)
    ko = ''
    for (x1, y1, x2, y2) in BARRIER['keepout']:
        ko += '    (keepout "barrier" (rect signal %d %d %d %d))\n' % (x1*1000, -y2*1000, x2*1000, -y1*1000)
    s = s.replace('    (via "Via', ko + '    (via "Via', 1)
    # classes
    m = re.search(r'\(class kicad_default.*?\n    \)\n', s, re.S)
    sig = [n for n in NETS if n not in LINE_NETS and n not in POWER_NETS]
    def cls(name, nets, w, c):
        return ('    (class %s %s\n      (circuit\n        (use_via "Via[0-1]_600:300_um")\n      )\n'
                '      (rule\n        (width %d)\n        (clearance %d)\n      )\n    )\n') % (name, ' '.join(nets), w, c)
    newcls = cls('sig', sig, 600, 500) + cls('pwr', POWER_NETS, 1000, 500) + cls('line', LINE_NETS, 1000, 500)
    s = s[:m.start()] + newcls.lstrip() + s[m.end():]
    open(dsn_out, 'w').write(s)

def run(board_in, ses_out, passes=40):
    b = pcbnew.LoadBoard(board_in)
    raw = os.path.join(OUT, 'work', 'raw.dsn'); dsn = os.path.join(OUT, 'work', 'board.dsn')
    os.makedirs(os.path.dirname(raw), exist_ok=True)
    pcbnew.ExportSpecctraDSN(b, raw)
    postprocess(raw, dsn)
    log = open(os.path.join(OUT, 'work', 'freerouting.log'), 'w')
    subprocess.run([JAVA,'-Djava.awt.headless=true','-jar',FR_JAR,'--gui.enabled=false','--router.automatic_neckdown=false','--router.copper_to_edge_clearance_um=600','-de', dsn, '-do', ses_out, '-mp', str(passes), '-mt', '4'], stdout=log, stderr=subprocess.STDOUT, timeout=1200)
    return dsn

if __name__ == '__main__':
    board_in = sys.argv[1]; out = sys.argv[2]
    ses = os.path.join(OUT, 'work', 'board.ses')
    run(board_in, ses, int(sys.argv[3]) if len(sys.argv) > 3 else 40)
    b = pcbnew.LoadBoard(board_in)
    ok = pcbnew.ImportSpecctraSES(b, ses)
    print('import', ok)
    # undo Freerouting neck-downs: force class widths
    for t in b.GetTracks():
        n = t.GetNetname()
        w = 1.0 if (n in LINE_NETS or n in POWER_NETS) else 0.6
        t.SetWidth(pcbnew.FromMM(w))
    # wire jumpers: model the top-side wire as an F.Cu track between JP pads
    for fp in b.GetFootprints():
        if fp.GetReference().startswith('JP'):
            pads = list(fp.Pads())
            for p in pads:
                ls = p.GetLayerSet(); ls.AddLayer(pcbnew.F_Cu); p.SetLayerSet(ls)
            tr = pcbnew.PCB_TRACK(b)
            tr.SetStart(pads[0].GetPosition()); tr.SetEnd(pads[1].GetPosition())
            tr.SetLayer(pcbnew.F_Cu); tr.SetWidth(pcbnew.FromMM(1.0)); tr.SetNet(pads[0].GetNet())
            b.Add(tr)
    b.Save(out)
