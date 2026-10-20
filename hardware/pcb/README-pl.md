# Domofon – PCB jednostronna (THT), do frezowania V-frezem 30°/0,2 mm

- Płytka: 55,5 x 45,9 mm (zaokrąglone narożniki R1), miedź tylko B.Cu, elementy od góry.
- Rew. 5: C8 (0,47 µF/250 V MKT, footprint CFILM_P7.62) zajmuje dokładnie pady/otwory dawnego R2 – miedź, otwory i G-code bez zmian; zmienione tylko opisy (silkscreen/Fab: C8, AQY214EH, P6KE220CA, 1u/100V).
- Zworki: 1 (JP1, GND, drut izolowany od strony elementów, rozstaw 17,78 mm, wzdłuż lewej krawędzi C1).
  W KiCad zworka jest narysowana jako ścieżka na F.Cu tylko po to, żeby DRC widział połączenie –
  warstwy F.Cu NIE frezować (gerbers/domofon-F_Cu-jumpers_DO_NOT_MILL.gtl).
- DRC (kicad-cli 9.0.2, wszystkie poziomy ważności, reguły z domofon.kicad_dru): 0 naruszeń, 0 niepodłączonych.
- Ścieżki: sygnałowe 0,6 mm; zasilanie (GND/+3V3/+5V) i linia domofonu 1,0 mm. Clearance min 0,4 (zmierzone min. 0,43 mm, GND–N_C6).
- Izolacja galwaniczna: reguła 4,0 mm linia <-> strona ESP; zmierzona min. odległość miedzi 5,23 mm; szczelina 2 mm pod U1/K1.
- Otwory: 0,8 (46), 1,0 (28), 1,2 (11) PTH; NPTH 1,0 (2, nieużywane piny J1) i 2,4 (2, kołki J1).
- Elementy pod ESP (R8a/R8b/R6a/D4/R10/R3/R9/D5/R11) wymagają osadzenia ESP32-C3 SuperMini na gniazdach goldpin (~8-11 mm).

Pliki: domofon.kicad_pcb/.kicad_pro/.kicad_dru, drc-report.txt, gerbers/ (B.Cu, Edge.Cuts ze szczeliną, F.Silkscreen, F.Fab, PTH/NPTH Excellon mm + mapy),
previews/ (bottom_copper_mirrored_for_milling.png – widok od spodu/lustro, top_placement.png, top_with_traces.png).
Skrypty generujące (scripts/): footprints.py, netlist.py, placement.py, build.py, route.py (Freerouting 2.5), mkproject.py, build_and_route.sh, drc.sh, export_gerbers.sh, make_previews.sh, preview.sh, check_track_widths.py.
