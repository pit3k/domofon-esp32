# Design notes (English summary)

Full, detailed notes in Polish: [design-notes-pl.md](design-notes-pl.md) (netlist, pin numbers, part rationale, ESPHome details).

## Assumptions — MEASURE before connecting
- 2-wire analog intercom handset: idle 12–24 V DC, ring AC/pulses 12–40 V, off-hook the line is loaded with ~200–600 Ω (drops to ~6–12 V).
- Opening with DTMF "1" works only if the intercom exchange accepts tone opening.

## Blocks
| Block | Parts | ESP pin |
|---|---|---|
| Ring detection | C8 0.47 µF/250 V MKT + R1 4k7 → U1 LTV-814 (AC-input optocoupler) → GPIO3 with pull-up R3 and filter C1 10 µF | GPIO3 (HW-466B R5) |
| Off-hook | K1 AQY214EH PhotoMOS (400 V) (LED via R4 330 Ω) switches R5 330 Ω 1 W load + T1 line winding onto the line | GPIO4 (R4) |
| DTMF transmit | sine PWM (`dtmf_tone`, carrier 200 kHz) low group on GPIO5, high group on GPIO6 → R8a/R8b 330 Ω summing (node A) → 2nd-order RC low-pass R6a/C2, R6b/C3 (100 Ω / 220 nF, ~55 dB at 200 kHz) → C4 → level trimmer R7 → T1 (600:600; line winding: pin 8 → H, pin 5 → C5) → C5 1 µF/100 V → line | GPIO5 (L1), GPIO6 (L2) |
| DTMF receive | T1 → C6 220 nF → R9 2k2 → GPIO1 (ADC1), bias 1.65 V by R10/R11, anti-alias C7 33 nF, clamp D4/D5 BAT85; software Goertzel decoder ([pit3k/esphome-dtmf-decoder](https://github.com/pit3k/esphome-dtmf-decoder)) | GPIO1 (R7) |
| Protection | D2 P6KE220CA bidirectional TVS across L1/L2 | – |
| Extra handset | J1 RJ11 (pins 2/3 = L1/L2) in parallel with X1 | – |

## Line voltages and line-side parts (revision 5)
- Measured: **42 V DC** idle. ETSI ES 201 970 / TBR21: ringing up to **100 Vrms** at 25 Hz (crest 1.2–1.6) superimposed on DC (TBR21 test: 90 Vrms on 60 V DC) → peaks ≈ 220–240 V. On-hook the device **must not draw DC** (TBR21: < 0.6 mA during ringing).
- Rev. 4 bug: D2 P6KE36CA conducted at 42 V and R1+R2 (2×4k7)+U1 drew ~4.4 mA DC → the exchange saw the line off-hook.
- **D2 → P6KE220CA** (same DO-15 footprint): VRWM ≈ 185 V, VBR 209–231 V – silent at 42 V DC and normal ringing, clamps surges.
- **Former R2 4k7 → C8 0.47 µF / 250 V (400 V better) MKT.** PCB footprint `CFILM_P7.62` keeps the exact R2 pads/holes (7.62 mm) – copper, drills and G-code unchanged; only silkscreen/Fab text changed. DC is blocked: idle current = 0.
- **K1 → AQY214EH** (400 V / 120 mA, DIP4, same pinout). **C5 → 1 µF / 100 V MKT** (WIMA MKS2, 5 mm pitch, 7.2×7.2×13 mm); same capacitance → DTMF TX unchanged.
- Ring current (C8 + R1 4k7, Xc = 13.55 kΩ, |Z| = 14.34 kΩ): 35 Vrms → 2.44 mA rms (3.45 mA pk); 100 Vrms → 6.97 mA, P(R1) = 0.228 W → R1 4k7 0.25 W kept. LTV-814 CTR ≥ 20 % → ≥ 0.69 mA collector at 35 Vrms, enough for the 10k pull-up; C1 holds GPIO3 low between half-cycles.

Galvanic isolation: ESP ground is **never** connected to the line. On the PCB, line side and ESP side are
separated by a 4 mm copper-free strip with a milled 2 mm slot under U1/K1; T1 bridges the barrier
(measured minimum copper distance 5.23 mm).

## ESP32-C3 SuperMini (HW-466B) pinout used
Top view (component side), USB-C at the top:
- Left row L1..L8: GPIO5, GPIO6, GPIO7, GPIO8, GPIO9, GPIO10, GPIO20, GPIO21
- Right row R1..R8: 5V, GND, 3V3, GPIO4, GPIO3, GPIO2, GPIO1, GPIO0

Clones differ — verify against the silkscreen of your board before soldering.
