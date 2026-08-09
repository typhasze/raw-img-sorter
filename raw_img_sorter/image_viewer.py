from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QImage, QImageReader, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy

from .models import PhotoState


class ImageViewer(QLabel):
    CACHE_LIMIT = 7

    def __init__(self) -> None:
        super().__init__("Open a folder to begin")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(480, 320)
        self.setStyleSheet("background: #111; color: #bbb;")
        self._path: Path | None = None
        self._image: QImage | None = None
        self._cache: OrderedDict[tuple[str, int, int], QImage] = OrderedDict()
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(100)
        self._resize_timer.timeout.connect(self.reload)

    def set_state(self, state: PhotoState) -> None:
        self.setStyleSheet("background: #111; color: #bbb;")

    def show_image(self, path: Path | None) -> None:
        self._path = path
        if path is None:
            self._image = None
            self.clear()
            self.setText("Open a folder to begin")
            return
        self.reload()

    def _target_size(self) -> QSize:
        scale = self.devicePixelRatioF()
        return QSize(max(1, int(self.width() * scale)), max(1, int(self.height() * scale)))

    def reload(self) -> None:
        if self._path is None:
            return
        target = self._target_size()
        key = (str(self._path), target.width() // 128, target.height() // 128)
        image = self._cache.get(key)
        if image is None:
            reader = QImageReader(str(self._path))
            reader.setAutoTransform(True)
            original = reader.size()
            if original.isValid() and (original.width() > target.width() or original.height() > target.height()):
                original.scale(target, Qt.AspectRatioMode.KeepAspectRatio)
                reader.setScaledSize(original)
            image = reader.read()
            if image.isNull():
                self._image = None
                self.setText(f"Unable to load {self._path.name}\n{reader.errorString()}")
                return
            self._cache[key] = image
            self._cache.move_to_end(key)
            while len(self._cache) > self.CACHE_LIMIT:
                self._cache.popitem(last=False)
        else:
            self._cache.move_to_end(key)
        self._image = image
        self._render()

    def _render(self) -> None:
        if self._image is None:
            return
        pixmap = QPixmap.fromImage(self._image)
        pixmap.setDevicePixelRatio(self.devicePixelRatioF())
        self.setPixmap(pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._render()
        self._resize_timer.start()
