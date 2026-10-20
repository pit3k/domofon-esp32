# Placement (mm, KiCad coords: x right, y down, top view). (x, y, rotation deg CCW)
DX, DY = 0.7, 0.5          # ESP-side global offset (room for GND channel along left/top edge)
XB = 31.0 + DX             # isolation barrier centre line
LX = DX + 1.0              # line-side offset
H = 45.9
EY = 12.39 + DY            # ESP centre y (pin row 1 at EY-8.89)
TY = 36.5                  # T1 centre y
E = lambda x, y, r: (x + DX, y + DY, r)
L = lambda x, y, r: (x + LX, y, r)
PLACEMENT = {
 'ESP': E(11.0, 12.39, 0),
 # under ESP (low lying parts only; ESP on female headers)
 'R8a': E(6.0, 7.31, 270), 'R8b': E(8.5, 9.85, 270), 'R6a': E(6.0, 18.01, 270),
 'D4':  E(11.0, 11.12, 270), 'R10': E(13.5, 12.39, 270), 'R3': E(16.0, 12.39, 90),
 'R9':  E(16.0, 22.55, 90), 'D5': E(13.5, 21.28, 270), 'R11': E(8.5, 20.01, 270),
 # corridor ESP <-> barrier
 'JP1': E(21.7, 17.01, 90),
 'X2':  E(21.8, 2.9, 90), 'R4': E(24.3, 14.93, 270), 'C1': E(24.6, 22.19, 0),
 # barrier parts
 'U1':  (XB, EY, 180), 'K1': (XB, EY+6.88, 0), 'T1': (XB, TY, 0),
 # ESP side bottom ("U" chain: B -> R6b -> C -> C4 -> R7 -> D -> C6 -> N_C6)
 'R6b': E(2.6, 30.08, 270), 'C2': E(7.7, 26.4, 0), 'C3': E(7.0, 32.6, 90),
 'C7':  E(14.0, 31.0, 270), 'C4': E(6.0, 41.0, 0), 'R7': E(10.0, 40.1, 270), 'C6': E(19.4, 29.04, 90),
 # line side
 'J1':  L(44.5, 8.0, 0), 'R1': L(41.3, 16.6, 180), 'C8': L(41.3, 19.2, 0), 'X1': L(46.5, 22.4, 0),
 'D2':  L(49.04, 29.0, 0), 'R5': L(41.8, 35.1, 270), 'C5': L(48.5, 37.5, 0),
}
W = 53.8 + LX
OUTLINE = (0.0, 0.0, W, H, 1.0)   # x1,y1,x2,y2,corner radius
BARRIER = {
 'keepout': [(XB-2.0, -1.0, XB+2.0, H+1.0)],   # no copper strip (4 mm)
 'silk': [(XB, 0.5, XB, EY-3.6), (XB, EY+10.4, XB, H-0.5)],
}
EXTRA = {
 'slots': [(XB-1.0, EY-2.7, XB+1.0, EY+9.6)],
 'texts': [('LINIA', 45.0+LX, H-1.2, 1.0)],
}
