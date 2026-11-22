"""Zloženie strán do PDF a OCR. Bez GUI, aby sa to dalo testovať samostatne."""
import shutil
import subprocess
import tempfile
from pathlib import Path

import img2pdf

OCR_LANGS = "slk+ces+deu+hun+eng"


def build_pdf(images: list[Path], out_pdf: Path, ocr: bool = True, langs: str = OCR_LANGS) -> None:
    """Zloží obrázky (v danom poradí) do jedného PDF. JPEG sa vkladá bez rekompresie,
    takže sa nestráca kvalita. Ak ocr=True, pridá textovú vrstvu cez OCRmyPDF."""
    if not images:
        raise ValueError("Žiadne strany na uloženie.")
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.pdf"
        raw.write_bytes(img2pdf.convert([str(p) for p in images]))
        if not ocr:
            shutil.copyfile(raw, out_pdf)
            return
        cmd = [
            "ocrmypdf",
            "--language", langs,
            "--output-type", "pdf",
            "--optimize", "0",       # nerekomprimovať obrázky
            "--skip-text",
            str(raw), str(out_pdf),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "OCR zlyhalo.")
