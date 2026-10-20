# Interfejs domofonu analogowego -> ESP32-C3 / ESPHome (wersja 5 – strona linii pod ES 201 970: D2 P6KE220CA, C8 zamiast R2, K1 AQY214EH, C5 100 V)

MCU: **ESP32-C3 SuperMini (HW-466B)**, ESPHome board `esp32-c3-devkitm-1`.
Schemat graficzny: [`hardware/schematic/schematic.svg`](../hardware/schematic/schematic.svg) / `schematic.png` (generowany z `hardware/schematic/schematic.py`).
Na schemacie: symbol HW-466B z fizycznym układem pinów (L1–L8 / R1–R8, widok z góry, USB-C u góry) oraz numery pinów U1, K1, T1, R7, X1, X2, J1 (kolor czerwony). Lista części: [`hardware/bom/bom.csv`](../hardware/bom/bom.csv).

Generowanie obrazka:
```bash
cd hardware/schematic
python3 -m venv .venv && .venv/bin/pip install schemdraw pillow   # jednorazowo
.venv/bin/python schematic.py                                    # -> schematic.svg + schematic.png
```

## Założenia (ZMIERZ przed podłączeniem!)
- Słuchawka 2-przewodowa: spoczynek 12–24 V DC, dzwonek AC/impulsy 12–40 V, po podniesieniu linia obciążona ~200–600 Ω (spadek do ~6–12 V).
- DTMF „1” działa tylko, jeśli centrala akceptuje tonowe otwieranie. W systemach z osobną żyłą otwierania wystarczy zwarcie przycisku drugim PhotoMOS-em.

## ESP32-C3 SuperMini (HW-466B) – fizyczne położenie pinów
Konwencja: **widok z góry = strona elementów** (układ ESP32-C3, przyciski BOOT/RST), **złącze USB-C u góry**.
Lewy rząd **L1…L8**, prawy rząd **R1…R8**, numerowane od strony USB-C w dół (raster 2,54 mm, rozstaw rzędów 15,24 mm).

| Poz. | Lewy rząd | Użycie | Poz. | Prawy rząd | Użycie |
|---|---|---|---|---|---|
| L1 | GPIO5 | **ton DTMF 697 Hz** (R8a) | R1 | 5V | X2.1 (opcjonalne zasilanie 5 V) |
| L2 | GPIO6 | **ton DTMF 1209 Hz** (R8b) | R2 | GND | **masa ESP**, X2.2 |
| L3 | GPIO7 | NC | R3 | 3V3 | **3V3** (R3, R10, D4) |
| L4 | GPIO8 | NC (LED, strapping) | R4 | GPIO4 | **off-hook** → R4 → K1.1 |
| L5 | GPIO9 | NC (BOOT, strapping) | R5 | GPIO3 | **dzwonek** ← U1.4 |
| L6 | GPIO10 | NC | R6 | GPIO2 | NC (strapping) |
| L7 | GPIO20 | NC (UART RX) | R7 | GPIO1 | **odbiór DTMF (ADC1_CH1)** ← R9 |
| L8 | GPIO21 | NC (UART TX) | R8 | GPIO0 | NC |

Źródła pinoutu:
- WMNologo (producent wzorcowej płytki ESP32C3 SuperMini), rysunek wymiarowy strony elementów – 5V/G/3.3 po **prawej**, „21” lewy dolny róg, „0” prawy dolny: https://www.nologo.tech/en/product/esp32/esp32c3SuperMini/esp32C3SuperMini.html (obraz `/assets/img/esp32/esp32c3supermini/dimension.png`); na tej samej stronie diagram pinów (`esp32c3foot1.png`) pokazuje lustrzane odbicie – to widok od spodu/nadruku.
- Apache NuttX, ESP32-C3 SuperMini – kolejność w rzędach od USB-C: „5V G 3.3 4 3 2 1 0” oraz „5 6 7 8 9 10 20 21”: https://nuttx.apache.org/docs/latest/platforms/risc-v/esp32c3/boards/esp32c3-supermini/index.html
- Uwaga: część stron (np. esp32hub.com) podaje 5V/GND/3V3 jako „lewy rząd” – to widok od spodu (strona z nadrukiem). Przed lutowaniem porównaj z nadrukiem na swojej płytce.

