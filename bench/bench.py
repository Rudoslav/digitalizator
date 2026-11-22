"""Porovnanie OCR enginov na vzorových stranách.

Použitie:  python bench.py DIR [--engines tesseract,...] [--langs slk+ces+deu+hun]
DIR obsahuje dvojice  strana.jpg + strana.txt  (strana.txt = ručne opravený správny text).
Výstup: chybovosť na znaky (CER) a úspešnosť zachovania diakritiky, za každý engine.
"""
import argparse
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

from rapidfuzz.distance import Levenshtein

IMG_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


# --- enginy: funkcia (Path obrázka, langs) -> text ---
def tesseract(img: Path, langs: str) -> str:
    r = subprocess.run(["tesseract", str(img), "-", "-l", langs], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return r.stdout


ROOT = Path(__file__).resolve().parent.parent


def pero(img: Path, langs: str) -> str:
    """PERO OCR (lokálne, CPU). Beží vo vlastnom prostredí .venv-pero (Python 3.11)."""
    import tempfile
    import xml.etree.ElementTree as ET

    cfgs = sorted((ROOT / "vendor/pero-models-dl/extracted").glob("*/config_cpu.ini"))
    if not cfgs:
        raise RuntimeError("PERO modely nie sú rozbalené vo vendor/pero-models-dl/extracted")
    with tempfile.TemporaryDirectory() as tmp:
        inp, out = Path(tmp) / "in", Path(tmp) / "out"
        inp.mkdir()
        out.mkdir()
        (inp / img.name).symlink_to(img.resolve())
        r = subprocess.run(
            [str(ROOT / ".venv-pero/bin/python"), str(ROOT / "vendor/pero-ocr/user_scripts/parse_folder.py"),
             "-c", str(cfgs[0]), "-i", str(inp), "--output-xml-path", str(out), "--device", "cpu"],
            capture_output=True, text=True)
        xmls = list(out.glob("*.xml"))
        if r.returncode != 0 or not xmls:
            raise RuntimeError(r.stderr[-500:])
        root = ET.parse(xmls[0]).getroot()
        lines = []
        for el in root.iter():
            if el.tag.endswith("}TextLine") or el.tag == "TextLine":
                u = next((e for e in el.iter() if e.tag.endswith("Unicode")), None)
                if u is not None and u.text:
                    lines.append(u.text)
        return "\n".join(lines)


ENGINES = {"tesseract": tesseract, "pero": pero}
# TODO: "paddleocr", "trocr" (len riadky -> treba layout)


# --- metriky ---
def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    return " ".join(s.split())  # zlúčiť whitespace, ignorovať zalomenia riadkov


def is_diacritic_letter(ch: str) -> bool:
    """Písmeno, ktoré sa rozkladá na základ + diakritiku (á, č, ő, ű, ß sa nepočíta...)."""
    return ch.isalpha() and len(unicodedata.normalize("NFD", ch)) > 1


def cer(ref: str, hyp: str) -> float:
    return Levenshtein.distance(ref, hyp) / max(len(ref), 1)


def diacritic_score(ref: str, hyp: str) -> tuple[int, int]:
    """(správne zachované znaky s diakritikou, všetky takéto znaky v referencii)."""
    total = ok = 0
    for op in Levenshtein.opcodes(ref, hyp):
        if op.tag == "equal":
            seg = ref[op.src_start:op.src_end]
            n = sum(1 for c in seg if is_diacritic_letter(c))
            total += n
            ok += n
        else:
            total += sum(1 for c in ref[op.src_start:op.src_end] if is_diacritic_letter(c))
    return ok, total


def nogt_mode(a, pages):
    names = a.engines.split(",")
    texts = {n: [] for n in names}
    times = {n: 0.0 for n in names}
    for n in names:
        for p in pages:
            t0 = time.time()
            texts[n].append(norm(ENGINES[n](p, a.langs)))
            times[n] += time.time() - t0
            if a.save:
                (a.save / f"{p.stem}.{n}.txt").write_text(texts[n][-1], encoding="utf-8")
    print(f"{'engine':<12}{'slov spolu':>12}{'čas/strana s':>15}")
    for n in names:
        print(f"{n:<12}{sum(len(t.split()) for t in texts[n]):>12}{times[n] / len(pages):>15.1f}")
    if len(names) > 1:
        base = names[0]
        print(f"\nNesúhlas voči '{base}' (CER medzi enginmi, %; vyššie = viac sporných miest):")
        for n in names[1:]:
            d = sum(Levenshtein.distance(x, y) for x, y in zip(texts[base], texts[n]))
            l = sum(max(len(x), 1) for x in texts[base])
            print(f"  {n}: {100 * d / l:.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", type=Path)
    ap.add_argument("--engines", default=",".join(ENGINES))
    ap.add_argument("--langs", default="slk+ces+deu+hun")
    ap.add_argument("--save", type=Path, help="priečinok na uloženie rozpoznaných textov")
    ap.add_argument("--nogt", action="store_true",
                    help="bez správneho textu: len počet slov, čas a nesúhlas medzi enginmi (nič sa nevypisuje)")
    ap.add_argument("--limit", type=int, default=0, help="spracovať len prvých N strán")
    a = ap.parse_args()

    pages = sorted(p for p in a.dir.iterdir() if p.suffix.lower() in IMG_EXT
                   and (a.nogt or p.with_suffix(".txt").exists()))
    if a.limit:
        pages = pages[:a.limit]
    if not pages:
        sys.exit("Nenašiel som dvojice obrázok + .txt v " + str(a.dir))
    if a.save:
        a.save.mkdir(parents=True, exist_ok=True)

    print(f"Strán: {len(pages)}, jazyky: {a.langs}\n")
    if a.nogt:
        return nogt_mode(a, pages)
    print(f"{'engine':<12}{'CER %':>8}{'diakritika %':>15}{'čas/strana s':>15}")
    for name in a.engines.split(","):
        fn = ENGINES[name]
        dist = length = d_ok = d_all = 0
        t0 = time.time()
        for p in pages:
            ref = norm(p.with_suffix(".txt").read_text(encoding="utf-8"))
            hyp = norm(fn(p, a.langs))
            if a.save:
                (a.save / f"{p.stem}.{name}.txt").write_text(hyp, encoding="utf-8")
            dist += Levenshtein.distance(ref, hyp)
            length += len(ref)
            ok, tot = diacritic_score(ref, hyp)
            d_ok += ok
            d_all += tot
        dt = (time.time() - t0) / len(pages)
        d = f"{100 * d_ok / d_all:.1f}" if d_all else "-"
        print(f"{name:<12}{100 * dist / max(length, 1):>8.2f}{d:>15}{dt:>15.1f}")


if __name__ == "__main__":
    main()
