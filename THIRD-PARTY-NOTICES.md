# Third-party software

Vlastný kód projektu je pod licenciou MIT (pozri `LICENSE`). Windows balík navyše obsahuje tieto programy a knižnice
s vlastnými licenciami:

| Súčasť | Licencia | Zdroj |
|---|---|---|
| PySide6 / Qt | LGPL-3.0 | https://www.qt.io/qt-for-python |
| img2pdf | LGPL-3.0 | https://gitlab.mister-muffin.de/josch/img2pdf |
| fpdf2 | LGPL-3.0 | https://github.com/py-pdf/fpdf2 |
| pikepdf (qpdf) | MPL-2.0 (qpdf: Apache-2.0) | https://github.com/pikepdf/pikepdf |
| Pillow | HPND | https://github.com/python-pillow/Pillow |
| Tesseract OCR + jazykové dáta | Apache-2.0 | https://github.com/tesseract-ocr/tesseract |
| Ghostscript | **AGPL-3.0** | https://ghostscript.com/ (zdrojový kód tam) |
| Android platform-tools (adb) | Apache-2.0 / Android SDK License | https://developer.android.com/tools/releases/platform-tools |
| Liberation Sans (font) | SIL OFL-1.1 | `desktop/fonts/LICENSE-LiberationSans.txt` |
| PERO OCR (voliteľne) | BSD-3-Clause | https://github.com/DCGM/pero-ocr |

Ghostscript sa používa len ako samostatný program na prevod PDF do PDF/A (spúšťa sa ako vedľajší proces).
Jeho zdrojový kód je dostupný na uvedenej stránke.
