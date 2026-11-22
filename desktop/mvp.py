"""MVP: živý náhľad z telefónu, medzerník = fotka do priečinka spisu (0001.jpg, 0002.jpg, …).
Vyžaduje na telefóne appku digitalizator-android a USB ladenie."""
import http.client
import io
import json
import re
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, QSize, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QImage, QImageReader, QPainter, QPen, QPixmap

import pipeline
from PIL import Image, ImageOps
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

PORT = 8765
PKG = "sk.digitalizator.camera"
FRAME_CFG = Path.home() / ".config" / "digitalizator" / "frame.json"
A_RATIO = 2 ** 0.5   # výška/šírka papiera A-série
A4_OF_A3 = 2 ** -0.5  # A4 je lineárne 0,707 × A3


def load_frame_cfg() -> dict:
    """Rám A3 ako podiel náhľadu: stred (cx, cy) a šírka w. A4 sa odvodí z A3."""
    try:
        return {**{"cx": 0.5, "cy": 0.5, "w": 0.9}, **json.loads(FRAME_CFG.read_text())}
    except (OSError, ValueError):
        return {"cx": 0.5, "cy": 0.5, "w": 0.9}


def crop_box(cfg: dict, mode: str, width: int, height: int) -> tuple[int, int, int, int]:
    """Rám (A4/A3) ako pixelový výrez (left, top, right, bottom) fotky, orezaný na hranice fotky."""
    w = cfg["w"] * (A4_OF_A3 if mode == "A4" else 1.0)
    h = w * A_RATIO * width / height
    box = ((cfg["cx"] - w / 2) * width, (cfg["cy"] - h / 2) * height,
           (cfg["cx"] + w / 2) * width, (cfg["cy"] + h / 2) * height)
    l, t, r, b = (round(v) for v in box)
    return max(l, 0), max(t, 0), min(r, width), min(b, height)


