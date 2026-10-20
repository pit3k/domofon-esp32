#!/usr/bin/env python3
"""Schemat interfejsu domofonu analogowego <-> ESP32-C3 SuperMini (HW-466B), ESPHome.

Generowanie obrazka:
    pip install schemdraw pillow
    python3 schematic.py   # -> schematic.svg + schematic.png (biale tlo)

Konwencja pinow ESP32-C3 SuperMini (HW-466B):
  widok z GORY (strona elementow: ESP32-C3, przyciski BOOT/RST), zlacze USB-C u gory.
  Lewy rzad  L1..L8 (od USB-C w dol): GPIO5, GPIO6, GPIO7, GPIO8, GPIO9, GPIO10, GPIO20, GPIO21
  Prawy rzad R1..R8 (od USB-C w dol): 5V, GND, 3V3, GPIO4, GPIO3, GPIO2, GPIO1, GPIO0
  Zrodlo: rysunek wymiarowy WMNologo (dimension.png, widok od strony elementow: 5V/G/3.3 po prawej,
  "21" lewy dolny, "0" prawy dolny) + pinout nologo.tech / NuttX (kolejnosc w rzedach).
"""
import os
import schemdraw
import schemdraw.elements as elm

schemdraw.config(fontsize=13, unit=3)

XI = 26            # bariera izolacji (x)
XL1, XL2 = 42, 46  # szyny linii L1 / L2
Y_RING = 9.25      # tor dzwonka (GPIO3)
Y_HOOK = 5         # off-hook (GPIO4)
Y_RX = 0.5         # odbior DTMF (GPIO1, ADC)
Y_TX = -4.5        # nadawanie DTMF - wiersz gorny (GPIO6, wezel A, filtr, T1)
Y_TX2 = -6.5       # nadawanie DTMF - wiersz dolny (GPIO5)
PIN_FS = 9         # czcionka numerow pinow
PIN_COL = '#b03000'

d = schemdraw.Drawing(show=False)
d.config(bgcolor='white')


def wire(*pts, **kw):
    for a, b in zip(pts, pts[1:]):
        d.add(elm.Line(**kw).at(a).to(b))


def dot(p, **kw):
    d.add(elm.Dot(**kw).at(p))


def gnd(p):
    d.add(elm.Ground().at(p))


def txt(p, s, **kw):
    kw.setdefault('fontsize', 11)
    d.add(elm.Label().at(p).label(s, **kw))


def pinno(p, s, dx=0.0, dy=0.3, halign='center'):
    """Numer pinu przy koncowce symbolu."""
    d.add(elm.Label().at((p[0] + dx, p[1] + dy)).label(s, fontsize=PIN_FS, color=PIN_COL, halign=halign))


# =====================================================================
# ESP32-C3 SuperMini (HW-466B) - widok z gory, USB-C u gory
# =====================================================================
XE, XEL = 0.0, -7.0          # prawa / lewa krawedz symbolu
YP0, PP = 13.0, 1.5          # y pinu nr 1 (przy USB-C) i raster rysunkowy
YB, YT = 1.6, 14.0           # dol / gora prostokata
STUB = 0.6
RIGHT = ['5V', 'GND', '3V3', 'GPIO4', 'GPIO3', 'GPIO2', 'GPIO1', 'GPIO0']
LEFT = ['GPIO5', 'GPIO6', 'GPIO7', 'GPIO8', 'GPIO9', 'GPIO10', 'GPIO20', 'GPIO21']
USED = {'5V': '5V', 'GND': 'GND', '3V3': '3V3',
        'GPIO4': 'GPIO4  off-hook', 'GPIO3': 'GPIO3  dzwonek', 'GPIO1': 'GPIO1  ADC odb.',
        'GPIO5': 'GPIO5  697 Hz', 'GPIO6': 'GPIO6  1209 Hz'}
NC_NOTE = {'GPIO2': 'strap', 'GPIO8': 'LED/strap', 'GPIO9': 'BOOT/strap', 'GPIO20': 'RX', 'GPIO21': 'TX'}

d.add(elm.Rect((XEL, YB), (XE, YT)))
# zlacze USB-C na gornej krawedzi
d.add(elm.Rect((-4.6, YT), (-2.4, YT + 0.7), fill='#dddddd'))
txt((-3.5, YT + 0.2), 'USB-C', fontsize=9)
txt((-3.5, YT + 1.75), 'ESP32-C3 SuperMini (HW-466B)\nwidok z góry (strona elementów), USB-C u góry', fontsize=11)

