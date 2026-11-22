"""Zloženie strán do PDF a OCR (PERO, záloha Tesseract). Bez GUI, aby sa to dalo testovať samostatne."""
import io
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import fpdf
import img2pdf
import pikepdf

import tools

OCR_LANGS = "slk+ces+deu+hun+eng"  # len pre Tesseract
ROOT = tools.app_dir()
FONT = tools.resource_dir() / "fonts" / "LiberationSans-Regular.ttf"  # má všetku potrebnú diakritiku
PERO_PY = ROOT / ".venv-pero" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
PERO_SCRIPT = ROOT / "vendor" / "pero-ocr" / "user_scripts" / "parse_folder.py"
PERO_CFGS = sorted((ROOT / "vendor" / "pero-models-dl" / "extracted").glob("*/config_cpu.ini"))


def pero_available() -> bool:
    return PERO_PY.exists() and PERO_SCRIPT.exists() and bool(PERO_CFGS) and FONT.exists()


def _raw_pdf(images: list[Path]) -> bytes:
    # rotation=ifvalid: telefón občas zapíše neplatnú EXIF orientáciu (0)
    # 300 dpi: fotky z telefónu nemajú DPI, tak má PDF rozumný rozmer strany
    return img2pdf.convert(
        [str(p) for p in images],
        rotation=img2pdf.Rotation.ifvalid,
        layout_fun=img2pdf.get_fixed_dpi_layout_fun((300, 300)),
    )


def _build_text_pdf(images: list[Path], out_pdf: Path, ocr: bool = True, engine: str = "auto",
              langs: str = OCR_LANGS, progress=None) -> str:
    """Zloží obrázky (v danom poradí) do jedného PDF; JPEG sa vkladá bez rekompresie.
    engine: "auto" (PERO ak je k dispozícii, inak Tesseract), "pero", "tesseract".
    progress(hotové, spolu) sa volá po dokončení každej strany. Vráti popis použitého OCR."""
    if not images:
        raise ValueError("Žiadne strany na uloženie.")
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    if not ocr:
        out_pdf.write_bytes(_raw_pdf(images))
        return "bez OCR"
    if engine == "auto":
        engine = "pero" if pero_available() else "tesseract"
    if engine == "pero":
        try:
            _build_pero(images, out_pdf, progress)
            return "PERO"
        except Exception as e:  # noqa: BLE001 - záloha: Tesseract
            _build_tesseract(images, out_pdf, langs, progress)
            return f"Tesseract (PERO zlyhal: {str(e)[:120]})"
    _build_tesseract(images, out_pdf, langs, progress)
    return "Tesseract"


