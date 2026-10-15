# Design notes (English summary)

Full, detailed notes in Polish: [design-notes-pl.md](design-notes-pl.md) (netlist, pin numbers, part rationale, ESPHome details).

## Assumptions — MEASURE before connecting
- 2-wire analog intercom handset: idle 12–24 V DC, ring AC/pulses 12–40 V, off-hook the line is loaded with ~200–600 Ω (drops to ~6–12 V).
- Opening with DTMF "1" works only if the intercom exchange accepts tone opening.

## Blocks
| Block | Parts | ESP pin |
|---|---|---|
| Ring detection | R1+R2 (4k7+4k7) → U1 LTV-814 (AC-input optocoupler) → GPIO3 with pull-up R3 and filter C1 10 µF | GPIO3 (HW-466B R5) |
| Off-hook | K1 AQY212GH PhotoMOS (LED via R4 330 Ω) switches R5 330 Ω 1 W load + T1 line winding onto the line | GPIO4 (R4) |
| DTMF transmit | two LEDC PWM tones (low group on GPIO5, high group on GPIO6) → R8a/R8b summing (node A) → 2nd-order RC low-pass R6a/C2, R6b/C3 (~3.4 kHz) → C4 → level trimmer R7 → T1 (600:600) → C5 → line | GPIO5 (L1), GPIO6 (L2) |
| DTMF receive | T1 → C6 220 nF → R9 2k2 → GPIO1 (ADC1), bias 1.65 V by R10/R11, anti-alias C7 33 nF, clamp D4/D5 BAT85; software Goertzel decoder | GPIO1 (R7) |
| Protection | D2 P6KE36CA bidirectional TVS across L1/L2 | – |
| Extra handset | J1 RJ11 (pins 2/3 = L1/L2) in parallel with X1 | – |

Galvanic isolation: ESP ground is **never** connected to the line. On the PCB, line side and ESP side are
separated by a 4 mm copper-free strip with a milled 2 mm slot under U1/K1; T1 bridges the barrier
(measured minimum copper distance 5.23 mm).

## ESP32-C3 SuperMini (HW-466B) pinout used
Top view (component side), USB-C at the top:
- Left row L1..L8: GPIO5, GPIO6, GPIO7, GPIO8, GPIO9, GPIO10, GPIO20, GPIO21
- Right row R1..R8: 5V, GND, 3V3, GPIO4, GPIO3, GPIO2, GPIO1, GPIO0

Clones differ — verify against the silkscreen of your board before soldering.