def crop_jpeg(data: bytes, cfg: dict, mode: str) -> bytes:
    """Orežie fotku podľa rámu. Znovu sa kóduje (kvalita 95)."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))  # neplatnú orientáciu ignoruje
    l, t, r, b = crop_box(cfg, mode, *img.size)
    out = io.BytesIO()
    img.crop((l, t, r, b)).save(out, "JPEG", quality=95, subsampling=0)
    return out.getvalue()


def adb(*a):
    return subprocess.run(["adb", *a], capture_output=True, text=True, timeout=20)


def connect_phone() -> str | None:
    """Vráti chybovú hlášku alebo None, ak je všetko pripravené."""
    try:
        devs = [l for l in adb("devices").stdout.splitlines()[1:] if l.endswith("\tdevice")]
    except (OSError, subprocess.TimeoutExpired):
        return "Nenašiel som program adb."
    if not devs:
        return "Telefón nie je pripojený. Pripojte USB kábel a povoľte ladenie."
    adb("forward", f"tcp:{PORT}", f"tcp:{PORT}")
    adb("shell", "am", "start", "-n", f"{PKG}/.MainActivity")
    return None


class Feed(QThread):
    frame = pyqtSignal(QImage)
    lost = pyqtSignal()

    def run(self):
        while not self.isInterruptionRequested():
            try:
                c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=5)
                c.request("GET", "/preview")
                r = c.getresponse()
                buf = b""
                while not self.isInterruptionRequested():
                    chunk = r.read1(65536)
                    if not chunk:
                        break
                    buf += chunk
                    a, b = buf.find(b"\xff\xd8"), buf.find(b"\xff\xd9")
                    while a != -1 and b != -1 and b > a:
                        img = QImage.fromData(buf[a:b + 2], "JPG")
                        if not img.isNull():
                            self.frame.emit(img)
                        buf = buf[b + 2:]
                        a, b = buf.find(b"\xff\xd8"), buf.find(b"\xff\xd9")
            except (OSError, http.client.HTTPException):
                pass
            self.lost.emit()
            self.msleep(1000)


class PdfJob(QThread):
    done = pyqtSignal(str)
    failed = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, images, out, engine):
        super().__init__()
        self.images, self.out, self.engine = images, out, engine

    def run(self):
        try:
            used = pipeline.build_pdf(self.images, self.out, engine=self.engine,
                                      progress=lambda d, t: self.progress.emit(int(100 * d / t)))
            self.done.emit(f"{self.out}  (OCR: {used})")
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


class Shot(QThread):
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, path: Path, crop=None):
        super().__init__()
        self.path = path
        self.crop = crop  # (cfg, mode) alebo None

    def run(self):
        try:
            c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30)
            c.request("GET", "/capture")
            r = c.getresponse()
            data = r.read()
            if r.status != 200:
                raise RuntimeError(f"telefón vrátil chybu {r.status}")
            if self.crop:
                data = crop_jpeg(data, *self.crop)
            self.path.write_bytes(data)
            self.done.emit(self.path.name)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


def next_number(folder: Path) -> int:
    nums = [int(m.group(1)) for p in folder.glob("*.jpg") if (m := re.fullmatch(r"(\d+)", p.stem))]
    return max(nums, default=0) + 1


class Window(QWidget):
    def __init__(self, folder: Path):
        super().__init__()
        self.setWindowTitle(f"Digitalizátor – {folder.name}")
        self.folder, self.n, self.busy = folder, next_number(folder), False
        self.view = QLabel("Čakám na telefón…")
        self.view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view.setMinimumSize(640, 480)
        self.view.setStyleSheet("background:#222;color:#ccc;font-size:22px;")
        self.status = QLabel()
        self.status.setStyleSheet("font-size:18px;padding:6px;")
        self.pages = QListWidget()
        self.pages.setIconSize(QSize(150, 200))
        self.pages.setFixedWidth(200)
        self.pages.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # nech medzerník ide vždy do okna
        self.pages.itemClicked.connect(self.show_page)
        for p in sorted(folder.glob("*.jpg")):
            self.add_thumb(p)

        self.paused, self.shown, self.shown_item = False, None, None
        self.btn_resume = self.top_button("Pokračovať", self.resume)
        self.btn_resume.setStyleSheet("font-size:20px;padding:10px 24px;background:#2e7d32;color:white;")
        self.btn_resume.hide()
        self.btn_full = self.top_button("Celá obrazovka (F11)", self.toggle_fullscreen)
        self.cfg, self.mode = load_frame_cfg(), "A4"
        self.mode_btns = {m: self.top_button(label, lambda _=False, m=m: self.set_mode(m))
                          for m, label in (("A4", "Rám A4"), ("A3", "Rám A3"), (None, "Bez rámu"))}
        self.set_mode(self.mode)
        top = QHBoxLayout()
        for b in self.mode_btns.values():
            top.addWidget(b)
        top.addStretch(1)
        self.btn_pdf = self.top_button("Vytvoriť PDF", self.make_pdf)
        self.btn_pdf.setStyleSheet("font-size:18px;padding:10px 20px;background:#6a1b9a;color:white;")
        self.pdf_job = None
        self.engine = QComboBox()
        self.engine.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # medzerník nesmie meniť výber
        self.engine.setStyleSheet("font-size:16px;padding:8px;")
        if pipeline.pero_available():
            self.engine.addItem("OCR: PERO (odporúčané)", "pero")
        self.engine.addItem("OCR: Tesseract", "tesseract")
        top.addWidget(self.engine)
        self.chk_crop = QCheckBox("Orezať pri fotení podľa rámu")
        self.chk_crop.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.chk_crop.setStyleSheet("font-size:16px;")
        self.chk_crop.setChecked(True)
        top.addWidget(self.chk_crop)
        top.addWidget(self.btn_pdf)
        top.addWidget(self.btn_resume)
        top.addWidget(self.btn_full)

        right = QVBoxLayout()
        right.addLayout(top)
        right.addWidget(self.view, 1)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setStyleSheet("font-size:16px;")
        self.bar.hide()
        right.addWidget(self.bar)
        right.addWidget(self.status)
        lay = QHBoxLayout(self)
        lay.addWidget(self.pages)
        lay.addLayout(right, 1)
        self.say()
        self.feed = Feed()
        self.feed.frame.connect(self.on_frame)
        self.feed.lost.connect(lambda: self.view.setText("Čakám na telefón…"))
        self.feed.start()

    def add_thumb(self, path: Path):
        r = QImageReader(str(path))
        r.setAutoTransform(True)
        size = r.size()
        if size.isValid():
            r.setScaledSize(size.scaled(300, 400, Qt.AspectRatioMode.KeepAspectRatio))
        item = QListWidgetItem(QIcon(QPixmap.fromImage(r.read())), path.stem)
        item.setData(Qt.ItemDataRole.UserRole, str(path))
        self.pages.addItem(item)
        self.pages.scrollToItem(item)

    @staticmethod
    def top_button(text, slot):
        b = QPushButton(text)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # medzerník nesmie stláčať tlačidlá
        b.setStyleSheet("font-size:16px;padding:10px 16px;")
        b.clicked.connect(slot)
        return b

    def show_pixmap(self, pm: QPixmap, overlay: bool = False):
        pm = pm.scaled(self.view.size(), Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
        if overlay and self.mode:
            p = QPainter(pm)
            pen = QPen(QColor("#00e676"), 3, Qt.PenStyle.DashLine)
            p.setPen(pen)
            w = self.cfg["w"] * (A4_OF_A3 if self.mode == "A4" else 1.0) * pm.width()
            h = w * A_RATIO
            r = QRectF(self.cfg["cx"] * pm.width() - w / 2, self.cfg["cy"] * pm.height() - h / 2, w, h)
            p.drawRect(r)
            p.drawText(QPointF(r.left() + 6, r.top() + 22), self.mode)
            p.end()
        self.view.setPixmap(pm)

    def set_mode(self, mode):
        self.mode = mode
        for m, b in self.mode_btns.items():
            on = m == mode
            b.setStyleSheet("font-size:16px;padding:10px 16px;" +
                            ("background:#1565c0;color:white;" if on else ""))

    def tune_frame(self, dx=0.0, dy=0.0, dw=0.0):
        """Ctrl+šípky = posun rámu, Ctrl +/- = veľkosť (nastavenie robí admin, ukladá sa)."""
        c = self.cfg
        c["cx"] = min(max(c["cx"] + dx, 0.0), 1.0)
        c["cy"] = min(max(c["cy"] + dy, 0.0), 1.0)
        c["w"] = min(max(c["w"] + dw, 0.2), 1.5)
        FRAME_CFG.parent.mkdir(parents=True, exist_ok=True)
        FRAME_CFG.write_text(json.dumps(c))

    def show_page(self, item: QListWidgetItem):
        """Klik na náhľad: preruší živý náhľad a ukáže uloženú fotku."""
        r = QImageReader(item.data(Qt.ItemDataRole.UserRole))
        r.setAutoTransform(True)
        size = r.size()
        if size.isValid():
            r.setScaledSize(size.scaled(1600, 1600, Qt.AspectRatioMode.KeepAspectRatio))
        self.shown = QPixmap.fromImage(r.read())
        self.shown_item = item
        self.paused = True
        self.btn_resume.show()
        self.show_pixmap(self.shown)
        self.say(f"Strana {item.text()} (náhľad pozastavený)")

    def delete_selected(self):
        """Delete: zmaže označenú stranu zo zoznamu aj z disku (po potvrdení)."""
        item = self.shown_item  # strana, ktorú práve vidno
        if item is None:
            return
        path = Path(item.data(Qt.ItemDataRole.UserRole))
        box = QMessageBox(QMessageBox.Icon.Warning, "Zmazať stranu",
                          f"Naozaj zmazať stranu {item.text()}? Fotka sa zmaže aj z disku.", parent=self)
        yes = box.addButton("Zmazať", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Zrušiť", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(yes)
        box.exec()
        if box.clickedButton() is not yes:
            return
        try:
            path.unlink()
        except OSError as e:
            self.say(f"Fotku sa nepodarilo zmazať: {e}")
            return
        self.pages.takeItem(self.pages.row(item))
        self.n = next_number(self.folder)  # číslovanie nadväzuje na najvyššie existujúce
        self.resume()
        self.say(f"Zmazané: {path.name}")

    def resume(self):
        self.paused, self.shown, self.shown_item = False, None, None
        self.pages.clearSelection()
        self.pages.setCurrentItem(None)
        self.btn_resume.hide()
        self.say()

    def make_pdf(self):
        """Zloží všetky fotky v priečinku spisu (podľa čísla) do <spis>.pdf a spraví OCR."""
        images = sorted(self.folder.glob("[0-9]*.jpg"))
        if not images:
            self.say("Najprv odfoťte aspoň jednu stranu.")
            return
        if self.pdf_job is not None:
            return
        out = self.folder / f"{self.folder.name}.pdf"
        self.btn_pdf.setEnabled(False)
        self.say(f"Vytváram PDF z {len(images)} strán a rozpoznávam text… môže to trvať.")
        self.pdf_msg = "PDF sa nepodarilo vytvoriť."
        self.pdf_job = PdfJob(images, out, self.engine.currentData())
        self.engine.setEnabled(False)
        self.pdf_job.done.connect(lambda p: setattr(self, "pdf_msg", f"Hotovo: {p}"))
        self.pdf_job.failed.connect(lambda m: setattr(self, "pdf_msg", f"PDF sa nepodarilo vytvoriť: {m}"))
        self.bar.setValue(0)
        self.bar.show()
        self.pdf_job.progress.connect(self.bar.setValue)
        # vlákno sa smie zahodiť až po skutočnom skončení (signál finished), inak appka spadne
        self.pdf_job.finished.connect(self.pdf_finished)
        self.pdf_job.start()

    def pdf_finished(self):
        self.pdf_job = None
        self.bar.hide()
        self.engine.setEnabled(True)
        self.btn_pdf.setEnabled(True)
        self.say(self.pdf_msg)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.paused and self.shown is not None:
            self.show_pixmap(self.shown)

    def say(self, extra=""):
        self.status.setText(f"Medzerník = odfotiť.  Ďalšia strana: {self.n}.  {extra}")

    def on_frame(self, img: QImage):
        if not self.paused:
            self.show_pixmap(QPixmap.fromImage(img), overlay=True)

    def keyPressEvent(self, e):
        ctrl = bool(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
        step = {Qt.Key.Key_Left: (-0.005, 0, 0), Qt.Key.Key_Right: (0.005, 0, 0),
                Qt.Key.Key_Up: (0, -0.005, 0), Qt.Key.Key_Down: (0, 0.005, 0),
                Qt.Key.Key_Plus: (0, 0, 0.01), Qt.Key.Key_Equal: (0, 0, 0.01),
                Qt.Key.Key_Minus: (0, 0, -0.01)}
        if ctrl and e.key() in step:
            self.tune_frame(*step[e.key()])
        elif e.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        elif e.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showNormal()
        elif e.key() == Qt.Key.Key_Delete and self.paused:
            self.delete_selected()
        elif e.key() == Qt.Key.Key_Space and self.paused:
            self.say("Najprv kliknite na Pokračovať.")
        elif e.key() == Qt.Key.Key_Space and not e.isAutoRepeat() and not self.busy:
            self.busy = True
            self.say("Fotím…")
            crop = (dict(self.cfg), self.mode) if self.chk_crop.isChecked() and self.mode else None
            self.shot = Shot(self.folder / f"{self.n:04d}.jpg", crop)
            self.shot.done.connect(self.shot_ok)
            self.shot.failed.connect(self.shot_fail)
            self.shot.start()

    def shot_ok(self, name):
        self.add_thumb(self.folder / name)
        self.n += 1
        self.busy = False
        self.say(f"Uložené: {name}" + (" (orezané podľa rámu)" if self.chk_crop.isChecked() and self.mode else ""))

    def shot_fail(self, msg):
        self.busy = False
        self.say(f"Fotenie zlyhalo: {msg}")

    def closeEvent(self, e):
        self.feed.requestInterruption()
        self.feed.wait(2000)
        super().closeEvent(e)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    err = connect_phone()
    if err:
        QMessageBox.warning(None, "Digitalizátor", err)
        sys.exit(1)
    folder = QFileDialog.getExistingDirectory(None, "Vyberte alebo vytvorte priečinok spisu")
    if not folder:
        sys.exit(0)
    w = Window(Path(folder))
    w.resize(1000, 800)
    w.show()
    sys.exit(app.exec())
