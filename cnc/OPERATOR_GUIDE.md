# Instrukcja dla operatora frezarki – płytka domofon-esp32

Maszyna: **PrintNC + Flexi-HAL (grblHAL)**, sender: **ioSender**.
Płytka jednostronna **55,5 × 45,9 mm**, miedź tylko od spodu (B.Cu). Pliki: [`gcode/`](gcode/).

> **Lustro jest już w plikach.** Laminat kładziesz **miedzią do góry**, a pliki są odbite w X.
> **Nie frezuj** `domofon-F_Cu-jumpers_DO_NOT_MILL.gtl`. Zworka JP1 to kawałek drutu.

## Pliki (uruchamiaj w tej kolejności)

| # | Plik | Narzędzie | Głębokość | Posuw / zagłębianie | Obroty | Czas ≈ |
|---|---|---|---|---|---|---|
| 1 | `01_isolation_vbit30.nc` | V-bit 30°, czubek 0,2 mm | Z −0,10 | F300 / F60 | 20 000 | 14 min |
| 2 | `02_drill_0.8mm.nc` | wiertło 0,8 mm (46 otw.) | Z −1,9 | F60 | 18 000 | 3 min |
| 3 | `03_drill_1.0mm.nc` | wiertło 1,0 mm (26 PTH + 2 NPTH) | Z −1,9 | F60 | 18 000 | 2 min |
| 4 | `04_drill_1.2mm.nc` | wiertło 1,2 mm (11 otw.) | Z −1,9 | F60 | 18 000 | 1 min |
| 5 | `05_mill_holes2.4_slot_endmill0.8mm.nc` | frez płaski 0,8 mm | Z −1,75 (co 0,4) | F150 / F30 (rampa F60) | 18 000 | 6 min |
| 6 | `06_outline_tabs_endmill0.8mm.nc` | frez płaski 0,8 mm (to samo) | Z −1,75 (co 0,4) | F150 / F30 | 18 000 | 8 min |

Plik 5 to dwa otwory Ø2,4 (zaczepy gniazda J1, frezowane po okręgu) i szczelina izolacyjna pod U1/K1.
Plik 6 to kontur z 4 mostkami (2 mm szerokości, 0,6 mm grubości).
Pliki 5 i 6 używają tego samego frezu, więc **między nimi nie wymieniasz narzędzia**.
Razem z wymianami narzędzi wychodzi ok. 50 min.

Każdy plik: `G21 G90`, start na Z10, `M3 S…`, 3 s na rozpędzenie wrzeciona, na końcu `M5`, powrót na X0 Y0 (Z10) i `M30`.
Nie ma `M6` ani cykli wiertarskich (same `G0/G1/G2`).

## Układ współrzędnych
- **X0 Y0 = lewy dolny róg płytki**, patrząc z góry na miedź (tak, jak leży na stole).
- **Z0 = powierzchnia miedzi.**
- Kontur wychodzi 0,5 mm poza płytkę (X −0,5…56,0, Y −0,5…46,4).

## Potrzebne
- Laminat FR4 1,5 mm, miedź 35 µm, jednostronny. Minimum **70 × 60 mm**, wygodnie **80 × 70 mm**.
- Płyta ofiarna (MDF), taśma dwustronna (cienka, np. do wykładzin), alkohol IPA.
- V-bit 30°/0,2 mm, wiertła 0,8 / 1,0 / 1,2 mm, frez płaski 0,8 mm (wszystkie z trzpieniem 3,175 mm), tuleja ER 1/8".
- **Sonda 3D** (V6 / TP06 „Anti-roll 3D Touch Probe”) z tuleją ER **6 mm**, podłączona do wejścia **Probe** Flexi-HAL.
- Kartka papieru (ok. 0,1 mm), multimetr, suwmiarka.

### Sonda 3D – założenia (sprawdź u siebie)
- Typowa specyfikacja tej sondy:
  - zasilanie 5–24 V DC, wyjście **NPN-NO**, 3 przewody: czerwony VCC, żółty/biały sygnał, czarny GND;
  - LED: zielony w spoczynku, czerwony po dotknięciu;
  - trzpień 6 mm;
  - powtarzalność ok. 0,01 mm przy posuwie 50–200 mm/min;
  - bicie fabryczne do 0,05 mm;
  - **dobieg Z tylko 2 mm** (XY ±4 mm).
- Podłączenie: sygnał do wejścia **Probe** Flexi-HAL, GND do GND, VCC z zasilania czujników (5 V lub 24 V, zależnie od złącza).
- Test przed pierwszym użyciem:
  - w ioSender w spoczynku sygnał Probe ma być **nieaktywny**, a po dotknięciu kulki palcem **aktywny** (LED czerwony);
  - jeśli jest odwrotnie, przełącz `$6` (odwrócenie wejścia probe).

## Krok po kroku

### A. Przygotowanie
1. Zmierz suwmiarką grubość laminatu. Jeśli nie wynosi 1,5 mm, zmień `thickness` i `total_depth` w `cam_config.toml` i wygeneruj pliki ponownie.
2. Opcjonalnie splanuj płytę ofiarną w miejscu, gdzie położysz laminat.
3. Odtłuść laminat i płytę alkoholem.
4. Okle spód laminatu taśmą dwustronną na całej powierzchni, połóż go **miedzią do góry**, równolegle do osi X, i dociśnij mocno.

