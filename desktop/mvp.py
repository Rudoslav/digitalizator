"""MVP: živý náhľad z telefónu, medzerník = fotka do priečinka spisu (0001.jpg, 0002.jpg, …).
Vyžaduje na telefóne appku digitalizator-android a USB ladenie."""
import http.client
import re
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QSize, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QImage, QImageReader, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

PORT = 8765
PKG = "sk.digitalizator.camera"


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


class Shot(QThread):
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, path: Path):
        super().__init__()
        self.path = path

    def run(self):
        try:
            c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30)
            c.request("GET", "/capture")
            r = c.getresponse()
            data = r.read()
            if r.status != 200:
                raise RuntimeError(f"telefón vrátil chybu {r.status}")
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

        self.paused, self.shown = False, None
        self.btn_resume = self.top_button("Pokračovať", self.resume)
        self.btn_resume.setStyleSheet("font-size:20px;padding:10px 24px;background:#2e7d32;color:white;")
        self.btn_resume.hide()
        self.btn_full = self.top_button("Celá obrazovka (F11)", self.toggle_fullscreen)
        top = QHBoxLayout()
        top.addStretch(1)
        top.addWidget(self.btn_resume)
        top.addWidget(self.btn_full)

        right = QVBoxLayout()
        right.addLayout(top)
        right.addWidget(self.view, 1)
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

    def show_pixmap(self, pm: QPixmap):
        self.view.setPixmap(pm.scaled(
            self.view.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def show_page(self, item: QListWidgetItem):
        """Klik na náhľad: preruší živý náhľad a ukáže uloženú fotku."""
        r = QImageReader(item.data(Qt.ItemDataRole.UserRole))
        r.setAutoTransform(True)
        size = r.size()
        if size.isValid():
            r.setScaledSize(size.scaled(1600, 1600, Qt.AspectRatioMode.KeepAspectRatio))
        self.shown = QPixmap.fromImage(r.read())
        self.paused = True
        self.btn_resume.show()
        self.show_pixmap(self.shown)
        self.say(f"Strana {item.text()} (náhľad pozastavený)")

    def resume(self):
        self.paused, self.shown = False, None
        self.pages.clearSelection()
        self.pages.setCurrentItem(None)
        self.btn_resume.hide()
        self.say()

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
            self.show_pixmap(QPixmap.fromImage(img))

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        elif e.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showNormal()
        elif e.key() == Qt.Key.Key_Space and self.paused:
            self.say("Najprv kliknite na Pokračovať.")
        elif e.key() == Qt.Key.Key_Space and not e.isAutoRepeat() and not self.busy:
            self.busy = True
            self.say("Fotím…")
            self.shot = Shot(self.folder / f"{self.n:04d}.jpg")
            self.shot.done.connect(self.shot_ok)
            self.shot.failed.connect(self.shot_fail)
            self.shot.start()

    def shot_ok(self, name):
        self.add_thumb(self.folder / name)
        self.n += 1
        self.busy = False
        self.say(f"Uložené: {name}")

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
