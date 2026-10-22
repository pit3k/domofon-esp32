# 3D-printed enclosure — domofon-esp32 (layout v7)

Flat, square wall box made of two printed parts: a **base** glued to the wall and a **lid** held by 3 countersunk M3 screws in brass heat-set inserts.
The design is parametric (CadQuery). All dimensions are in `source/enclosure.py`, in the `P` dict at the top of the file.

| | |
|---|---|
| Outer size | **68 × 68 × 26 mm** (W × H × depth from the wall) |
| Walls / back / lid | 2.0 / 2.0 / 3.0 mm, top wall 1.39 mm |
| PCB | 55.5 × 45.9 mm, **flipped: components face the wall**, solder side faces the lid |
| Orientation (looking toward the wall) | **RJ11 (J1) exits through the left wall**, **USB-C points up** |
| USB-C | socket axis **5.0 mm from the wall**. The mouth sits 2.38 mm below the top surface. The overmold sits in a **13 × 8 mm pocket** (R2, 1.98 mm deep), with a **9.25 × 3.4 mm obround** opening (R1.7) in the pocket floor. The plug goes **6.2 mm** into the socket |
| Phone cable from the wall | Ø12 hole in the back plate, centre **16 mm from the left edge, 10.5 mm from the bottom edge** (seen from the room). It sits in the strip under the PCB |
| Screws | 3 × M3×10 countersunk (ISO 10642 / DIN 7991) + 3 × brass M3 heat-set inserts Ø4 × 4 mm, posts Ø7.5 at (6;6), (62;6), (62;62) |
| PCB fixing | the board rests on 4 round supports from the back plate plus 4 edge ledges. It is held sideways by the top/left walls and 4 guide ribs. 4 pins on the lid press the solder side. Supports and pins are coaxial and avoid all component bodies and pads |

![inside](previews/assembly_inside_no_lid.png)

## Folder layout
```
hardware/enclosure/
├── source/
│   ├── enclosure.py                 # CadQuery model + interference check + exports
│   ├── render_previews.py           # PNG previews (pyvista, white background)
│   ├── export_board_components.py   # PCB → board_components.json (system python + KiCad pcbnew)
│   └── board_components.json        # component bodies / positions exported from the PCB
├── stl/    enclosure_base.stl, enclosure_lid.stl          (already in print orientation)
├── 3mf/    enclosure_base.3mf, enclosure_lid.3mf, enclosure_plate_base_and_lid.3mf
├── step/   enclosure_base.step, enclosure_lid.step, enclosure_assembly_with_pcb.step
└── previews/  assembly_front.png, assembly_inside_no_lid.png, base_only.png, exploded.png,
               top_view_usb_pocket.png, back_view_wall_hole.png, front_view.png
```

Regenerate:
```bash
python3 hardware/enclosure/source/export_board_components.py      # only if the PCB changed (needs KiCad 9)
python3 -m venv .venv-cad && .venv-cad/bin/pip install cadquery trimesh networkx lxml pyvista
.venv-cad/bin/python hardware/enclosure/source/enclosure.py        # prints the interference report
.venv-cad/bin/python hardware/enclosure/source/render_previews.py
```

## Coordinates
- **Frame:** looking toward the wall. X points right, Y up, Z out of the wall. The origin is the outer lower-left corner.
- **PCB position:** X 2.30–57.80, Y 20.41–66.31. Component face at Z = 18.6, solder face at Z = 20.1.
- **USB-C axis:** X = 46.1, Z = 5.0.
- **RJ11 slot:** centre Y = 58.3, width 12.8, Z from 3.6 up to the lid.
- **Wall-cable hole:** (16; 10.5) as seen from the room. Seen from the wall side it is mirrored, at 52 mm from that side's left edge.

---

## Instrukcja (PL)

