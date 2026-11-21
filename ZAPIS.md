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

## Ďalší krok
Test kvality (natívna kamera + adb) → potom nechať Opus high agenta spraviť plán zadania.