ESP = {}
for i, (ln, rn) in enumerate(zip(LEFT, RIGHT)):
    y = YP0 - i * PP
    for name, side in ((ln, 'L'), (rn, 'R')):
        used = name in USED
        x0 = XEL if side == 'L' else XE
        sgn = -1 if side == 'L' else 1
        ESP[name] = (x0 + sgn * STUB, y)
        if used:
            wire((x0, y), (x0 + sgn * STUB, y))
            label, fs, col = USED[name], 10, 'black'
        else:
            note = NC_NOTE.get(name)
            label = f'{name} NC' + (f' ({note})' if note else '')
            fs, col = 8, 'gray'
        if side == 'L':
            txt((x0 + 0.2, y), label, fontsize=fs, color=col, halign='left')
            pinno((x0, y), f'L{i + 1}', dx=-0.1, dy=0.28, halign='right')
        else:
            txt((x0 - 0.2, y), label, fontsize=fs, color=col, halign='right')
            pinno((x0, y), f'R{i + 1}', dx=0.1, dy=0.28, halign='left')

# zasilanie: R1 5V -> X2.1, R2 GND -> X2.2 + masa, R3 3V3 -> szyna 3V3
p5, pg, p3 = ESP['5V'], ESP['GND'], ESP['3V3']
wire(p5, (p5[0] + 0.6, p5[1]))
dot((p5[0] + 0.6, p5[1]), open=True)
txt((p5[0] + 0.8, p5[1]), 'X2.1 +5V   X2: XY308-2P r. 2,54', fontsize=9, halign='left')
wire(pg, (pg[0] + 1.6, pg[1]))
dot((pg[0] + 0.5, pg[1]))
gnd((pg[0] + 0.5, pg[1]))
dot((pg[0] + 1.6, pg[1]), open=True)
txt((pg[0] + 1.8, pg[1]), 'X2.2 GND (X2 = zasilanie, opc.)', fontsize=9, halign='left')
wire(p3, (p3[0] + 0.6, p3[1]))
txt((p3[0] + 0.7, p3[1]), '→ 3V3', fontsize=10, halign='left')

# =====================================================================
# Detekcja dzwonka: GPIO3 (R5) -> kolektor U1
# =====================================================================
XA, XB3 = 2.4, 3.6           # pionowe odcinki: GPIO4 (XA), GPIO3 (XB3)
g3 = ESP['GPIO3']
wire(g3, (XB3, g3[1]), (XB3, Y_RING), (7, Y_RING))
dot((7, Y_RING))
d.add(elm.Resistor().at((7, Y_RING)).up().length(2).label('R3\n10k\n(opc.)', loc='bottom', fontsize=11))
d.add(elm.Vdd().label('3V3', fontsize=10))
wire((7, Y_RING), (10, Y_RING))
dot((10, Y_RING))
d.add(elm.Capacitor(polar=True).at((10, Y_RING)).down().length(2).label('C1 10µF/25V\nECEA1EKS100', loc='bottom', fontsize=10))
gnd((10, Y_RING - 2))

u1 = d.add(elm.Optocoupler().right().at((XI - 0.75, Y_RING + 0.05)).reverse())
txt((XI, Y_RING + 1.4), 'U1 LTV-814 (DIP4, wejście AC)', fontsize=12)
wire((10, Y_RING), u1.collector)
wire(u1.emitter, (u1.emitter[0] - 1.5, u1.emitter[1]))
gnd((u1.emitter[0] - 1.5, u1.emitter[1]))
pinno(u1.collector, '4 (C)', dx=-0.15, halign='right')
pinno(u1.emitter, '3 (E)', dx=-0.15, halign='right')
pinno(u1.anode, '1', dx=0.45, halign='left')
pinno(u1.cathode, '2', dx=0.45, halign='left')
# strona linii: pin1 -> R1 -> R2 -> L1, pin2 -> L2
wire(u1.anode, (29, u1.anode[1]))
d.add(elm.Resistor().at((29, u1.anode[1])).right().label('R1 4k7 0,25W', fontsize=11))
d.add(elm.Resistor().right().label('R2 4k7 0,25W', fontsize=11))
wire((35, u1.anode[1]), (XL1, u1.anode[1]))
dot((XL1, u1.anode[1]))
wire(u1.cathode, (XL2, u1.cathode[1]))
dot((XL2, u1.cathode[1]))