### B. Zero XY (V-bitem)
5. Załóż V-bit 30°.
6. Podjedź Jogiem czubkiem V-bitu nad punkt ok. **8 mm od lewej i 8 mm od dolnej krawędzi laminatu**. To lewy dolny róg płytki.
7. Wyzeruj **X i Y** w DRO. Od teraz **nie zmieniaj zera XY aż do końca**.
   - Nie zeruj XY sondą 3D, jeśli nie jest wycentrowana czujnikiem zegarowym. Ma bicie do 0,05 mm i to bicie zmienia się przy każdym założeniu. Czubek V-bitu jest wystarczająco dokładny.

### C. Height Map sondą 3D
Mapa w ioSender jest **względna**. Wysokości są liczone od **pierwszego punktu siatki**, czyli lewego dolnego rogu obszaru (Min X, Min Y). Dla naszego pliku to **X0 Y0**.
Dlatego później zerujesz Z V-bitu **dokładnie w X0 Y0**.

8. Podnieś Z, zdejmij V-bit, załóż sondę 3D. **Wrzeciono wyłączone**, najlepiej z wyłączonym falownikiem.
9. Sprawdź sondę: LED zielony, dotknięcie kulki zmienia sygnał Probe w ioSender.
10. Załaduj `01_isolation_vbit30.nc`.
11. ioSender → zakładka **Probing** → **Height map**:
    - **Area to probe**: przycisk **Set from program limits** (powinno wyjść X0, Y0, W ≈ 53,6, H ≈ 44,2);
    - **Gridsize**: 5 mm, ewentualnie zaznacz **Lock**, żeby X i Y były równe;
    - „Set Z = 0 at X0Y0” **odznaczone**, bo i tak zmieniasz potem narzędzie;
    - „Pause before probing” odznaczone.
12. Parametry w **Probing distances and speed**:
    - **Probing distance** 3 mm;
    - **Search feed rate** 100;
    - **Latch distance** 0,5–1 mm;
    - **Latch feed rate** 50.
    - **Probe/touchplate XY offsets** 0.
    - Uwaga: sonda ma tylko 2 mm dobiegu w Z. Jeśli sonda nic nie trafi, zjedzie co najwyżej o Probing distance poniżej punktu startu. Dlatego startuj nisko.
13. Podjedź sondą **1–1,5 mm nad miedź**. Ta wysokość to wysokość przejazdów między punktami.
14. **Start**. ioSender najpierw podjedzie do X0 Y0 i pokaże okno z informacją o tym ruchu (OK), potem zmierzy siatkę.
15. Na końcu pojawi się komunikat „Probing completed: Z min … Z max …”.
    - Jeśli różnica przekracza 0,3 mm, laminat odstaje: dociśnij go albo przyklej ponownie i zmierz jeszcze raz.
16. **Save**: zapisz mapę (`.map`) na wypadek restartu ioSendera. Później wczytasz ją przez **Load**.

### C2. V-bit i Z0 w punkcie odniesienia mapy
17. Podnieś Z, **zdejmij sondę 3D**, załóż V-bit.
18. Zero Z V-bitu **w punkcie X0 Y0** (`G0 X0 Y0`). To musi być dokładnie ten punkt, który jest zerem mapy.
    - **Metoda kartki (domyślna):** połóż kartkę na miedzi pod czubkiem. Opuszczaj Z krokiem 0,01 mm, aż kartka zacznie stawiać opór przy przesuwaniu. Wpisz w MDI `G10 L20 P0 Z0.1` (0,1 = grubość kartki, zmierz ją suwmiarką). Zdejmij kartkę.
    - **Czujnik długości narzędzia (tool setter), jeśli masz:**
      - zanim zdejmiesz sondę, ustaw nią Z0 w X0 Y0: z wysokości ok. 1 mm wpisz w MDI `G38.2 Z-3 F50`, potem `G10 L20 P0 Z0`;
      - zmierz sondę na czujniku (**Probing → Tool length offset**);
      - po założeniu V-bitu zmierz go tam samo;
      - ioSender doliczy różnicę długości (TLO), więc Z0 zostaje bez zmian.
19. Zostaw załadowany `01_isolation_vbit30.nc` → **Probing → Height map → Apply**. ioSender skoryguje Z w programie (po restarcie najpierw **Load** mapy).
20. Podjedź na Z5.

### D. Izolacja (plik 01)
21. Sprawdź podgląd 3D (ma wyglądać jak w [`previews/toolpaths_overview.png`](previews/toolpaths_overview.png)).
22. Włącz odciąg lub odkurzacz (pył FR4 jest szkodliwy), załóż okulary i **Cycle Start**.
23. Po pierwszym okrążeniu pada zatrzymaj (**Feed Hold**) i sprawdź rowek:
    - musi przeciąć miedź na całej długości, do żółtawego FR4, ale nie głęboko;
    - jeśli miejscami zostaje miedź (kartka to dokładność ok. ±0,03 mm), zatrzymaj, **Reset**, obniż Z0 o 0,02–0,03 mm i uruchom 01 jeszcze raz. Mapa jest względna, więc zostaje ważna. Obniżenie w MDI: `G10 L20 P0 Z0.03`, gdy V-bit stoi tam, gdzie wcześniej było Z0;
    - jeśli rowek jest za głęboki i szeroki, podnieś Z0.
