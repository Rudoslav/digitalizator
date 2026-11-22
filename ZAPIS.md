# Digitalizator – zápis požiadaviek a research (2026-11-21)

Stav: len zápis, žiadna implementácia. Plán zadania má vytvoriť Opus (high) agent – zatiaľ sa nerobí.

## Cieľ
DIY náhrada CZUR skenera: Android telefón na stojane kolmo nad stolom + osvetlenie, ovládanie z PC.

## Funkčné požiadavky
1. Živý náhľad toho, čo telefón vidí, na PC.
2. Snímka tlačidlom na klávesnici alebo USB nožným pedálom (väčšina pedálov = klávesnica).
3. Uložiť snímky za sebou do jedného PDF jedným tlačidlom.
4. OCR (searchable PDF), jazyky: SK, CS, DE, HU (potvrdené 2026-11-21), možno latinčina (zatiaľ nezáväzne; staré tlače/fraktúra treba otestovať). Tesseract: slk, ces, deu, hun, lat.
5. **Silná kvalita fotky** – plné rozlíšenie senzora, nie video/webcam stream.

## Používatelia a nasadenie
- Koncoví používatelia: archivárky, technicky nezdatné. Musí byť plug and play, veľké tlačidlá, slovenské UI, žiadne technické pojmy, zrozumiteľné chybové hlášky.
- Cieľové PC: **Windows 10 a 11**. Vývojový PC: Linux (Fedora) → vývoj cross-platform, balenie pre Windows (.exe inštalátor, OCR bundlnuté).
- Zatiaľ jedno pracovisko; viac pracovísk neskôr (neriešiť teraz).
- Jednorazové nastavenie robí vývojár/admin, nie archivárky.
- Odporúčanie: vyhradený telefón stále na stojane.

## Rozhodnutia
- Prenos telefón→PC: **USB kábel** (rozhodnuté 2026-11-21). USB ladenie nastaví admin raz; kábel zároveň nabíja telefón.

## Rozsah
- Teraz: voľné listy. Knihy (dewarp zakrivenia, rozdelenie spreadu) až neskôr.
- Stojan so svetlom v archíve už existuje, "nebol úplný šmejd", možno bude treba vylepšiť (difúzne svetlo z 2 strán, bez odleskov).

## Telefóny k dispozícii
Samsung Galaxy Z Flip 6 alebo Xiaomi 17T Pro (na testy kvality). Na produkciu skôr vyhradený telefón s dobrým hlavným senzorom.

## Architektúra (návrh)
- Android appka (CameraX/Camera2): náhľad na PC, zamknuté ostrenie a expozícia, odfotenie v plnom rozlíšení na povel, prenos do PC. Párovanie QR kódom; prenos Wi-Fi alebo USB (USB ladenie nastaví admin raz).
- Desktop appka (Python+Qt alebo podobné, balenie PyInstaller): náhľad, pedál/klávesa, miniatúry strán, zmazať/preusporiadať, "Uložiť PDF" = PDF + OCR automaticky.
- OCR: Tesseract cez OCRmyPDF (alt. EasyOCR/PaddleOCR pluginy). Post-processing: deskew/orez (OpenCV, príp. ScanTailor Advanced).
- scrcpy webcam režim a adb keyevent = len na rýchly test kvality, nie finálny produkt (krehké, nižšia kvalita).

## Research – nájdené na GitHube (nič hotové "všetko v jednom")
- camscan https://github.com/suhren/camscan – Python/OpenCV, webcam, split spreadu, PDF export, MIT; bez hotkey/OCR. Kandidát na fork/vzor.
- ytsutano/bookscan – de-keystoning pre jednokamerové DIY skenery.
- hxrts/book-scanner – RPi + webcam + Tesseract.
- Lios (zendalona/lios), Pi Scan (Tenrec-Builders/pi-scan), spreads (mŕtvy).
- ScanTailor Advanced https://github.com/4lex4/scantailor-advanced
- OCRmyPDF https://github.com/ocrmypdf/OCRmyPDF
- Telefón ako webcam: scrcpy+v4l2loopback wrappery (phonecam, android-webcam, android-cam-tui, ReCam) – nevhodné pre kvalitu.
- Android skenery (ScanFromCam, OpenScan, MakeACopy): skenujú v telefóne, bez PC streamu/hotkey.