# =====================================================================
# Off-hook: GPIO4 (R4) -> R4 330R -> K1 (AQY212GH)
# =====================================================================
k1 = d.add(elm.Ic(pins=[elm.IcPin(name='K', pin='2', side='left', anchorname='k'),
                        elm.IcPin(name='A', pin='1', side='left', anchorname='a'),
                        elm.IcPin(pin='3', side='right', anchorname='o3'),
                        elm.IcPin(pin='4', side='right', anchorname='o4')],
                  size=(2, 2), pinspacing=1).right().at((XI - 1, Y_HOOK - 1.5)))
txt((XI, Y_HOOK + 1.1), 'K1 AQY212GH (PhotoMOS 60V, DIP4)', fontsize=12)
g4 = ESP['GPIO4']
# GPIO4 lezy na plytce NAD GPIO3, a tor off-hook jest POD torem dzwonka -> jedno skrzyzowanie bez polaczenia
wire(g4, (XA, g4[1]), (XA, Y_HOOK), (6, Y_HOOK))
d.add(elm.Resistor().at((6, Y_HOOK)).right().label('R4 330R', fontsize=11))
wire((9, Y_HOOK), k1.a)
wire(k1.k, (k1.k[0] - 1.5, k1.k[1]))
gnd((k1.k[0] - 1.5, k1.k[1]))
# wyjscie: pin4 -> L1, pin3 -> wezel H -> R5 -> L2
wire(k1.o4, (XL1, k1.o4[1]))
dot((XL1, k1.o4[1]))
XH = 31
wire(k1.o3, (XH, k1.o3[1]))
dot((XH, k1.o3[1]))
d.add(elm.Resistor().at((XH, k1.o3[1])).right().label('R5 330R 1W\nMBE0414', fontsize=10, loc='bottom'))
wire((XH + 3, k1.o3[1]), (XL2, k1.o3[1]))
dot((XL2, k1.o3[1]))
txt((XH - 0.4, k1.o3[1] + 0.45), 'H')

# =====================================================================
# Nadawanie DTMF: GPIO5 (L1) 697 Hz, GPIO6 (L2) 1209 Hz - wyprowadzone z lewej strony plytki
# =====================================================================
g5, g6 = ESP['GPIO5'], ESP['GPIO6']
XR5, XR6 = XEL - 2.2, XEL - 1.4      # trasy pionowe (zewnetrzna dla L1, wewnetrzna dla L2)
wire(g5, (XR5, g5[1]), (XR5, Y_TX2), (4.6, Y_TX2))
wire(g6, (XR6, g6[1]), (XR6, Y_TX), (4.6, Y_TX))
d.add(elm.Resistor().at((4.6, Y_TX)).to((7.6, Y_TX)).label('R8b 330R', fontsize=11))
d.add(elm.Resistor().at((4.6, Y_TX2)).to((7.6, Y_TX2)).label('R8a 330R', fontsize=11, loc='bottom'))
wire((7.6, Y_TX), (8.5, Y_TX))
wire((7.6, Y_TX2), (8.5, Y_TX2), (8.5, Y_TX))
dot((8.5, Y_TX))
txt((8.5, Y_TX + 0.4), 'A')
d.add(elm.Resistor().at((8.5, Y_TX)).right().label('R6a 100R', fontsize=11))
dot((11.5, Y_TX))
d.add(elm.Capacitor().at((11.5, Y_TX)).down().length(2).label('C2 220nF\nfolia r.5,08', loc='bottom', fontsize=10))
gnd((11.5, Y_TX - 2))
d.add(elm.Resistor().at((11.5, Y_TX)).right().label('R6b 100R', fontsize=11))
dot((14.5, Y_TX))
d.add(elm.Capacitor().at((14.5, Y_TX)).down().length(2).label('C3 220nF\nfolia r.5,08', loc='bottom', fontsize=10))
gnd((14.5, Y_TX - 2))
d.add(elm.Capacitor().at((14.5, Y_TX)).right().label('C4 10µF/16V NP\nECEA1CN100U', fontsize=10))
# R7 trymer jako potencjometr-reostat: 1 = wejscie, 2 (suwak) zwarty z 3 = wyjscie
r7 = d.add(elm.Potentiometer().at((17.5, Y_TX)).right())
txt((18.6, Y_TX - 0.9), 'R7 CA9V 4k7 trymer (poziom)', fontsize=11)
wire(r7.tap, (r7.tap[0], Y_TX + 1.1), (20.5, Y_TX + 1.1), (20.5, Y_TX))
dot((20.5, Y_TX))
pinno(r7.start, '1', dx=0.25, dy=0.25)
pinno((r7.tap[0], Y_TX + 1.1), '2', dx=-0.25, dy=0.05, halign='right')
pinno(r7.end, '3', dx=-0.3, dy=0.3)

