# Footprint geometry definitions (local coordinates, mm, KiCad: x right, y down, top view)
# pad tuple: (number, x, y, shape 'C'|'O', size_x, size_y, drill)  ; drill 0 => no hole (not used)
# 'npth' list: (x, y, drill)
# body: list of rect (x1,y1,x2,y2) or circle ('c', x, y, r) for silkscreen/courtyard
FP = {}

def dip4(name):
    # DIP4 7.62 x 2.54, pin1 top-left, counter-clockwise
    return dict(pads=[('1',-3.81,-1.27,'O',2.4,1.7,1.0),('2',-3.81,1.27,'O',2.4,1.7,1.0),
                      ('3',3.81,1.27,'O',2.4,1.7,1.0),('4',3.81,-1.27,'O',2.4,1.7,1.0)],
                body=[(-3.25,-2.4,3.25,2.4)], pin1mark=(-3.25,-2.4))
FP['DIP4'] = dip4('DIP4')

# Bourns LM-NP-1001-B1L: 2 rows x 4 @2.54, rows 12.7 apart, body 17.7x17.7, only pins 1,4,5,8 populated.
# Placed with winding rows vertical: pins 1..4 at x=-6.35 (top->bottom), 8..5 at x=+6.35 (top->bottom)
FP['T1'] = dict(pads=[('1',-6.35,-3.81,'C',2.2,2.2,0.8),('4',-6.35,3.81,'C',2.2,2.2,0.8),
                      ('8',6.35,-3.81,'C',2.2,2.2,0.8),('5',6.35,3.81,'C',2.2,2.2,0.8)],
                body=[(-8.85,-8.85,8.85,8.85)], pin1mark=(-8.85,-8.85))

# ESP32-C3 SuperMini HW-466B, top view, USB-C at top (-y). Pins L1..L8 at x=-7.62, R1..R8 at x=+7.62
_esp = []
for k in range(8):
    y = -8.89 + 2.54*k
    _esp.append(('L%d'%(k+1), -7.62, y, 'O', 2.2, 1.7, 1.0))
    _esp.append(('R%d'%(k+1),  7.62, y, 'O', 2.2, 1.7, 1.0))
FP['ESP'] = dict(pads=_esp, body=[(-9.0,-10.16,9.0,12.36),(-4.5,-12.2,4.5,-6.0)], pin1mark=None)

def r_lying(p, pad=1.9, drill=0.8, body=(3.2,1.15)):
    return dict(pads=[('1',-p/2,0,'C',pad,pad,drill),('2',p/2,0,'C',pad,pad,drill)],
                body=[(-body[0],-body[1],body[0],body[1])], pin1mark=None)
FP['R0207_P7.62'] = r_lying(7.62)
FP['R0207_P10.16'] = r_lying(10.16)
# C8 0.47uF/250V MKT in the former R2 holes: identical pads/drills to R0207_P7.62 (copper unchanged); 7.5 mm pitch box
FP['CFILM_P7.62'] = r_lying(7.62)
# Vishay MBE0414 1W: body d=4, L=11.5 -> 15.24 pitch
FP['R0414_P15.24'] = r_lying(15.24, pad=2.4, drill=1.2, body=(5.9,2.1))
# DO-15 lying 12.7 pitch (P6KE)
FP['DO15_P12.7'] = r_lying(12.7, pad=2.4, drill=1.2, body=(3.9,1.9))
# DO-34 (BAT85) lying 5.08 pitch, pin1 = cathode (band)
FP['DO34_P5.08'] = dict(pads=[('1',-2.54,0,'C',1.8,1.8,0.8),('2',2.54,0,'C',1.8,1.8,0.8)],
                        body=[(-1.6,-0.9,1.6,0.9)], pin1mark=(-1.6,-0.9))
# Film cap box, pitch 5.08, body 7.2 x 4.5 (worst case)
FP['CFILM_P5.08'] = dict(pads=[('1',-2.54,0,'C',2.0,2.0,0.8),('2',2.54,0,'C',2.0,2.0,0.8)],
                         body=[(-3.6,-1.75,3.6,1.75)], pin1mark=None)
# Radial electrolytic d=5, pitch 2.0 (Panasonic ECEA 5x11)
FP['CP_D5_P2.0'] = dict(pads=[('1',-1.0,0,'O',1.4,2.2,0.8),('2',1.0,0,'O',1.4,2.2,0.8)],
                        body=[('c',0,0,2.55)], pin1mark=(-2.6,-2.6))
# ACP CA9V (CA9 V10): pins 1,3 at (+-2.5,0), wiper 2 at (0,-10); body 9.8 x 10
FP['CA9V'] = dict(pads=[('1',-2.5,0,'C',2.6,2.6,1.2),('3',2.5,0,'C',2.6,2.6,1.2),('2',0,-10,'C',2.6,2.6,1.2)],
                  body=[(-4.9,-10.5,4.9,0.5)], pin1mark=None)
# XY308-2P 2.54: pins along y, wire entry to +x; body ~6.2 deep (assumed)
FP['XY308_2P'] = dict(pads=[('1',0,0,'O',2.6,1.8,1.2),('2',0,2.54,'O',2.6,1.8,1.2)],
                      body=[(-3.1,-1.27,3.1,3.81)], pin1mark=None)
# Adam Tech MTJ-642BX2 (RJ11 6P4C) - recommended PCB layout, opening facing +x, origin = peg line centre
FP['MTJ642'] = dict(pads=[('2',-2.30,0.51,'C',1.7,1.7,1.0),('3',-4.84,-0.51,'C',1.7,1.7,1.0)],
                    npth=[(0,-6.0,2.4),(0,6.0,2.4),(-2.30,-1.53,1.0),(-4.84,1.53,1.0)],  # pins 1,4 NC -> NPTH holes
                    body=[(-7.0,-6.1,6.0,6.1)], pin1mark=None)
# DO-15 standing, pitch 5.08 (body d=3.6 over pin 1)
FP['DO15_P5.08_V'] = dict(pads=[('1',-2.54,0,'C',2.4,2.4,1.2),('2',2.54,0,'C',2.4,2.4,1.2)],
                          body=[('c',-2.54,0,1.9)], pin1mark=None)
# Film cap with 7.62 (bent) option not used

# Wire jumper (top side, insulated wire), pitch 17.78
FP['WIRE_P10.16'] = dict(pads=[('1',-8.89,0,'C',1.9,1.9,0.8),('2',8.89,0,'C',1.9,1.9,0.8)], body=[], pin1mark=None, wire=True)