24. Po końcu pliku obejrzyj płytkę (lupa). **Nie zdejmuj płytki** ze stołu.

### E. Wymiana narzędzia – za każdym razem tak samo
25. Poczekaj, aż plik się skończy (wrzeciono stoi, M5).
26. Podnieś Z (Jog), nie ruszaj X ani Y. Jeśli trzeba, podjedź tylko w Z.
27. Wymień narzędzie (wysuw jak najkrótszy, ale tak, by przejść 1,9 mm w głąb).
28. **Zeruj tylko Z, metodą kartki** (jak w kroku 18), na miedzi blisko płytki. **Nie zeruj X ani Y!**
    - Precyzja nie jest tu potrzebna: wiertła i frez schodzą 0,25–0,4 mm poniżej spodu laminatu.
    - Sondą 3D tego nie zrobisz, bo mierzy tylko samą siebie, a nie nowe narzędzie.
29. Załaduj następny plik, **Cycle Start**.
    - Height Map nakładaj **tylko** na plik 01. Wiercenie i kontur przechodzą na wylot, więc jej nie potrzebują.

### F. Wiercenie (pliki 02, 03, 04)
30. Wiertło 0,8 → plik `02`, wymiana (kroki 25–29) → wiertło 1,0 → `03`, wymiana → wiertło 1,2 → `04`.
31. Po każdym pliku sprawdź, czy otwory trafiły w środki padów.

### G. Frez 0,8 mm: otwory 2,4, szczelina, kontur (pliki 05, 06)
32. Załóż frez płaski 0,8 mm, zeruj tylko Z, uruchom `05_…`.
33. Bez wymiany narzędzia uruchom `06_outline_tabs_…`. Kontur idzie na zewnątrz płytki w 4 przejściach i zostawia 4 mostki.
34. Odkurz pył.

### H. Zdjęcie i wykończenie
35. Podważ laminat szpachelką, zdejmij taśmę.
36. Przetnij mostki (nożyk lub obcinaczki), wyrównaj krawędzie pilnikiem lub papierem.
37. Oczyść miedź: gąbka ścierna lub drobny papier (P600+), potem IPA. Usuń zadziory z otworów (wiertło większe, ręcznie).
38. Opcjonalnie: kalafonia w IPA lub lakier lutowniczy, żeby miedź nie śniedziała.

### I. Kontrola multimetrem (przed lutowaniem!)
39. W trybie ciągłości sprawdź **brak zwarć** między sąsiednimi ścieżkami, zwłaszcza tam, gdzie odstęp jest mały (okolice R/C przy T1).
40. **Bariera izolacyjna:** strona linii (J1, T1 pin 5/8, K1 3/4, U1 1/2, transil) **nie może mieć połączenia** ze stroną ESP (GND, 3V3, GPIO). Sprawdź na zakresie 200 MΩ albo w trybie ciągłości, że jest przerwa, między linią a GND ESP. Szczelina pod U1/K1 musi być przecięta na wylot.
41. Sprawdź ciągłość kilku dłuższych ścieżek (pad–pad), czy rowek ich nie przeciął.

### J. Montaż
42. **Zworka JP1:** drut (np. odcięta nóżka rezystora) wlutowany **od strony elementów** (góra, bez miedzi), zgodnie z warstwą `F_Cu-jumpers_DO_NOT_MILL`.
43. Elementy wkładaj od strony bez miedzi, lutuj od strony miedzi.

## Bezpieczeństwo i typowe problemy
- **Nigdy nie włączaj wrzeciona z sondą 3D w uchwycie.** Pliki `.nc` od razu wydają `M3`, więc przed **Cycle Start** zawsze sprawdź, czy w uchwycie jest narzędzie, a nie sonda.
- Sondą jedź tylko z posuwami 50–200 mm/min i nisko nad miedzią. Dobieg w Z to tylko 2 mm.
- Przed każdym pomiarem sprawdź, czy sygnał Probe reaguje na dotknięcie kulki. Jeśli nie, **nie startuj**.
- Najpierw najlepiej zrobić **próbę na skrawku laminatu**: sam plik 01 przez 1–2 minuty, żeby dobrać Z0 i obroty.
- Rowek za płytki lub nierówny: laminat odstaje. Dociśnij taśmę, zrób mapę gęściej (siatka 4 mm), splanuj płytę ofiarną.
- Wyrwane pady przy wierceniu: za duży posuw lub tępe wiertło. Zmniejsz `feed` w `[drill]`.
- Zmiana parametrów: edytuj [`cam_config.toml`](cam_config.toml), potem `python3 cnc/scripts/verify_gcode.py` (wygeneruje pliki ponownie i sprawdzi je).