t1 = d.add(elm.Transformer(t1=4, t2=4, core=True).right().at((XI - 0.5, Y_TX - 1.6)))
wire((20.5, Y_TX), t1.p1)
txt((XI + 3.4, Y_TX - 2.6), 'T1 600:600 (1:1) Bourns LM-NP-1001-B1L\nuzw. A: piny 1–4 | uzw. B: piny 5–8', fontsize=11)
wire(t1.p2, (t1.p2[0] - 1.5, t1.p2[1]))
gnd((t1.p2[0] - 1.5, t1.p2[1]))
pinno(t1.p1, '1', dx=-0.2, halign='right')
pinno(t1.p2, '4', dx=-0.2, halign='right')
pinno(t1.s1, '5', dx=0.2, halign='left')
pinno(t1.s2, '8', dx=0.2, halign='left')
# wtorne: pin5 -> wezel H (rownolegle do R5), pin8 -> C5 -> L2
wire(t1.s1, (XH, t1.s1[1]), (XH, k1.o3[1]))
wire(t1.s2, (33, t1.s2[1]))
d.add(elm.Capacitor().at((33, t1.s2[1])).right().label('C5 1µF folia r.5,08\n(≥100 V, lepiej 250 V)', fontsize=10))
wire((36, t1.s2[1]), (XL2, t1.s2[1]))
dot((XL2, t1.s2[1]))

# =====================================================================
# Odbior DTMF: wezel D (R7 pin3 / T1 pin1) -> C6 -> R9 -> GPIO1 (R7 na plytce, ADC1_CH1)
# =====================================================================
XT = 22.5
dot((XT, Y_TX))
txt((XT - 0.45, Y_TX + 0.4), 'D')
wire((XT, Y_TX), (XT, Y_RX))
d.add(elm.Capacitor().at((XT, Y_RX)).left().length(3).label('C6 220nF folia r.5,08', fontsize=10))
d.add(elm.Resistor().at((XT - 3, Y_RX)).left().length(3).label('R9 2k2', fontsize=11))
g1 = ESP['GPIO1']
XG1 = 1.2
wire(g1, (XG1, g1[1]), (XG1, Y_RX), (XT - 6, Y_RX))
XB = 15.5  # wezel polaryzacji (VADC ~1,65 V)
dot((XB, Y_RX))
d.add(elm.Resistor().at((XB, Y_RX)).up().length(2.2).label('R10\n4k7', loc='bottom', fontsize=11))
d.add(elm.Vdd().label('3V3', fontsize=10))
d.add(elm.Resistor().at((XB, Y_RX)).down().length(2.2).label('R11\n4k7', loc='bottom', fontsize=11))
gnd((XB, Y_RX - 2.2))
XD = 12
dot((XD, Y_RX))
d.add(elm.Schottky().at((XD, Y_RX)).up().length(2.2).label('D4\nBAT85S', loc='bottom', fontsize=11))
d.add(elm.Vdd().label('3V3', fontsize=10))
d.add(elm.Schottky().at((XD, Y_RX - 2.2)).up().length(2.2).label('D5\nBAT85S', loc='bottom', fontsize=11))
gnd((XD, Y_RX - 2.2))
XC = 8.5
dot((XC, Y_RX))
d.add(elm.Capacitor().at((XC, Y_RX)).down().length(2.2).label('C7 33nF\nfolia\nr.5,08', loc='bottom', fontsize=10))
gnd((XC, Y_RX - 2.2))

# =====================================================================
# Szyny linii, transil, X1
# =====================================================================
YTOP = 13.5
wire((XL1, YTOP), (XL1, k1.o4[1]))
wire((XL2, YTOP), (XL2, t1.s2[1]))
dot((XL1, YTOP), open=True)
dot((XL2, YTOP), open=True)
pinno((XL1, YTOP), '1', dx=-0.3, dy=0.05, halign='right')
pinno((XL2, YTOP), '2', dx=0.3, dy=0.05, halign='left')
txt((XL1, YTOP + 0.5), 'L1', fontsize=12)
txt((XL2, YTOP + 0.5), 'L2', fontsize=12)
txt((44, YTOP + 1.6), 'X1 XY308-2P (r. 2,54 mm)\nLINIA DOMOFONU (2 żyły)', fontsize=11)
dot((XL1, 11.5)); dot((XL2, 11.5))
d.add(elm.DiodeTVS().at((XL1, 11.5)).to((XL2, 11.5)).label('D2 P6KE36CA', fontsize=11, loc='bottom'))


