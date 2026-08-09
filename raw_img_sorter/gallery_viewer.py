from collections import deque
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QImage, QImageReader, QPixmap
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from .models import Photo, PhotoState


STATE_COLORS = {
    PhotoState.PENDING: "#f0c75e",
    PhotoState.SELECTED: "#39d353",
    PhotoState.REJECTED: "#ff5c5c",
}


class LoaderSignals(QObject):
    finished = Signal(int, int, int, object, str)


class ThumbnailLoader(QRunnable):
    """Decode one thumbnail away from the GUI thread."""

    def __init__(
        self, index: int, generation: int, quality: int, path: Path, target_size: QSize,
    ) -> None:
        super().__init__()
        self.index = index
        self.generation = generation
        self.quality = quality
        self.path = path
        self.target_size = target_size
        self.signals = LoaderSignals()

    @Slot()
    def run(self) -> None:
        reader = QImageReader(str(self.path))
        reader.setAutoTransform(True)
        if self.quality == 0:
            # Fast preview: ask the JPEG decoder to avoid producing pixels the
            # thumbnail cannot display.
            source_size = reader.size()
            if source_size.isValid():
                source_size.scale(self.target_size, Qt.AspectRatioMode.KeepAspectRatio)
                reader.setScaledSize(source_size)
        image = reader.read()
        if self.quality == 1 and not image.isNull():
            # Refinement pass: decode the source normally, then use Qt's best
            # downsampling filter for the final thumbnail.
            image = image.scaled(
                self.target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.signals.finished.emit(
            self.index,
            self.generation,
            self.quality,
            image,
            reader.errorString() if image.isNull() else "",
        )


class Thumbnail(QFrame):
    clicked = Signal(int)

    def __init__(self, index: int, photo: Photo) -> None:
        super().__init__()
        self.setObjectName("thumbnail")
        self.index = index
        self._image: QImage | None = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)
        image = QLabel("Loading…")
        self.image_label = image
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image.setMinimumSize(64, 64)
        # A decoded pixmap must not change the placeholder's layout size. This
        # keeps the scroll range stable while thumbnails load in phase two.
        image.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        image.setStyleSheet("background: #111;")
        image.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.path = photo.jpg
        name = QLabel(photo.jpg.name)
        name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setWordWrap(True)
        self.status_label = QLabel("PENDING")
        self.status_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-weight: 700;")
        layout.addWidget(image, 1)
        layout.addWidget(name)
        layout.addWidget(self.status_label)
        self.setToolTip(f"Click to focus {photo.jpg.name}. Press Space or K to toggle keep.")

    def set_image(self, image: QImage, error: str) -> None:
        if image.isNull():
            self.image_label.setText(f"Unable to load\n{error}")
        else:
            self._image = image
            self._render_image()

    def _render_image(self) -> None:
        if self._image is not None:
            self.image_label.setPixmap(QPixmap.fromImage(self._image).scaled(
                self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._render_image()

    def set_status(self, state: PhotoState, current: bool) -> None:
        color = STATE_COLORS[state]
        self.status_label.setText(("▶ " if current else "") + state.value.upper())
        self.status_label.setStyleSheet(f"font-weight: 800; color: {color};")
        if state == PhotoState.SELECTED:
            if current:
                self.setStyleSheet(
                    "QFrame#thumbnail { border: 5px solid #8cffaa; "
                    "border-radius: 5px; background: #315c3d; }"
                )
                self.status_label.setStyleSheet("font-weight: 900; color: #b7ffc8;")
            else:
                self.setStyleSheet(
                    "QFrame#thumbnail { border: 3px solid #39d353; "
                    "border-radius: 5px; background: #203a2a; }"
                )
        elif current:
            self.setStyleSheet(
                "QFrame#thumbnail { border: 4px solid #78a9ff; "
                "border-radius: 5px; background: #30394a; }"
            )
        else:
            self.setStyleSheet(
                "QFrame#thumbnail { border: 2px solid #555b66; "
                "border-radius: 5px; background: #202124; }"
            )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(event)


class GalleryViewer(QScrollArea):
    photo_clicked = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setWidget(self.container)
        self.thumbnails: list[Thumbnail] = []
        self._displayed_states: list[PhotoState] = []
        self._current_index = -1
        self.columns = 4
        self._load_queue: deque[int] = deque()
        self._high_quality_queue: deque[int] = deque()
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(2)
        self._active_loaders = 0
        self._generation = 0
        self._load_timer = QTimer(self)
        self._load_timer.setSingleShot(True)
        self._load_timer.timeout.connect(self._start_queued_loaders)
        self._loading_requested = False

    def set_photos(self, photos: list[Photo]) -> None:
        self._load_timer.stop()
        self._generation += 1
        self._active_loaders = 0
        self._loading_requested = False
        self._load_queue.clear()
        self._high_quality_queue.clear()
        for thumbnail in self.thumbnails:
            self.grid.removeWidget(thumbnail)
            thumbnail.deleteLater()
        self.thumbnails = []
        self._displayed_states = []
        self._current_index = -1
        for index, photo in enumerate(photos):
            thumbnail = Thumbnail(index, photo)
            thumbnail.clicked.connect(self.photo_clicked)
            self.thumbnails.append(thumbnail)
            self._load_queue.append(index)
            self._high_quality_queue.append(index)
        # Phase one: install every placeholder and settle the complete layout
        # before any image is decoded into it.
        self._relayout()
        self.grid.activate()
        self.container.adjustSize()

    def start_loading(self) -> None:
        if self._load_queue and not self._loading_requested:
            self._loading_requested = True
            # Let Qt paint the final set of placeholders and establish its
            # scrollbar range before phase two starts.
            self._load_timer.start(50)

    def _start_queued_loaders(self) -> None:
        while self._load_queue and self._active_loaders < 2:
            index = self._load_queue.popleft()
            thumbnail = self.thumbnails[index]
            target_size = thumbnail.image_label.size()
            if not target_size.isValid():
                target_size = QSize(320, 220)
            loader = ThumbnailLoader(index, self._generation, 0, thumbnail.path, target_size)
            loader.signals.finished.connect(self._thumbnail_loaded)
            self._active_loaders += 1
            self._thread_pool.start(loader)
        # High-quality work starts only after every fast preview is available,
        # and runs one image at a time to preserve UI responsiveness.
        if not self._load_queue and self._active_loaders == 0 and self._high_quality_queue:
            index = self._high_quality_queue.popleft()
            thumbnail = self.thumbnails[index]
            target_size = thumbnail.image_label.size()
            if not target_size.isValid():
                target_size = QSize(320, 220)
            loader = ThumbnailLoader(index, self._generation, 1, thumbnail.path, target_size)
            loader.signals.finished.connect(self._thumbnail_loaded)
            self._active_loaders = 1
            self._thread_pool.start(loader)
        elif not self._load_queue and not self._high_quality_queue and self._active_loaders == 0:
            self._loading_requested = False

    @Slot(int, int, int, object, str)
    def _thumbnail_loaded(
        self, index: int, generation: int, quality: int, image: QImage, error: str,
    ) -> None:
        # Results from a folder that has since been replaced are intentionally
        # discarded. Their workers cannot mutate the current panel.
        if generation != self._generation:
            return
        self._active_loaders = max(0, self._active_loaders - 1)
        if 0 <= index < len(self.thumbnails):
            self.thumbnails[index].set_image(image, error)
        if quality == 1 and self._high_quality_queue:
            self._load_timer.start(100)
        else:
            self._start_queued_loaders()

    def set_columns(self, columns: int) -> None:
        self.columns = columns
        self._relayout()

    def _relayout(self) -> None:
        for thumbnail in self.thumbnails:
            self.grid.removeWidget(thumbnail)
        for column in range(10):
            self.grid.setColumnStretch(column, 0)
        for index, thumbnail in enumerate(self.thumbnails):
            self.grid.addWidget(thumbnail, index // self.columns, index % self.columns)
        for column in range(self.columns):
            self.grid.setColumnStretch(column, 1)
        self._size_square_tiles()

    def _size_square_tiles(self) -> None:
        margins = self.grid.contentsMargins()
        spacing = max(0, self.grid.horizontalSpacing())
        available = (
            self.viewport().width()
            - margins.left()
            - margins.right()
            - spacing * (self.columns - 1)
            - 2
        )
        tile_size = max(100, available // self.columns)
        for thumbnail in self.thumbnails:
            thumbnail.setFixedSize(tile_size, tile_size)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._size_square_tiles()

    def update_statuses(self, states: list[PhotoState], current_index: int) -> None:
        if len(self._displayed_states) != len(states):
            changed = set(range(min(len(self.thumbnails), len(states))))
        else:
            changed = {
                index for index, (old, new) in enumerate(zip(self._displayed_states, states))
                if old != new
            }
        if self._current_index >= 0:
            changed.add(self._current_index)
        if current_index >= 0:
            changed.add(current_index)
        for index in changed:
            if 0 <= index < len(self.thumbnails) and index < len(states):
                self.thumbnails[index].set_status(states[index], index == current_index)
        self._displayed_states = list(states)
        self._current_index = current_index
        if 0 <= current_index < len(self.thumbnails):
            self.ensureWidgetVisible(self.thumbnails[current_index], 20, 20)
