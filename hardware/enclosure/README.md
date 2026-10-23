# 3D-printed enclosure — domofon-esp32 (layout v9)

Flat wall box made of two printed parts: a **base** glued to the wall and a **lid** held by 4 countersunk M3 screws in brass heat-set inserts.
The design is parametric (CadQuery). All dimensions are in `source/enclosure.py`, in the `P` dict at the top of the file.

| | |
|---|---|
| Outer size | **93 × 68 × 26 mm** (W × H × depth from the wall; widened by +25 mm on the left) |
| Walls / back / lid | 2.0 / 2.0 / 3.0 mm, top wall 1.39 mm |
| PCB | 55.5 × 45.9 mm, **flipped (components face the wall)** and **shifted +25 mm right** (`X = 27.30..82.80 mm`), leaving a **25.3 mm left chamber** |
| Orientation (looking toward the wall) | **RJ11 (J1) plug sits inside the left chamber**, **flat cable exits at the bottom-left**, **USB-C points up** |
| USB-C | socket axis **5.0 mm from the wall**, `X = 71.10 mm`. The mouth sits 2.38 mm below the top surface. The overmold sits in a **13 × 8 mm pocket** (R2, 1.98 mm deep), with a **9.25 × 3.4 mm obround** opening (R1.7) in the pocket floor. The plug goes **6.2 mm** into the socket |
| RJ11 & left-wall cable slot | The RJ11 modular plug connects to `J1` inside the left chamber (`Y = 58.31 mm`). The flat telephone cable exits through a **5.0 × 2.5 mm** channel at the bottom of the left wall (`Y = 11.75..16.75 mm`, `2.0 mm` above the bottom-left post, and `Z = 2.0..4.5 mm` directly on the back floor). A **reinforced 5.0 mm thick plunger on the lid** (`Z = 4.5..23.0 mm`, with a `7.5 × 8.5 mm` 45° gusseted root base and side guide channel `X = 0..5.5 mm`) slides down to pinch the cable and seal the rest of the slot |
| Phone cable from the wall | Ø12 hole in the back plate, centre **(16.0; 15.5) mm** (16.0 mm from the left outer edge, 15.5 mm from the bottom outer edge, inside the left chamber, 5.3 mm clear of the PCB) |
| Screws | 4 × M3×10 countersunk (ISO 10642 / DIN 7991) + 4 × brass M3 heat-set inserts Ø4 × 4 mm, posts Ø7.5 at (6;6), (87;6), (87;62), (6;62) |
| PCB fixing | the board rests on 4 round supports from the back plate plus 6 edge ledges (2 left, 2 right, 2 bottom). It is held sideways by the top wall and 6 guide ribs. 4 pins on the lid press the solder side. Supports and pins are coaxial and avoid all component bodies and pads |

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
- **Frame:** looking toward the wall. X points right, Y up, Z out of the wall. The origin is the outer lower-left corner (`0..93 × 0..68 × 0..26 mm`).
- **PCB position:** X 27.30–82.80, Y 20.41–66.31. Component face at Z = 18.6, solder face at Z = 20.1.
- **USB-C axis:** X = 71.1, Z = 5.0.
- **Left-wall flat cable channel:** Y = 11.75–16.75 (centre Y = 14.25, 5.0 mm high), Z = 2.0–4.5 (2.5 mm deep, right against the 2.0 mm back floor), closed from Z = 4.5 to 23.0 by the lid's 5.0 mm thick plunger (guided in X = 0–5.5 mm, with a 7.5 × 8.5 mm 45° gusseted root).
- **Wall-cable hole:** (16.0; 15.5) as seen from the room (`Ø12 mm`). Seen from the wall side it is mirrored, at 77.0 mm from that side's left edge.

---

## Instrukcja (PL)

### Druk (Bambu Lab P2S, Bambu Studio)
- Pliki `3mf/`: `enclosure_plate_base_and_lid.3mf` (obie części na jednym stole) albo osobno.
- Orientacja jest już ustawiona:
  - **baza** leży tylną ścianką (stroną przyklejaną do ściany) na stole;
  - **pokrywa** leży frontem na stole, a kołki, krawędź centrująca oraz pogrubiony trzpień dociskający kabel (z fazowaną bazą 45°) są skierowane do góry. Stożki pod łby śrub i fazy u nasady trzpienia rozszerzają się w stronę stołu (45°) – całość drukuje się **bez podpór**.
