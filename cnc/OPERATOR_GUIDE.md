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
| 5 | `05_mill_holes2.4_slot_endmill1.0mm.nc` | frez płaski 1,0 mm | Z −1,75 (co 0,5) | F200 / F40 | 18 000 | 2 min |
| 6 | `06_outline_tabs_endmill1.0mm.nc` | frez płaski 1,0 mm (to samo) | Z −1,75 (co 0,5) | F200 / F40 | 18 000 | 5 min |

Plik 5 to dwa otwory Ø2,4 (zaczepy gniazda J1, frezowane po okręgu) i szczelina izolacyjna pod U1/K1.
Plik 6 to kontur z 4 mostkami (2 mm szerokości, 0,6 mm grubości).
Pliki 5 i 6 używają tego samego frezu, więc **między nimi nie wymieniasz narzędzia**.
Razem z wymianami narzędzi wychodzi ok. 45 min.

Każdy plik: `G21 G90`, start na Z10, `M3 S…`, 3 s na rozpędzenie wrzeciona, na końcu `M5`, powrót na X0 Y0 (Z10) i `M30`.
Nie ma `M6` ani cykli wiertarskich (same `G0/G1/G2`).

## Układ współrzędnych
- **X0 Y0 = lewy dolny róg płytki**, patrząc z góry na miedź (tak, jak leży na stole).
- **Z0 = powierzchnia miedzi.**
- Kontur wychodzi 0,5 mm poza płytkę (X −0,5…56,0, Y −0,5…46,4).

## Potrzebne
- Laminat FR4 1,5 mm, miedź 35 µm, jednostronny. Minimum **70 × 60 mm**, wygodnie **80 × 70 mm**.
- Płyta ofiarna (MDF), taśma dwustronna (cienka, np. do wykładzin), alkohol IPA.
- V-bit 30°/0,2 mm, wiertła 0,8 / 1,0 / 1,2 mm (trzpień 3,175 mm), frez płaski 1,0 mm (trzpień 3,175 mm).
- Tuleja ER 1/8" (3,175 mm), sonda: przewód z krokodylkiem do wejścia probe Flexi-HAL.
- Multimetr, suwmiarka.

## Krok po kroku

### A. Przygotowanie
1. Zmierz suwmiarką grubość laminatu. Jeśli nie wynosi 1,5 mm, zmień `thickness` i `total_depth` w `cam_config.toml`, wygeneruj pliki ponownie i dopiero potem frezuj.
2. Opcjonalnie splanuj płytę ofiarną frezem planującym w miejscu, gdzie położysz laminat, żeby była płaska.
3. Odtłuść laminat i płytę alkoholem.
4. Okle spód laminatu taśmą dwustronną na całej powierzchni, bez przerw. Połóż go **miedzią do góry**, równolegle do osi X, i dociśnij mocno (np. wałkiem).

### B. V-bit i zerowanie
5. Załóż V-bit 30° (wysuw ok. 15 mm).
6. W ioSender podjedź Jogiem nad punkt ok. **8 mm od lewej i 8 mm od dolnej krawędzi laminatu**. To będzie lewy dolny róg płytki.
7. Wyzeruj **X i Y**: przyciski „0” przy X i Y w DRO. Od tej chwili **nie ruszaj zera XY aż do końca**.
8. Zeruj Z sondą (zalecane):
   - Krokodylek GND na **trzpień V-bitu**, przewód probe na **miedź laminatu**.
   - Sprawdź przewodzenie: dotknij palcem lub folią obu i zobacz, czy w ioSender zapala się sygnał Probe.
   - ioSender → zakładka **Probing → Tool length offset / Height**. Grubość płytki dotykowej = **0**, bo dotykasz samej miedzi. Uruchom probe, by ustawić Z0.
   - Ręcznie zamiast tego: w MDI wpisz `G38.2 Z-5 F50`, a potem `G10 L20 P0 Z0`.
   - Podjedź do Z5 i **zdejmij krokodylki**.
   - Bez sondy: metoda kartki. Opuść narzędzie do lekkiego oporu kartki 0,1 mm, potem `G10 L20 P0 Z0.1`.

### C. Height Map (opcjonalnie, ale polecane)
Laminat prawie nigdy nie leży idealnie płasko, a V-bit przy 0,1 mm głębokości jest bardzo czuły na Z.
9. Załaduj `01_isolation_vbit30.nc`. Załóż krokodylki jak w kroku 8.
10. ioSender → **Probing → Height map**. Obszar pobierz z limitów programu (ok. X0–54, Y0–45). Siatka **5–8 mm**, posuw probe F50, wysokość przejazdu 1–2 mm.
11. Uruchom pomiar. Po zakończeniu zrób **Apply to program**: ioSender poprawi Z w załadowanym programie.
12. Zdejmij krokodylki.