### Druk (Bambu Lab P2S, Bambu Studio)
- Pliki `3mf/`: `enclosure_plate_base_and_lid.3mf` (obie części na jednym stole) albo osobno.
- Orientacja jest już ustawiona:
  - **baza** leży tylną ścianką (stroną przyklejaną do ściany) na stole;
  - **pokrywa** leży frontem na stole, a kołki i krawędź centrująca są skierowane do góry. Stożki pod łby śrub rozszerzają się w stronę stołu, co daje nawis 45° – drukuje się bez podpór.
- **Podpory: wyłączone.** Kieszeń USB, owalny otwór i szczelina RJ11 drukują się jako krótkie mostki.
- Materiał:
  - **PETG** – lepszy przy ciepłej ścianie;
  - **PLA** – wystarczy w mieszkaniu.
- Ustawienia: warstwa 0,2 mm, 3–4 obrysy (słupki pod wtopki muszą mieć pełne ścianki), wypełnienie 20 % gyroid.

### Do kupienia
- **3 × śruba M3×10 z łbem stożkowym** (ISO 10642 / DIN 7991, imbus).
- **3 × wkładka mosiężna M3 do wtapiania, Ø4 × 4 mm** (otwór w słupku Ø4,0, głębokość 10 mm).
- Taśma dwustronna montażowa (np. 3M VHB): paski na tylnej ściance, omijając otwór na kabel.

### Wtapianie wkładek
1. Lutownica 220–230 °C (PLA) lub 245–260 °C (PETG), najlepiej z końcówką do wtopek.
2. Postaw wkładkę prosto na otworze słupka i wciśnij ją bez nacisku bocznego, aż będzie równo z górą słupka (lub 0,2 mm niżej).
3. Od razu dociśnij płaskim przedmiotem, żeby się nie przekrzywiła. Odczekaj, aż ostygnie.
- Śruba M3×10 przechodzi przez 3 mm pokrywy, potem przez 4 mm wkładki i jeszcze 3 mm w otwór pod nią.

### Składanie
1. **Trymer R7 ustaw przed montażem.** Po zamknięciu jest od strony ściany i nie ma do niego dostępu.
2. Przeciągnij kabel ze ściany przez otwór Ø12 i przyklej bazę do ściany. Otwór jest w lewym dolnym rogu (patrząc na ścianę).
3. Żyły doprowadź do zacisków **X1** wzdłuż lewej strony, pod płytką. Przejście pod C5 ma ok. 3,6 mm wysokości.
4. Włóż płytkę elementami do ściany: J1 w lewo, USB-C do góry. Wsuń ją pod górną ściankę tak, żeby gniazdo USB weszło w owalny otwór. Płytka oprze się na wspornikach i półkach.
5. Załóż pokrywę i przykręć 3 śruby. Kołki pokrywy dociskają płytkę.
6. Wtyk USB-C wkładasz z zewnątrz, od góry. Obudowa wtyku chowa się w kieszeni 13 × 8 mm.
7. Wtyk RJ11 wkładasz z lewej strony, przez szczelinę w lewej ściance.

### Założenia do sprawdzenia
- **Stos ESP32:** listwa 8,5 + dystans pinów 2,5 + PCB 1,0 + USB-C 3,2 mm = 15,2 mm. Jeśli Twój moduł jest inny, zmień `fheader_h` / `mheader_spacer`. Oś USB musi zostać 5,0 mm od ściany – wtedy popraw też `air`.
- **Wtyk USB-C:** metalowa końcówka 6,6 mm przed obudową wtyku (`plug_tip`), obudowa wtyku do 12,5 × 8 mm. Jeśli końcówka jest krótsza, zwiększ głębokość kieszeni (z `insert_need`).
- **Gniazdo USB-C w otworze:** obudowa gniazda 8,94 × 3,2 mm, otwór 9,25 × 3,4 mm (pasowanie ciasne, ok. 0,15 mm na stronę). W razie potrzeby rozwierć otwór pilnikiem.
- **Wysokości elementów** są uproszczone: C5 13 mm, J1 14,5 mm, D2 11,5 mm, C8 11 mm, T1 11 mm, elektrolity 12 mm.