| Funkcja | GPIO | Pin płytki | Uwagi |
|---|---|---|---|
| Dzwonek (wejście) | GPIO3 | R5 | INPUT_PULLUP (+ opcj. R3 10k do 3V3), kolektor U1 (pin 4), C1 10µF do GND |
| Off-hook (wyjście) | GPIO4 | R4 | przez R4 330R na diodę K1 (pin 1, ≈5 mA) |
| Ton DTMF 697 Hz | GPIO5 | L1 | sinus PWM (`dtmf_tone`), R8a 330R do węzła A |
| Ton DTMF 1209 Hz | GPIO6 | L2 | sinus PWM (`dtmf_tone`), R8b 330R do węzła A |
| Odbiór DTMF (ADC) | GPIO1 | R7 | ADC1_CH1; dekoder Goertzela w [pit3k/esphome-dtmf-decoder](https://github.com/pit3k/esphome-dtmf-decoder) |
| Zasilanie | 5V / GND / 3V3 | R1 / R2 / R3 | 5V tylko gdy USB-C nie jest podłączone |
Omijamy GPIO2/8/9 (strapping), GPIO18/19 (USB), GPIO20/21 (UART). ADC tylko na ADC1 (GPIO0–4) – ADC2 (GPIO5) koliduje z WiFi.
Na schemacie: GPIO4 (R4) leży na płytce nad GPIO3 (R5), a tor off-hook jest narysowany pod torem dzwonka – stąd jedno skrzyżowanie przewodów **bez kropki = bez połączenia**. GPIO5/GPIO6 (lewy rząd) są poprowadzone wokół symbolu do toru nadawania.

## Numery pinów elementów wielopinowych
| Element | Piny | Źródło |
|---|---|---|
| U1 LTV-814 (DIP4) | 1 = anoda/katoda, 2 = katoda/anoda (diody antyrównoległe), 3 = emiter, 4 = kolektor | karta Liteon LTV-814/824/844, „Pin No. and internal connection diagram” |
| K1 AQY214EH (DIP4) | 1 = anoda LED, 2 = katoda LED, 3 i 4 = wyjście MOSFET (AC/DC, zamienne) | karta Panasonic PhotoMOS AQY21□EH (DIP4 1 Form A) |
| T1 LM-NP-1001-B1L | uzwojenie A: piny **1–4**, uzwojenie B: piny **5–8** (widok od spodu, pin 1 przy białym znaczniku/ściętym rogu; obsadzone tylko 1, 4, 5, 8). Uzwojenia identyczne – dowolne pierwotne/wtórne. Na schemacie: strona ESP 1–4, strona linii 5–8 | karta Bourns LM-NP/-LP 1000 Series, „Pin Assignment and Winding Configurations (Bottom View)” |
| R7 trymer 4k7 | 1 = koniec, 2 = suwak, 3 = koniec; jako reostat: 2 zwarty z 3 | konwencja |
| X1 XY308-2P (Xinya, raster 2,54 mm) | 1 = L1, 2 = L2 | – |
| X2 XY308-2P (opc.) | 1 = +5V (pin R1 płytki), 2 = GND (pin R2) | – |
| J1 MTJ-642BX2 (Adam Tech, RJ11 6P4C, 1 port, kątowe THT) | piny PCB 1–4 = styki wtyku 6P nr 2–5; **2 = L1, 3 = L2** (środkowa para = linia telefoniczna), 1 i 4 NC | karta Adam Tech MTJ-642BX2 rev. C (front: „4 3 2 1”, recommended PCB layout) |

## Części wg zamówienia (TME) i zapasów
Pełna lista: `hardware/bom/bom.csv` (pierwotne zamówienie TME, historia sprzed rew. 5: `hardware/bom/tme-order.csv`). Z TME: U1 LTV-814, K1 AQY214EH, T1 LM-NP-1001-B1L, R5 MBE04140C3300FC100 (330R 1W), D2 P6KE220CA-DIO, C5 MKS2-1U/100-5%-R (WIMA 1µF/100V), D4/D5 BAT85S-TAP, C1 ECEA1EKS100 (10µF/25V), C4 ECEA1CN100U (10µF/16V NP), R7 CA9V-4K7, X1/X2 XY308-2P-2.54-GN, J1 MTJ-642BX2.
Z zapasów: wszystkie rezystory 0,25 W (także R1), kondensatory foliowe C2/C3 220nF, C7 33nF, C6 220nF (żółte prostopadłościenne, raster 5,08 mm = co 2 otwory płytki uniwersalnej), płytka uniwersalna.
- **C8** 0,47 µF / 250–400 V MKT – kondensator posiadany/dokupiony, raster 7,5 mm (pola 7,62 mm) lub 5 mm z odgiętymi nóżkami; korpus stojący ≤ ~3,2 mm grubości między R1 a X1 (albo pochylony nad R1).
- **R1 4k7 0,25 W**: przy dzwonku 100 Vrms 0,228 W (obliczenia w sekcji „Napięcia linii”).


## Napięcia linii i dobór elementów strony linii (rewizja 5)
- **Pomiar u Piotra:** 42 V DC w spoczynku (słuchawka odłożona).
- **ETSI ES 201 970 / TBR21:** dzwonienie do **100 Vrms** (25 Hz, współczynnik szczytu 1,2–1,6) nałożone na napięcie DC; próba TBR21: 90 Vrms na 60 V DC. Szczyt: 100·1,6 + 60…78 V ≈ **220–240 V**. Urządzenie w stanie spoczynku **nie może pobierać prądu DC** (TBR21: < 0,6 mA podczas dzwonienia) – inaczej centralka widzi „podniesioną słuchawkę”.
- **Przyczyna błędu rew. 4:** D2 P6KE36CA (VRWM ≈ 31 V) przewodził już przy 42 V, a tor R1+R2 (2×4k7)+U1 pobierał ~4,4 mA DC → centralka sygnalizowała zajętą linię.
- **D2 → P6KE220CA** (DO-15, ten sam footprint): VRWM ≈ 185 V, VBR 209–231 V, Vc 388 V @ Ipp – nie przewodzi przy 42 V DC ani przy typowym dzwonku (42 V + 75 Vrms·1,41 ≈ 150 V), ogranicza przepięcia. Zadziała dopiero przy skrajnym dzwonku z normy – to zamierzone (ochrona K1 400 V i C8).
- **Dawny R2 4k7 → C8 0,47 µF / 250 V (lepiej 400 V) MKT.** Na PCB footprint `CFILM_P7.62` ma te same pady/otwory co dawny R2 (raster 7,62 mm) – miedź, otwory i G-code bez zmian, zmienił się tylko opis (silkscreen/Fab). Pasuje kondensator 7,5 mm lub 5 mm z odgiętymi nóżkami. C8 blokuje DC: **prąd spoczynkowy = 0**.
- **K1 → AQY214EH** (Panasonic, DIP4, 400 V / 120 mA, Ron 25–35 Ω; pinout identyczny: 1 = A, 2 = K, 3/4 = wyjście). AQY212GH (60 V) nie przeżyłby dzwonka.
- **C5 → 1 µF / 100 V MKT** (WIMA MKS2D041001K00JO00, raster 5 mm, korpus 7,2×7,2×13 mm). C5 widzi napięcie linii tylko przy zwartym K1 (6–15 V) + skok przy zamknięciu (≤ 78 V). Pojemność bez zmian → tor DTMF TX bez zmian (Xc ≈ 228 Ω @ 697 Hz).

### Obliczenia toru dzwonka (C8 0,47 µF + R1 4k7, 25 Hz)
Xc = 1/(2π·25·0,47 µF) ≈ 13,55 kΩ; |Z| = √(13,55² + 4,7²) ≈ 14,34 kΩ (LED U1 ~1,2 V pominięte).

| Dzwonek | I (rms) | I (szczyt) | P(R1) | U(C8) rms |
|---|---|---|---|---|
| 35 Vrms | 2,44 mA | 3,45 mA | 28 mW | 33 V |
| 75 Vrms | 5,23 mA | 7,4 mA | 0,13 W | 71 V |
| 90 Vrms | 6,28 mA | 8,9 mA | 0,185 W | 85 V |
| 100 Vrms | 6,97 mA | 9,9 mA | 0,228 W | 94,5 V |

- **R1 4k7 0,25 W zostaje** – nawet przy 100 Vrms (norma, skrajność) 91 % mocy, przy realnych 35–75 Vrms ≤ 0,13 W. Większy R1 *zwiększa* moc (10k → 0,35 W), bo dominuje Xc. Mniejszy (3k3 → ~0,17 W @100 Vrms) jest opcją, ale zwiększa udar przy włączeniu dzwonka (skok ~200 V / R1, τ = R1·C8 ≈ 2,2 ms) – zostajemy przy 4k7.
- **U(C8):** 94,5 Vrms (134 V szczyt) + DC 42–78 V ≈ 210 V < 250 V; 400 V daje zapas.
- **LTV-814:** CTR min 20 % @ 1 mA → przy 35 Vrms w szczycie Ic ≥ ~0,69 mA; pull-up R3 10k potrzebuje 0,33 mA → tranzystor nasycony w każdym półokresie (diody antyrównoległe = 50 impulsów/s), C1 10 µF utrzymuje GPIO3 nisko między impulsami (τ = 10k·10 µF = 0,1 s ≫ 20 ms). Brak DC nie przeszkadza – dzwonek to AC.
- Ograniczenia: dzwonienie impulsami DC (niespotykane w ES 201 970) nie zostanie wykryte; odwrócenie polaryzacji linii daje krótki impuls ~ms – odfiltruje `delayed_on` w ESPHome.

## J1 – gniazdo dodatkowego telefonu (MTJ-642BX2)
- Adam Tech MTJ-642BX2: **1 port**, RJ11 **6P4C** (4 styki obsadzone, pasuje wtyk 6P2C/6P4C), kątowe 90°, THT z zatrzaskami PCB, zatrzask wtyku u góry. Karta: https://app.adam-tech.com/products/download/data_sheet/203851/mtj-642bx2-data-sheet.pdf ; TME: https://www.tme.eu/pl/details/mtj-642bx2/zlacza-rj/adam-tech/
- Piny PCB 1–4 odpowiadają stykom wtyku 6P nr 2–5. Linia telefoniczna (środkowa para, styki 3/4 wtyku RJ11) = **piny 2 i 3** → J1.2 = L1, J1.3 = L2. Piny 1 i 4 – NC (zostaw albo obetnij). Polaryzacja L1/L2 bez znaczenia dla zwykłego telefonu; słuchawka domofonu może mieć polaryzację – wtedy sprawdź.
- Brak drugiego portu → alternatywnego wejścia linii przez RJ nie ma; linię doprowadzasz do X1. (Gdybyś chciał wejście linii kablem RJ z gniazdka, potrzebny byłby drugi MTJ-642BX2 lub inne gniazdo 2-portowe, połączony identycznie równolegle.)
- **Footprint nie pasuje wprost do rastra 2,54 mm:** piny w dwóch rzędach odległych o 2,54 mm, ale przesunięte co 1,02 mm (w rzędzie co 2,04 mm); dwa kołki zatrzasku Ø2,36 mm w rozstawie 12,00 mm. Na płytce uniwersalnej: lekko odgiąć piny 2 i 3 do sąsiednich otworów (lub nawiercić), kołki zatrzasku obciąć albo rozwiercić otwory Ø2,4 mm; ewentualnie przykleić gniazdo i połączyć piny 2/3 przewodami.
- **Uwaga – praca równoległa:** dodatkowy telefon wisi na tej samej linii co interfejs.
  - Dzwonek: oba urządzenia dostają ten sam sygnał; detekcja U1 działa normalnie, ale stary dzwonek/telefon też dzwoni i obciąża linię – przy słabej centrali prąd LED U1 może spaść (zmierz).
  - Gdy dodatkowy telefon podniesie słuchawkę, linia jest obciążona (napięcie spada do ~6–12 V). Jeśli w tym czasie ESP też zrobi off-hook (R5 równolegle), obciążenie się sumuje – napięcie i poziom tonów DTMF spadną, nadawanie „1” może nie zostać rozpoznane przez centralę, a odbiór DTMF dostaje słabszy sygnał (ew. obniż `min_amplitude`). Firmware nie wie, że inny telefon jest podniesiony (U1 wykrywa tylko dzwonek).
  - Nie podłączaj do J1 publicznej linii telefonicznej ani niczego poza słuchawką domofonu tej samej instalacji.

## Złącza XY308-2P (raster 2,54 mm)
- Pasują wprost do płytki uniwersalnej (raster 2,54 mm), da się je łączyć w zespoły.
- Raster 2,54 mm = mały zacisk: typowo przewód do ok. 0,5 mm² (AWG 26–20) wg typowych danych tej klasy złączy – dokładnego zakresu w karcie TME nie weryfikowałem. Żyły domofonowe (YTDY/YTKSY 0,5 mm średnicy ≈ 0,2 mm²) mieszczą się bez problemu; linka 0,75–1 mm² już nie – wtedy zaciśnij tulejkę lub cieńszy odcinek.
- Napięcie linii domofonu (<60 V) i prądy (mA) są dalekie od limitów takich złączy.

## Netlista
### Strona linii (izolowana od ESP)
- X1.1 = **L1**, X1.2 = **L2**
- **J1 (dodatkowy telefon): J1.2 = L1, J1.3 = L2** (równolegle do X1 i D2), J1.1, J1.4 – NC
- D2 P6KE220CA: L1–L2 (transil dwukierunkowy, VRWM 185 V – powyżej DC + szczytu dzwonka)
- Dzwonek: L1 → C8 0,47µF/250V MKT → R1 4k7 0,25W → U1.1 (LED, antyrównoległe) ; U1.2 → L2
- Off-hook: L1 → K1.4 ; K1.3 → **H** ; H → R5 330R 1W (MBE04140C3300FC100) → L2
- DTMF: H → T1.5 ; T1.8 → C5 1µF/100V MKT (WIMA MKS2) → L2  (sygnał wstrzykiwany równolegle do R5, tylko gdy K1 zwarty; C5 blokuje DC przez uzwojenie)

### Strona ESP (GND ESP)
- U1.4 (kolektor) → GPIO3 [R5] ; U1.3 (emiter) → GND [R2] ; R3 10k GPIO3–3V3 (opc.) ; C1 10µF/25V ECEA1EKS100 GPIO3–GND (+ do GPIO3)
- GPIO4 [R4] → R4 330R → K1.1 (A) ; K1.2 (K) → GND
- GPIO5 [L1] → R8a 330R → A ; GPIO6 [L2] → R8b 330R → A
- A → R6a 100R → B ; C2 220nF foliowy B–GND ; B → R6b 100R → C ; C3 220nF foliowy C–GND  (2× RC pod nośną PWM 200 kHz, tłumienie ~55 dB; pasmo DTMF płaskie w 0,3 dB. C5 zostaje 1 µF)
- C → C4 10µF/16V NP ECEA1CN100U → R7.1 ; R7.2 (suwak) + R7.3 → **D** → T1.1 ; T1.4 → GND
- **Odbiór DTMF:** węzeł **D** (R7.3 ↔ T1.1) → C6 220nF foliowy → R9 2k2 → **GPIO1 [R7]** ; R10 4k7 GPIO1–3V3 ; R11 4k7 GPIO1–GND ; C7 33nF foliowy GPIO1–GND ; D4 BAT85 (A: GPIO1, K: 3V3) ; D5 BAT85 (A: GND, K: GPIO1)
- Zasilanie: USB-C SuperMini z izolowanego zasilacza 5V (X2 XY308-2P opcjonalnie: X2.1 → 5V [R1], X2.2 → GND [R2]); 3V3 [R3] zasila R3, R10, D4

Prąd LED U1: tylko AC (C8 blokuje DC) – 2,4 mA rms przy 35 Vrms, 7 mA przy 100 Vrms; w spoczynku 0 mA.

## Tor odbioru DTMF (programowe dekodowanie w ESP32-C3)
Zamiast MT8870: sygnał z tego samego uzwojenia T1 (strona ESP) trafia na ADC1 (GPIO1), a tony rozpoznaje algorytm Goertzela w zewnętrznym komponencie [pit3k/esphome-dtmf-decoder](https://github.com/pit3k/esphome-dtmf-decoder).

**Gdzie odczep:** węzeł **D** – między trymerem R7 a uzwojeniem T1, czyli *za* trymerem (od strony T1):
- odbiór nie zależy od nastawy R7 (trymer ustawia tylko poziom nadawania, a gdyby odczep był przed nim, R7 tłumiłby też odbiór i zmiana poziomu nadawania rozstrajałaby odbiór),
- tor nadawczy przy R7 = 0 Ω obciąża uzwojenie przez C4 i filtr (setki omów, nie kilka kΩ) — jak odbiór słabnie, podnieś R7,
- podczas nadawania własny ton też trafia na ADC; firmware wyłącza dekoder na czas nadawania (`dtmf_decoder.disable` w skrypcie `open_gate`). Można go też zostawić włączonego jako test pętli zwrotnej.
- T1 przenosi sygnał linii tylko przy załączonym K1 (off-hook) – dekoder jest włączany razem z przełącznikiem off-hook.

**Elementy i wartości:**
| Ozn. | Wartość | Funkcja |
|---|---|---|
| C6 | 220 nF foliowy (zapas, raster 5,08 mm) | sprzęgający, odcina DC; z R9+R10‖R11 (≈4,5 kΩ) fd ≈ 160 Hz |
| R9 | 2,2 kΩ | szeregowy: tworzy dzielnik ×0,52 z R10‖R11 i ogranicza prąd diod D4/D5 (impuls 36 V → ~16 mA) |
| R10, R11 | 4,7 kΩ / 4,7 kΩ | polaryzacja wejścia ADC do 1,65 V (prąd 0,35 mA) |
| C7 | 33 nF foliowy (zapas, raster 5,08 mm) | filtr antyaliasingowy: R9‖R10‖R11 ≈ 1,14 kΩ → fg ≈ 4,2 kHz (przy fs = 8 kHz); niska impedancja dla próbkującego ADC |
| D4, D5 | BAT85 (Schottky) | ograniczenie napięcia na GPIO1 do −0,3…3,6 V |

**Czy potrzebny wzmacniacz? Nie.** DTMF na linii −10…0 dBm (składowa ~0,17–0,55 V sk na ton, szczyt sumy do ~1,1 V) × 0,52 = ±0,57 V wokół 1,65 V → 1,1…2,2 V, w zakresie ADC (12 dB, ~0–2,5 V). Nawet słaby ton −25 dBm daje ~32 mV szczytowo ≈ 50 LSB (próg domyślny `min_amplitude: 25` LSB). Przy dużo słabszej linii: zmniejsz R9 (np. 1 kΩ) lub obniż próg.

**Firmware dekodera** ([pit3k/esphome-dtmf-decoder](https://github.com/pit3k/esphome-dtmf-decoder), nie w tym repozytorium):
- ADC1 w trybie ciągłym (`esp_adc/adc_continuous.h`, DMA), 8000 Hz, 12 bit, tłumienie 12 dB; odczyt nieblokujący w `loop()` (bufor ~256 ms),
- blok N = 205 próbek (25,6 ms), usuwanie składowej stałej, Goertzel dla 697/770/852/941/1209/1336/1477/1633 Hz,
- warunki detekcji: amplituda ≥ `min_amplitude`, twist ≤ `max_twist` (8 dB), przewaga najsilniejszego tonu w grupie ≥ `min_group_ratio` (6 dB), udział obu tonów w energii bloku ≥ `min_tone_energy_ratio` (0,4 – odrzuca mowę/szum),
- debounce: cyfra zgłaszana po `min_on_blocks` (2 bloki ≈ 51 ms), ponowne zgłoszenie po `min_off_blocks` ciszy,
- wyjścia: `text_sensor` ostatniej cyfry, `text_sensor` sekwencji (reset po `sequence_timeout`), trigger `on_digit` (zmienna `x`) → encja `event` w HA („Domofon DTMF”),
- akcje: `dtmf_decoder.enable`, `dtmf_decoder.disable`, `dtmf_decoder.clear_sequence`,
- `debug: true` loguje poziomy tonów w każdym bloku i rzeczywistą częstotliwość próbkowania (strojenie progów).
Algorytm sprawdzony symulacją (cyfry 0–9 * #, szum, błąd częstotliwości 1,5 %, sygnał „mowy” – brak fałszywych detekcji).

## T1 – transformator 600:600 z TME
**Bourns LM-NP-1001-B1L** (symbol TME `LM-NP-1001-B1L`) – line matching transformer 600 Ω : 600 Ω, 1:1, 2,8 H, Rdc 66 Ω/66 Ω, izolacja 6,5 kV DC (EN 41003), THT 8 pin raster 2,54 mm, korpus ~17,7×12,7 mm.
https://www.tme.eu/pl/details/lm-np-1001-b1l/dlawiki/bourns/ – 9,05 zł netto (1 szt.), 211 szt. w magazynie (stan na 15.10.2026).
Uzwojenia są identyczne (dowolne pierwotne/wtórne). Wg karty Bourns (widok od spodu): uzwojenie A = piny 1–4, uzwojenie B = piny 5–8 (obsadzone piny 1, 4, 5, 8). Potwierdź omomierzem: 1–4 ≈ 66 Ω, 5–8 ≈ 66 Ω, brak ciągłości między 1/4 a 5/8.

## ESPHome (ESP32-C3)
Konfiguracja: `firmware/esphome/domofon.yaml`. Wi-Fi w `secrets.yaml` (wzór: `secrets.yaml.example`).

Komponenty są w osobnych repozytoriach, nie w tym drzewie:

- nadawanie (sinus PWM, dowolna sekwencja): [pit3k/esphome-dtmf-tone](https://github.com/pit3k/esphome-dtmf-tone)
- odbiór (Goertzel): [pit3k/esphome-dtmf-decoder](https://github.com/pit3k/esphome-dtmf-decoder)

Sekwencja, czas tonu i przerwy są encjami w Home Assistant (domyślnie sekwencja `1`, ton 200 ms). Na czas nadawania dekoder jest wyłączany, bo własny ton wpada na ADC.

## Bezpieczeństwo / uruchomienie
1. Zmierz: napięcie spoczynkowe DC, przy dzwonieniu (DC i AC), przy podniesionej słuchawce i prąd pętli → dobierz R5 (prąd jak przy oryginalnej słuchawce, zwykle 20–60 mA; moc R5 do 0,5–1 W).
2. Strona linii dobrana pod ES 201 970 (dzwonek ≤ 100 Vrms na DC ≤ 78 V): K1 400 V, D2 VRWM 185 V, C8 ≥ 250 V. W spoczynku urządzenie nie pobiera DC.
3. Nie łącz GND ESP z linią. Testuj najpierw na zasilaczu laboratoryjnym przez rezystor.
4. Ingerencja w instalację budynku – sprawdź zgodę administratora.