### D. Izolacja (plik 01)
13. Załaduj `01_isolation_vbit30.nc`, sprawdź podgląd 3D (ma wyglądać jak w [`previews/toolpaths_overview.png`](previews/toolpaths_overview.png)).
14. Włącz odciąg lub odkurzacz (pył FR4 jest szkodliwy), załóż okulary i **Cycle Start**.
15. Po pierwszym okrążeniu pada zatrzymaj (**Feed Hold**) i sprawdź rowek:
    - musi przeciąć miedź na całej długości, do żółtawego FR4, ale nie głęboko;
    - jeśli miejscami zostaje miedź, zatrzymaj, **Reset**, obniż Z0 o 0,02–0,03 mm (`G10 L20 P0 Z0.03` w bieżącej pozycji nad miedzią) i uruchom 01 jeszcze raz;
    - jeśli jest za głęboko i szeroko, podnieś Z0.
16. Po końcu pliku obejrzyj płytkę (lupa). **Nie zdejmuj płytki** ze stołu.

### E. Wymiana narzędzia – za każdym razem tak samo
17. Poczekaj, aż plik się skończy (wrzeciono stoi, M5).
18. Podnieś Z (Jog), nie ruszaj X ani Y. Jeśli trzeba, podjedź tylko w Z.
19. Wymień narzędzie (wysuw jak najkrótszy, ale tak, by przejść 1,9 mm w głąb).
20. **Zeruj tylko Z** (krok 8: sonda lub kartka) nad miedzią, blisko płytki. **Nie zeruj X ani Y!**
21. Zdejmij krokodylki, załaduj następny plik, **Cycle Start**.
   - Height Map nakładaj **tylko** na plik 01. Wiercenie i kontur idą przez materiał na wylot, więc jej nie potrzebują.

### F. Wiercenie (pliki 02, 03, 04)
22. Wiertło 0,8 → plik `02`, wymiana (kroki 17–21) → wiertło 1,0 → `03`, wymiana → wiertło 1,2 → `04`.
23. Po każdym pliku sprawdź, czy otwory trafiły w środki padów.

### G. Frez 1,0 mm: otwory 2,4, szczelina, kontur (pliki 05, 06)
24. Załóż frez płaski 1,0 mm, zeruj tylko Z, uruchom `05_…`.
25. Bez wymiany narzędzia uruchom `06_outline_tabs_…`. Kontur idzie na zewnątrz płytki w 4 przejściach i zostawia 4 mostki.
26. Odkurz pył.

### H. Zdjęcie i wykończenie
27. Podważ laminat szpachelką, zdejmij taśmę.
28. Przetnij mostki (nożyk lub obcinaczki), wyrównaj krawędzie pilnikiem lub papierem.
29. Oczyść miedź: gąbka ścierna lub drobny papier (P600+), potem IPA. Usuń zadziory z otworów (wiertło większe, ręcznie).
30. Opcjonalnie: kalafonia w IPA lub lakier lutowniczy, żeby miedź nie śniedziała.

### I. Kontrola multimetrem (przed lutowaniem!)
31. W trybie ciągłości sprawdź **brak zwarć** między sąsiednimi ścieżkami, zwłaszcza tam, gdzie odstęp jest mały (okolice R/C przy T1).
32. **Bariera izolacyjna:** strona linii (J1, T1 pin 5/8, K1 3/4, U1 1/2, transil) **nie może mieć połączenia** ze stroną ESP (GND, 3V3, GPIO). Sprawdź na zakresie 200 MΩ albo w trybie ciągłości, że jest przerwa, między linią a GND ESP. Szczelina pod U1/K1 musi być przecięta na wylot.
33. Sprawdź ciągłość kilku dłuższych ścieżek (pad–pad), czy rowek ich nie przeciął.

### J. Montaż
34. **Zworka JP1:** drut (np. odcięta nóżka rezystora) wlutowany **od strony elementów** (góra, bez miedzi), zgodnie z warstwą `F_Cu-jumpers_DO_NOT_MILL`.
35. Elementy wkładaj od strony bez miedzi, lutuj od strony miedzi.

## Bezpieczeństwo i typowe problemy
- Krokodylki **zawsze zdejmij** przed startem wrzeciona.
- Najpierw najlepiej zrobić **próbę na skrawku laminatu**: sam plik 01 przez 1–2 minuty, żeby dobrać Z0 i obroty.
- Rowek za płytki lub nierówny: laminat odstaje, użyj Height Map, dociśnij taśmę, splanuj płytę ofiarną.
- Wyrwane pady przy wierceniu: za duży posuw lub tępe wiertło. Zmniejsz `feed` w `[drill]`.
- Zmiana parametrów: edytuj [`cam_config.toml`](cam_config.toml), potem `python3 cnc/scripts/verify_gcode.py` (wygeneruje pliki ponownie i sprawdzi je).