## Stav dev PC (Fedora)
Je: adb, scrcpy 3.3.4, ImageMagick, python3. Chýba: tesseract, ocrmypdf, img2pdf, opencv, PyQt6. Telefón nepripojený.

## Otvorené otázky
- Model vyhradeného telefónu (zatiaľ neviem, rozhodne sa po teste kvality).
- Stojan/svetlo: použiť existujúci stojan (rozhodnuté 2026-11-21); najprv otestovať, úpravy až podľa výsledku.
- Test kvality: otestovať oba telefóny (Flip 6 aj 17T Pro) na rovnakom dokumente, porovnať ostrosť a presnosť OCR (rozhodnuté 2026-11-21).

## Research: ako robia OCR archívy v ČR/SK (2026-11-22)
Archívy engine väčšinou nezverejňujú a kvalitu OCR nehodnotia; OCR je u nich nová vec, knižnice ho robia bežne.
- Zemský archiv Opava (+ SOkA Olomouc): OCR v digitálnej badateľni od 05/2025, 600+ kroník, engine neuvedený.
- Národní archiv: metodika 2015 radí pri OCR dokumentoch zvýšiť vzorkovaciu frekvenciu; OCR/deep learning plánované (NDA II).
- AHMP Praha: Ad fontes, planetárne skenery 600 DPI; o OCR nič.
- Městská knihovna v Praze: 600 dpi JPG, 8-bit šedá, OCR ABBYY, ProArc, Kramerius. NK ČR: ABBYY (strategia 2024–2027).
- MZK Brno + VUT: PERO OCR (open source, BSD-3), staré tlače a rukopisy.
- SOA Plzeň: projekt s ZČU (OCR/HTR, 12 102 snímok / 492 GB), engine neuvedený. SOA Litoměřice, Třeboň, Hradec Králové: len skenovanie.
- ABS: fulltext OCR od 11/2022, ~8 mil. strán, engine neuvedený.
- Archiv města Plzně, Ostravy: skenovanie; MSVK (knižnica) robí sken→úprava→OCR→metadáta.
- SK: SNA/MV SR plánuje 10 digitalizačných pracovísk s OCR/ICR; TMG Digitality robila OCR pre SNA.

### Research kolo 3: ČR, PL, HU
- ČR (Plzeň SOA, MZA vrátane Jihlavy/Zlína, Třeboň/Hradec): nič nové o enginoch; väčšinou len skenovanie, SOA Plzeň s ZČU rieši OCR/HTR.
- PL: AP Szczecin – Transkribus na regestá (34 kníh, 5 000 skenov, spolu s Greifswaldom). NAC je centrum kompetencií pre digitalizáciu (Podręcznik digitalizatora). AP Poznań/Katowice/Wrocław/Kraków: skeny na szukajwarchiwach.gov.pl, OCR nespomínaný (Poznań 5 mil.+ skenov). 31 AP digitalizuje vo vlastných dielňach.
- HU: MNL (Digitális Örökség Nemzeti Laboratórium) – HTR pre matriky (Pest), otvorené TrOCR modely pre maďarské a latinské rukopisy (DH-Lab), Transkribus považovali za drahý. OSZK urobilo prvý verejný maďarský HTR model v Transkribuse (CER 6,94 %). BFL Budapešť: 10 skenerov s OCR softvérom, ~805 000 snímok ročne. OSZK/Arcanum: ABBYY FineReader 8 pri maďarských knihách.
- Možné test-kandidáty navyše: DH-Lab TrOCR (maďarčina/latinčina, rukopisy) – až pri rukopisoch; Transkribus je platený (kredity), zatiaľ mimo.

