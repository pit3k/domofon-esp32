"""Report tracks narrower than their net-class width. usage: check_track_widths.py board.kicad_pcb"""
import pcbnew, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netlist import LINE_NETS, POWER_NETS
b=pcbnew.LoadBoard(sys.argv[1])
for t in b.GetTracks():
    n=t.GetNetname(); w=pcbnew.ToMM(t.GetWidth())
    need = 1.0 if (n in LINE_NETS or n in POWER_NETS) else 0.6
    if w < need-1e-3:
        s,e=t.GetStart(),t.GetEnd()
        print(n, w, (round(pcbnew.ToMM(s.x),1),round(pcbnew.ToMM(s.y),1)), (round(pcbnew.ToMM(e.x),1),round(pcbnew.ToMM(e.y),1)))