# ---------------------------------------------------------------- PERO
def _build_pero(images: list[Path], out_pdf: Path, progress) -> None:
    if not pero_available():
        raise RuntimeError("PERO nie je nainštalovaný.")
    total = len(images)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        inp, out = tmp / "in", tmp / "alto"
        inp.mkdir()
        out.mkdir()
        for i, p in enumerate(images):
            link = inp / f"p{i:05d}{p.suffix.lower()}"
            try:
                link.symlink_to(p.resolve())
            except OSError:
                shutil.copyfile(p, link)

        proc = subprocess.Popen(
            [str(PERO_PY), str(PERO_SCRIPT), "-c", str(PERO_CFGS[0]), "-i", str(inp),
             "--output-alto-path", str(out), "--word-splitters", " ", "--device", "cpu"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, **tools.NOWIN,
        )
        tail: list[str] = []
        for line in proc.stdout:
            tail = (tail + [line.strip()])[-15:]
            m = re.search(r"DONE (\d+)/(\d+)", line)
            if m and progress:
                progress(int(m.group(1)), total)
        if proc.wait() != 0:
            raise RuntimeError(" | ".join(tail[-3:]))

        altos = {i: out / f"p{i:05d}.xml" for i in range(total)}
        missing = [i + 1 for i, a in altos.items() if not a.exists()]
        if missing:
            raise RuntimeError(f"PERO nevytvoril výstup pre strany {missing}.")
        _overlay(images, altos, out_pdf)


def _overlay(images: list[Path], altos: dict[int, Path], out_pdf: Path) -> None:
    """Pôvodné strany (obrázky) + neviditeľná textová vrstva z ALTO XML (spoločné pre PERO aj Tesseract)."""
    raw = pikepdf.open(io.BytesIO(_raw_pdf(images)))
    keep = []
    for i in range(len(images)):
        page = raw.pages[i]
        w_pt, h_pt = (float(x) for x in page.mediabox[2:4])
        layer = pikepdf.open(io.BytesIO(_text_layer(altos[i], w_pt, h_pt)))
        keep.append(layer)
        page.add_overlay(layer.pages[0])
    raw.save(out_pdf)
    raw.close()
    for k in keep:
        k.close()


def _text_layer(alto: Path, w_pt: float, h_pt: float) -> bytes:
    """Neviditeľná textová vrstva (po slovách) podľa ALTO z PERO, zmenšená na rozmer strany v bodoch."""
    root = ET.parse(alto).getroot()
    page = next(e for e in root.iter() if e.tag.endswith("}Page") or e.tag == "Page")
    sx, sy = w_pt / int(page.attrib["WIDTH"]), h_pt / int(page.attrib["HEIGHT"])

    pdf = fpdf.FPDF(unit="pt", format=(w_pt, h_pt))
    pdf.set_auto_page_break(False)
    pdf.add_font("F", "", str(FONT))
    pdf.add_page()
    pdf.text_mode = "INVISIBLE"
    for s in root.iter():
        if not (s.tag.endswith("}String") or s.tag == "String"):
            continue
        text = s.attrib.get("CONTENT", "")
        if not text.strip():
            continue
        x, y = float(s.attrib["HPOS"]) * sx, float(s.attrib["VPOS"]) * sy
        w, h = float(s.attrib["WIDTH"]) * sx, float(s.attrib["HEIGHT"]) * sy
        pdf.set_stretching(100.0)  # inak sa šírka meria s roztiahnutím z predošlého slova
        pdf.set_font("F", size=max(h * 0.8, 1.0))
        tw = pdf.get_string_width(text)
        pdf.set_stretching(100.0 * w / tw if tw > 0 else 100.0)
        pdf.text(x, y + h * 0.8, text)
    return bytes(pdf.output())


# ------------------------------------------------------------ Tesseract
def _build_tesseract(images: list[Path], out_pdf: Path, langs: str, progress) -> None:
    """Tesseract vráti ALTO XML (rovnaký formát ako PERO), textovú vrstvu skladáme rovnako."""
    total = len(images)
    workers = max(1, min(total, (os.cpu_count() or 2) // 2))
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        def ocr(i: int, img: Path) -> Path:
            base = tmp / f"p{i:05d}"
            proc = subprocess.run(
                [tools.tesseract(), str(img), str(base), "-l", langs, "alto"],
                capture_output=True, text=True, **tools.NOWIN,
                env={**os.environ, "OMP_THREAD_LIMIT": "1", **tools.tessdata_env()},
            )
            if proc.returncode != 0 or not base.with_suffix(".xml").exists():
                raise RuntimeError(f"Strana {i + 1}: " + (proc.stderr.strip()[-200:] or "OCR zlyhalo."))
            return base.with_suffix(".xml")

        altos: dict[int, Path] = {}
        done = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(ocr, i, p): i for i, p in enumerate(images)}
            for f in as_completed(futs):
                altos[futs[f]] = f.result()
                done += 1
                if progress:
                    progress(done, total)
        _overlay(images, altos, out_pdf)


# -------------------------------------------------------------- PDF/A
def _gs_exe() -> str | None:
    return tools.gs()


def _gs_icc(gs: str) -> Path | None:
    """sRGB profil, ktorý je súčasťou Ghostscriptu (Linux aj Windows)."""
    base = Path(gs).resolve().parent.parent
    roots = [Path("/usr/share/ghostscript"), base / "share" / "ghostscript", base]
    for r in roots:
        for pat in ("iccprofiles/srgb.icc", "*/iccprofiles/srgb.icc", "*/*/iccprofiles/srgb.icc"):
            found = sorted(r.glob(pat))
            if found:
                return found[-1]
    return None


def _to_pdfa(pdf: Path) -> str:
    """Prevedie hotové PDF na PDF/A-2b cez Ghostscript. Vráti popis; pri chybe nechá pôvodné PDF."""
    gs = _gs_exe()
    icc = _gs_icc(gs) if gs else None
    if not gs or not icc:
        return "bez PDF/A: chýba Ghostscript"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        icc_ps = str(icc).replace("\\", "/")
        (tmp / "PDFA_def.ps").write_text(
            "%!\n"
            f"/ICCProfile ({icc_ps}) def\n"
            "[/_objdef {icc_PDFA} /type /stream /OBJ pdfmark\n"
            "[{icc_PDFA} <</N 3>> /PUT pdfmark\n"
            "[{icc_PDFA} ICCProfile (r) file /PUT pdfmark\n"
            "[/_objdef {OutputIntent_PDFA} /type /dict /OBJ pdfmark\n"
            "[{OutputIntent_PDFA} <</Type /OutputIntent /S /GTS_PDFA1 "
            "/DestOutputProfile {icc_PDFA} /OutputConditionIdentifier (sRGB)>> /PUT pdfmark\n"
            "[{Catalog} <</OutputIntents [ {OutputIntent_PDFA} ]>> /PUT pdfmark\n"
        )
        out = tmp / "pdfa.pdf"
        r = subprocess.run(
            [gs, f"--permit-file-read={icc}", "-dPDFA=2", "-dPDFACompatibilityPolicy=1", "-dBATCH", "-dNOPAUSE", "-dNOOUTERSAVE",
             "-dQUIET", "-sDEVICE=pdfwrite", "-sColorConversionStrategy=RGB",
             "-sProcessColorModel=DeviceRGB", "-dPassThroughJPEGImages=true",
             f"-sOutputFile={out}", str(tmp / "PDFA_def.ps"), str(pdf)],
            capture_output=True, text=True, **tools.NOWIN,
        )
        if r.returncode != 0 or not out.exists() or out.stat().st_size == 0:
            return "bez PDF/A: " + ((r.stderr + r.stdout).strip()[-300:] or "Ghostscript zlyhal")
        shutil.copyfile(out, pdf)
    return "PDF/A"


def build_pdf(images: list[Path], out_pdf: Path, ocr: bool = True, engine: str = "auto",
              langs: str = OCR_LANGS, progress=None) -> str:
    """Vytvorí PDF/A s textovou vrstvou (OCR). Vráti popis: použitý engine a PDF/A."""
    used = _build_text_pdf(images, out_pdf, ocr, engine, langs, progress)
    return f"{used}, {_to_pdfa(out_pdf)}"