- **Podpory: wyłączone.** Kieszeń USB, owalny otwór i kanał kabla drukują się bez wiszących nawisów.
- Materiał:
  - **PETG** – lepszy przy ciepłej ścianie;
  - **PLA** – wystarczy w mieszkaniu.
- Ustawienia: warstwa 0,2 mm, 3–4 obrysy (słupki pod wtopki i trzpień dociskowy mają wtedy bardzo mocne ścianki), wypełnienie 20 % gyroid.

### Do kupienia
- **4 × śruba M3×10 z łbem stożkowym** (ISO 10642 / DIN 7991, imbus).
- **4 × wkładka mosiężna M3 do wtapiania, Ø4 × 4 mm** (otwór w słupku Ø4,0, głębokość 10 mm).
- Taśma dwustronna montażowa (np. 3M VHB): paski na tylnej ściance, omijając otwór na kabel.

### Wtapianie wkładek
1. Lutownica 220–230 °C (PLA) lub 245–260 °C (PETG), najlepiej z końcówką do wtopek.
2. Postaw wkładkę prosto na otworze słupka i wciśnij ją bez nacisku bocznego, aż będzie równo z górą słupka (lub 0,2 mm niżej).
3. Od razu dociśnij płaskim przedmiotem, żeby się nie przekrzywiła. Odczekaj, aż ostygnie.
- Śruba M3×10 przechodzi przez 3 mm pokrywy, potem przez 4 mm wkładki i jeszcze 3 mm w otwór pod nią.

### Składanie
1. **Trymer R7 ustaw przed montażem.** Po zamknięciu jest od strony ściany i nie ma do niego dostępu.
2. Przeciągnij kabel ze ściany przez otwór Ø12 `(16,0; 15,5)` w lewej komorze i przyklej bazę do ściany.
3. Podłącz żyły do zacisków **X1** i wsuń płytkę elementami do ściany (J1 w lewo, USB-C do góry) pod górną ściankę tak, żeby gniazdo USB weszło w owalny otwór. Płytka oprze się na wspornikach i 6 prowadnicach bocznych/dolnych.
4. Wepnij wtyk **RJ11** do gniazda **J1** wewnątrz lewej komory, a płaski przewód telefoniczny ułóż na dnie w prowadnicy `5 × 2,5 mm` na dole lewej ścianki (`2 mm` nad dolnym słupkiem).
5. Załóż pokrywę i przykręć 4 śruby. Kołki pokrywy dociskają płytkę, a pogrubiony trzpień pokrywy (`5 mm` grubości z szeroką bazą) wsuwa się w kanał prowadzący, dociska płaski kabel do dna i zaślepia wycięcie z boku.
6. Wtyk USB-C wkładasz z zewnątrz, od góry. Obudowa wtyku chowa się w kieszeni 13 × 8 mm.

### Założenia do sprawdzenia
- **Stos ESP32:** listwa 8,5 + dystans pinów 2,5 + PCB 1,0 + USB-C 3,2 mm = 15,2 mm. Jeśli Twój moduł jest inny, zmień `fheader_h` / `mheader_spacer`. Oś USB musi zostać 5,0 mm od ściany – wtedy popraw też `air`.
- **Wtyk USB-C:** metalowa końcówka 6,6 mm przed obudową wtyku (`plug_tip`), obudowa wtyku do 12,5 × 8 mm. Jeśli końcówka jest krótsza, zwiększ głębokość kieszeni (z `insert_need`).
- **Gniazdo USB-C w otworze:** obudowa gniazda 8,94 × 3,2 mm, otwór 9,25 × 3,4 mm (pasowanie ciasne, ok. 0,15 mm na stronę). W razie potrzeby rozwierć otwór pilnikiem.
- **Wysokości elementów** są uproszczone: C5 13 mm, J1 14,5 mm, D2 11,5 mm, C8 11 mm, T1 11 mm, elektrolity 12 mm.
