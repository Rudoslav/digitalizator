"""Hľadanie externých programov (Tesseract, Ghostscript, adb): najprv pribalené vedľa appky
(`tools/` v inštalácii pre Windows), inak v PATH (Linux, vývoj)."""
import os
import shutil
import subprocess
import sys
from pathlib import Path


def app_dir() -> Path:
    """Priečinok appky: pri zabalenej appke vedľa .exe, pri vývoji koreň repa."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    """Priečinok s dátami appky (fonty): pri zabalenej appke rozbalené zdroje, inak desktop/."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


TOOLS = app_dir() / "tools"
# Na Windows nech vedľajšie programy neotvárajú čierne okná
NOWIN = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def _first(paths) -> str | None:
    for p in paths:
        if Path(p).exists():
            return str(p)
    return None


def tesseract() -> str:
    return _first([TOOLS / "tesseract" / "tesseract.exe"]) or shutil.which("tesseract") or "tesseract"


def tessdata_env() -> dict:
    d = TOOLS / "tesseract" / "tessdata"
    return {"TESSDATA_PREFIX": str(d)} if d.exists() else {}


def gs() -> str | None:
    bundled = sorted((TOOLS / "gs").glob("*/bin/gswin64c.exe")) + sorted((TOOLS / "gs").glob("bin/gswin64c.exe"))
    return _first(bundled) or shutil.which("gs") or shutil.which("gswin64c") or shutil.which("gswin32c")


def adb() -> str:
    return _first([TOOLS / "adb" / "adb.exe"]) or shutil.which("adb") or "adb"