## Rozhodnutia o OCR (2026-11-22)
- **Základ: Tesseract** (slk+ces+deu+hun, možno lat). Už integrovaný cez OCRmyPDF.
- **ABBYY: nepoužijeme** (platený, bez trvalej free verzie).
- **PERO OCR: zaradiť na lokálny test.** Licencia modelov nie je problém – len lokálny test, projekt sa nikdy nebude predávať. Len lokálne, nikdy hosted API (posiela obrázky na tréning). Inštalácia z vetvy `develop` (DCGM/pero-ocr); publikované modely sú pre české noviny/európsku tlač, slovenský/maďarský model nenájdený.
- **Do testu (potvrdené 2026-11-22): Tesseract, PERO, TrOCR (až pri rukopisoch/latinčine; MNL/DH-Lab modely, TrOCR je len riadkový → potrebuje layout), voliteľne PaddleOCR. ABBYY NIE (platený). Transkribus zatiaľ nie (cloud, platený).**
- Skript `bench/bench.py`: dvojice strana.jpg + strana.txt (správny text) → CER a % zachovanej diakritiky za engine. Zatiaľ len Tesseract; PERO/PaddleOCR/TrOCR sa doplnia (TODO v kóde).
- Voliteľne PaddleOCR (zadarmo, CPU). Lokálne vision-LLM (Ollama, PaddleOCR-VL…) len ako možnosť pre ťažké strany: riziko halucinácií, pri fotkách z telefónu horšie skóre, balenie ~1–2 GB.
- Test: 10–20 reálnych strán z archívu s ručne opraveným textom; merať CER a osobitne diakritiku (ľščťžýáíéúôäňďĺŕ, ě ř ů, ű ő). Skenovať vo vyššom rozlíšení (odporúčanie NA).

## Rozhodnutie: OCR engine = PERO (2026-11-22)
Používateľ rozhodol ísť s PERO OCR. Tesseract zostáva ako záloha/rýchly režim (zatiaľ nerozhodnuté).
- PERO = toolkit (BSD-3, Python) + modely (ParseNet = riadky, OCR_350000 = čítanie riadkov); modely `pero_eu_cz_print_newspapers_2022-09-26` (EU tlač, české noviny). Neurónová sieť, nie generatívny LLM → neháda vety.
- Používatelia: MZK + VUT Brno (vývoj), Digitálna študovňa MO ČR (+ ScribbleSense), VHÚ (PERO API), UT Austin (workshop). Žiadne potvrdené nasadenie v štátnych archívoch.
- Systémové požiadavky (namerané: Ryzen AI 5 340, 12 vlákien, 14 GB RAM, bez GPU): CPU stačí, RAM špička ~0,9 GB/strana, ~8 s/strana (11 s s načítaním), disk ~2,3 GB (PyTorch prostredie 1,9 GB + modely 374 MB), Python 3.11 (numpy~=1.24; 3.14 nejde). Pomalšie PC pravdepodobne 20–60 s/strana (nemerané) → OCR dávkovo v pozadí.
- Prvé porovnanie na 2 stranách z Adobe Scan PDF (slovenský strojopis, 5 MP, otočené 90°): Tesseract 569 slov / 3,5 s, PERO 558 slov / 12,6 s, nesúhlas medzi nimi 17 % CER. Kvalita zatiaľ NEOVERENÁ voči správnemu textu (potrebný ručný prepis niekoľkých riadkov).
- Citlivé vzorky (súdne dokumenty): len lokálne, `samples/` je v .gitignore, nikam sa neposielajú; hosted PERO API sa nepoužíva.
- Ďalšie kroky: (1) integrácia PERO do desktop appky/PDF (ALTO/PAGE XML → textová vrstva, napr. OCRmyPDF plugin alebo hOCR), (2) balenie (PyTorch ~2 GB; zvážiť ONNX), (3) overiť kvalitu na správnom texte.

## Stav implementácie
Prototyp desktopovej appky v `desktop/` (Qt, PDF + OCR, dočasné sťahovanie fotiek z telefónu cez adb). Overené na vygenerovaných stranách; v teste sa stratili ű/ő a diakritika pri zmiešaných jazykoch. Xiaomi 17T Pro: adb keyevent zablokovaný (treba USB ladenie – bezpečnostné nastavenia) → vlastná Android appka. Tesseract 5.5.4 + OCRmyPDF 16.11 nainštalované.

## Ďalší krok
Reálny test kvality (fotky natívnou kamerou → OCR, porovnanie Tesseract vs PERO) → potom Opus high agent spraví plán zadania.
