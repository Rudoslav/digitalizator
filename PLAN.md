# Plán – čo bude treba

## Hardvér
- Existujúci stojan so svetlom v archíve; otestovať a prípadne doladiť osvetlenie (difúzne, bez odleskov).
- Telefón: Flip 6 a 17T Pro na test kvality, neskôr vyhradený telefón na stojane.
- Kvalitný a dosť dlhý USB kábel (telefón sa cez neho aj nabíja).
- USB nožný pedál (tvári sa ako klávesnica).
- PC s Windows 10/11 v archíve.

## Android appka (Kotlin, CameraX/Camera2)
- Náhľad do PC a odfotenie na povel v plnom rozlíšení.
- Zamknuté ostrenie a expozícia, vypnuté zhasínanie obrazovky.
- Prenos cez USB; USB ladenie nastaví admin raz.
- Jednoduché párovanie s PC.

## Desktopová appka (Windows; vývoj na Fedore)
- Živý náhľad, snímka klávesou alebo pedálom, miniatúry strán.
- Zmazať poslednú stranu, zmeniť poradie.
- Orezanie a vyrovnanie strán (OpenCV).
- Tlačidlo „Uložiť PDF" = PDF + OCR bez ďalšieho nastavovania.
- Slovenské UI, veľké tlačidlá, zrozumiteľné chybové hlášky.
- OCR: Tesseract cez OCRmyPDF; jazyky slk, ces, deu, hun, možno lat.

## Balenie a nasadenie
- Jeden inštalátor pre Windows (.exe) so všetkým vnútri (OCR, adb).
- Návod na jednorazové nastavenie telefónu pre admina.

## Vývojový PC (Fedora)
- Doinštalovať tesseract, ocrmypdf, opencv, PyQt a jazykové balíky.
- Na test Windows balíka treba Windows PC alebo VM.

## Postup
1. Test kvality na oboch telefónoch (natívna kamera + adb, OCR na tom istom dokumente).
2. Plán zadania (Opus high agent).
3. Prototyp desktopovej appky.
4. Android appka.
5. Balenie a skúška s archivárkami.

## Neskôr (zatiaľ neriešime)
- Knihy: dewarp zakrivenia, rozdelenie rozkrytej knihy.
- Viac pracovísk.

Podrobnosti, rozhodnutia a research: [ZAPIS.md](ZAPIS.md)
