"""Dočasný zdroj fotiek: sleduje DCIM/Camera na telefóne cez adb a sťahuje nové fotky.
Do času, kým bude vlastná Android appka. Rozhranie (poll -> nové súbory) ostane rovnaké."""
import subprocess
import time
from pathlib import Path

DCIM = "/sdcard/DCIM/Camera"


def _adb(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(["adb", *args], capture_output=True, text=True, timeout=timeout)


def device_connected() -> bool:
    try:
        out = _adb("devices").stdout.splitlines()[1:]
    except (OSError, subprocess.TimeoutExpired):
        return False
    return any(line.strip().endswith("\tdevice") for line in out)


def _list_photos() -> dict[str, int]:
    out = _adb("shell", f"ls -l {DCIM}").stdout
    files = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 8 and parts[-1].lower().endswith((".jpg", ".jpeg")):
            files[parts[-1]] = int(parts[4])
    return files


class PhoneWatcher:
    def __init__(self, dest: Path):
        self.dest = dest
        dest.mkdir(parents=True, exist_ok=True)
        self.seen = set(_list_photos())  # existujúce fotky ignorujeme

    def poll(self) -> list[Path]:
        """Vráti stiahnuté nové fotky (zoradené podľa mena = podľa času)."""
        new = []
        current = _list_photos()
        for name in sorted(set(current) - self.seen):
            time.sleep(0.4)  # počkať, kým sa súbor dopíše
            if _list_photos().get(name) != current[name]:
                continue  # ešte sa zapisuje, skúsime pri ďalšom pollingu
            target = self.dest / name
            if _adb("pull", f"{DCIM}/{name}", str(target), timeout=120).returncode == 0:
                self.seen.add(name)
                new.append(target)
        return new