# =====================================================================
# J1 MTJ-642BX2 (Adam Tech, RJ11 6P4C, 1 port, THT katowe) - dodatkowy telefon rownolegle do linii
# piny PCB 1-4 = styki 6P nr 2-5; srodkowa para (6P: 3/4) = piny 2 i 3 -> L1 / L2
# =====================================================================
YJ = -9.0                       # gorna krawedz J1
wire((XL1, k1.o4[1]), (XL1, YJ))
wire((XL2, t1.s2[1]), (XL2, YJ))
XJ = {'1': 40.3, '2': XL1, '3': XL2, '4': 47.7}
wire((39.3, YJ - 0.6), (48.7, YJ - 0.6), (48.7, YJ - 2.6), (39.3, YJ - 2.6), (39.3, YJ - 0.6))
for pn, xj in XJ.items():
    wire((xj, YJ), (xj, YJ - 0.6))
    pinno((xj, YJ), pn, dx=0.2, dy=-0.05, halign='left')
for xj in (XJ['1'], XJ['4']):
    txt((xj, YJ + 0.35), 'NC', fontsize=8, color='gray')
txt((44, YJ - 1.25), 'J1 MTJ-642BX2 (RJ11 6P4C, 1 port, THT)', fontsize=10)
txt((44, YJ - 2.0), 'styki wtyku 6P: 2 3 4 5 = piny 1 2 3 4', fontsize=9, color='gray')
txt((44, YJ - 3.1), 'DODATKOWY TELEFON (równolegle do X1)', fontsize=10)
# =====================================================================
# Bariera izolacji i opisy
# =====================================================================
wire((XI, 16.3), (XI, -11.0), ls='--', color='gray')
txt((XI - 0.3, -11.0), 'strona ESP (GND ESP)', halign='right', color='gray')
txt((XI + 0.3, -11.0), 'strona linii (izolowana)', halign='left', color='gray')
txt((XI, 16.8), 'BARIERA IZOLACJI: U1 / K1 / T1', fontsize=12, color='gray')

txt((21, -13.2),
    'HW-466B: widok z góry (strona elementów), USB-C u góry; L1–L8 = lewy rząd, R1–R8 = prawy rząd, liczone od USB-C. '
    'Pinouty z „5V/G/3.3” po LEWEJ pokazują spód płytki.\n'
    'Numery pinów: czerwone. U1/K1 – karty Liteon/Panasonic; T1 – karta Bourns (widok od spodu, uzw. 1–4 i 5–8, identyczne) – potwierdź omomierzem (~66 Ω).',
    fontsize=10, color='#205080')
txt((21, -14.6),
    'Tor odbioru DTMF: D (R7.3 / T1.1) → C6 → R9 → GPIO1; polaryzacja 1,65 V (R10/R11), filtr R9‖R10‖R11 + C7 (fc ≈ 4,2 kHz), ograniczenie D4/D5. '
    'Masa ESP NIE jest połączona z linią. LTV-814 ma diody antyrównoległe (AC/DC).\n'
    'J1: piny 2/3 (środkowa para wtyku RJ11) = L1/L2, równolegle do X1 i D2. Gdy dodatkowy telefon podniesie słuchawkę, obciąża linię (spada napięcie, tony DTMF słabsze). '
    'Skrzyżowania bez kropki = brak połączenia.',
    fontsize=10, color='#205080')

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    d.save(os.path.join(here, 'schematic.svg'))
    d.save(os.path.join(here, 'schematic.png'), dpi=200)
    print('OK: schematic.svg, schematic.png')

# --- wymuszenie bialego tla (PNG i SVG) ---
def _white_bg(here):
    from PIL import Image
    p = os.path.join(here, 'schematic.png')
    im = Image.open(p).convert('RGBA')
    bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    bg.convert('RGB').save(p)
    s = os.path.join(here, 'schematic.svg')
    txt = open(s, encoding='utf-8').read()
    if 'id="white-bg"' not in txt:
        import re
        txt = re.sub(r'(<svg[^>]*>)', r'\1<rect id="white-bg" width="100%" height="100%" fill="white"/>', txt, count=1)
        open(s, 'w', encoding='utf-8').write(txt)

if __name__ == '__main__':
    _white_bg(os.path.dirname(os.path.abspath(__file__)))
