"""Digitalizátor – prototyp desktopovej appky (Qt)."""
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QImageReader, QKeySequence, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

import phone
import pipeline

WORK = Path(__file__).resolve().parent.parent / "work"
ROLE_PATH = Qt.ItemDataRole.UserRole


def load_pixmap(path: Path, max_side: int) -> QPixmap:
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)  # EXIF orientácia
    size = reader.size()
    if size.isValid():
        reader.setScaledSize(size.scaled(max_side, max_side, Qt.AspectRatioMode.KeepAspectRatio))
    return QPixmap.fromImage(reader.read())


class SaveWorker(QThread):
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, images, out):
        super().__init__()
        self.images, self.out = images, out

    def run(self):
        try:
            pipeline.build_pdf(self.images, self.out)
            self.done.emit(str(self.out))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Digitalizátor")
        self.resize(1200, 800)
        self.watcher = None
        self.worker = None

        self.preview = QLabel("Zatiaľ žiadne strany.\nOdfoťte stranu telefónom.")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(500, 400)
        self.preview.setStyleSheet("background:#222;color:#ccc;font-size:20px;")

        self.pages = QListWidget()
        self.pages.setViewMode(QListWidget.ViewMode.IconMode)
        self.pages.setIconSize(QSize(120, 160))
        self.pages.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.pages.setMovement(QListWidget.Movement.Static)
        self.pages.setMaximumWidth(330)
        self.pages.currentItemChanged.connect(self.show_current)

        self.status = QLabel("")
        self.status.setStyleSheet("font-size:16px;padding:6px;")

        btn_add = self.big_button("Pridať fotky zo súboru", self.add_files)
        btn_up = self.big_button("↑ Posunúť hore", lambda: self.move(-1))
        btn_down = self.big_button("↓ Posunúť dole", lambda: self.move(1))
        btn_del = self.big_button("Zmazať stranu", self.delete_current)
        self.btn_save = self.big_button("Uložiť PDF", self.save_pdf)
        self.btn_save.setStyleSheet("font-size:22px;padding:16px;background:#2e7d32;color:white;")

        side = QVBoxLayout()
        side.addWidget(self.pages, 1)
        for b in (btn_up, btn_down, btn_del, btn_add, self.btn_save):
            side.addWidget(b)
        main = QHBoxLayout()
        main.addWidget(self.preview, 1)
        main.addLayout(side)
        root = QVBoxLayout()
        root.addLayout(main, 1)
        root.addWidget(self.status)
        central = QWidget()
        central.setLayout(root)
        self.setCentralWidget(central)

        QShortcut(QKeySequence(Qt.Key.Key_Delete), self, self.delete_current)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_phone)
        self.timer.start(1500)
        self.update_status()

    @staticmethod
    def big_button(text, slot):
        b = QPushButton(text)
        b.setStyleSheet("font-size:18px;padding:12px;")
        b.clicked.connect(slot)
        return b

    # --- strany ---
    def add_page(self, path: Path):
        item = QListWidgetItem(QIcon(load_pixmap(path, 240)), "")
        item.setData(ROLE_PATH, str(path))
        self.pages.addItem(item)
        self.renumber()
        self.pages.setCurrentItem(item)
        self.update_status()

    def renumber(self):
        for i in range(self.pages.count()):
            self.pages.item(i).setText(f"Strana {i + 1}")

    def paths(self) -> list[Path]:
        return [Path(self.pages.item(i).data(ROLE_PATH)) for i in range(self.pages.count())]

    def show_current(self, item, _prev=None):
        if item is None:
            self.preview.setPixmap(QPixmap())
            self.preview.setText("Zatiaľ žiadne strany.\nOdfoťte stranu telefónom.")
            return
        pm = load_pixmap(Path(item.data(ROLE_PATH)), 1600)
        self.preview.setPixmap(pm.scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.show_current(self.pages.currentItem())

    def delete_current(self):
        row = self.pages.currentRow()
        if row < 0:
            return
        self.pages.takeItem(row)
        self.renumber()
        self.update_status()

    def move(self, delta):
        row = self.pages.currentRow()
        new = row + delta
        if row < 0 or not 0 <= new < self.pages.count():
            return
        item = self.pages.takeItem(row)
        self.pages.insertItem(new, item)
        self.pages.setCurrentItem(item)
        self.renumber()

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Vyberte fotky", "", "Obrázky (*.jpg *.jpeg *.png)")
        for f in files:
            self.add_page(Path(f))

    # --- telefón ---
    def poll_phone(self):
        if self.worker is not None:
            return
        if not phone.device_connected():
            self.watcher = None
            self.update_status()
            return
        if self.watcher is None:
            self.watcher = phone.PhoneWatcher(WORK / datetime.now().strftime("%Y%m%d_%H%M%S"))
            self.update_status()
        for p in self.watcher.poll():
            self.add_page(p)

    # --- uloženie ---
    def save_pdf(self):
        images = self.paths()
        if not images:
            QMessageBox.information(self, "Digitalizátor", "Najprv odfoťte aspoň jednu stranu.")
            return
        default = str(Path.home() / "Documents" / f"sken_{datetime.now():%Y%m%d_%H%M}.pdf")
        out, _ = QFileDialog.getSaveFileName(self, "Uložiť PDF", default, "PDF (*.pdf)")
        if not out:
            return
        self.btn_save.setEnabled(False)
        self.status.setText("Ukladám a rozpoznávam text… môže to chvíľu trvať.")
        self.worker = SaveWorker(images, Path(out))
        self.worker.done.connect(self.save_done)
        self.worker.failed.connect(self.save_failed)
        self.worker.start()

    def save_done(self, out):
        self.worker = None
        self.btn_save.setEnabled(True)
        self.status.setText(f"Hotovo: {out}")

    def save_failed(self, msg):
        self.worker = None
        self.btn_save.setEnabled(True)
        self.status.setText("Uloženie sa nepodarilo.")
        QMessageBox.warning(self, "Digitalizátor", f"Uloženie sa nepodarilo.\n\n{msg}")

    def update_status(self):
        n = self.pages.count()
        ph = "Telefón pripojený." if self.watcher else "Telefón nie je pripojený."
        self.status.setText(f"{ph}  Strán: {n}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Main()
    w.show()
    sys.exit(app.exec())
