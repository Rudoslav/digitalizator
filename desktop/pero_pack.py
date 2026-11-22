"""Stiahnutie a rozbalenie balíka PERO OCR (Windows). Spúšťa sa inštalátorom: `Digitalizator.exe --install-pero`."""
import hashlib
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import tools

BASE = "https://github.com/Rudoslav/digitalizator/releases/download/pero-pack-v1/"
ZIP = "pero-pack-windows-x64.zip"
DEST = tools.app_dir() / "pero"  # rozloženie: python/, pero-ocr/, models/


def install(progress=None) -> None:
    """Stiahne balík, overí kontrolný súčet a rozbalí ho do DEST. progress(fáza, hotové, spolu)."""
    def report(stage, done, total):
        if progress:
            progress(stage, done, total)

    with urllib.request.urlopen(BASE + ZIP + ".sha256", timeout=30) as r:
        want = r.read().decode().split()[0].lower()
    tmp = Path(tempfile.mkdtemp(prefix="pero_"))
    try:
        archive, h = tmp / ZIP, hashlib.sha256()
        with urllib.request.urlopen(BASE + ZIP, timeout=60) as r, open(archive, "wb") as f:
            total, done = int(r.headers.get("Content-Length", 0)), 0
            while chunk := r.read(1 << 20):
                f.write(chunk)
                h.update(chunk)
                done += len(chunk)
                report("Sťahujem", done, total)
        if h.hexdigest() != want:
            raise RuntimeError("Stiahnutý súbor je poškodený (nesedí kontrolný súčet).")
        part = DEST.with_name("pero.part")
        shutil.rmtree(part, ignore_errors=True)
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
            for i, n in enumerate(names, 1):
                zf.extract(n, part)
                if i % 200 == 0 or i == len(names):
                    report("Rozbaľujem", i, len(names))
        shutil.rmtree(DEST, ignore_errors=True)
        part.rename(DEST)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
