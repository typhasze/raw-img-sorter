from pathlib import Path

from PySide6.QtCore import QThread, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QAbstractSpinBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QProgressDialog, QPushButton, QSizePolicy, QSpinBox,
    QStackedWidget, QVBoxLayout, QWidget,
)

from .exporter import ExportResult, ExportWorker
from .gallery_viewer import GalleryViewer
from .image_metadata import describe_image
from .image_viewer import ImageViewer
from .models import Photo, PhotoState
from .photo_manager import scan_folder
from .session_manager import SessionManager


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RAW IMG Sorter")
        self.resize(1200, 800)
        self.photos: list[Photo] = []
        self.states: list[PhotoState] = []
        self.index = 0
        self.source: Path | None = None
        self.sessions = SessionManager()
        self.export_thread: QThread | None = None
        self.export_worker: ExportWorker | None = None
        self._build_ui()
        self._build_actions()
        last = self.sessions.last_source()
        if last:
            self.load_folder(last)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("appRoot")
        asset_path = (Path(__file__).parent / "assets").as_posix()
        root.setStyleSheet(
            "QWidget#appRoot { background: #191b1f; }"
            "QToolTip { background: #f2f3f5; color: #202124; border: 1px solid #8b9099; "
            "padding: 5px; }"
            "QPushButton { background: #343840; border: 1px solid #4a505b; "
            "border-radius: 5px; padding: 7px 13px; font-weight: 600; }"
            "QPushButton:hover { background: #414751; border-color: #6d7685; }"
            "QPushButton:pressed { background: #292d33; }"
            "QPushButton#exportButton { background: #287a43; border-color: #39a85d; }"
            "QPushButton#exportButton:hover { background: #329452; }"
            "QComboBox, QSpinBox { background: #292c32; border: 1px solid #4a505b; "
            "border-radius: 5px; padding: 5px 32px 5px 9px; min-height: 22px; }"
            "QComboBox:hover, QSpinBox:hover { border-color: #78a9ff; }"
            "QComboBox::drop-down { subcontrol-origin: border; subcontrol-position: top right; "
            "width: 28px; background: #3b4049; border-left: 1px solid #555c68; "
            "border-top-right-radius: 4px; border-bottom-right-radius: 4px; }"
            "QComboBox::drop-down:hover { background: #4a5260; }"
            f"QComboBox::down-arrow {{ image: url({asset_path}/arrow-down.svg); "
            "width: 12px; height: 8px; }"
            "QSpinBox { padding-right: 28px; }"
            "QSpinBox::up-button, QSpinBox::down-button { subcontrol-origin: border; "
            "width: 24px; background: #3b4049; border-left: 1px solid #555c68; }"
            "QSpinBox::up-button { subcontrol-position: top right; "
            "border-top-right-radius: 4px; border-bottom: 1px solid #555c68; }"
            "QSpinBox::down-button { subcontrol-position: bottom right; "
            "border-bottom-right-radius: 4px; }"
            "QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #4a5260; }"
            f"QSpinBox::up-arrow {{ image: url({asset_path}/arrow-up.svg); "
            "width: 12px; height: 8px; }"
            f"QSpinBox::down-arrow {{ image: url({asset_path}/arrow-down.svg); "
            "width: 12px; height: 8px; }"
            "QLabel#statusChip { background: #292c32; border: 1px solid #40454f; "
            "border-radius: 5px; padding: 6px 10px; }"
        )
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        source_caption = QLabel("SOURCE FOLDER")
        source_caption.setStyleSheet(
            "color: #8f96a3; font-size: 10px; font-weight: 800; letter-spacing: 1px;"
        )
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.folder_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.folder_label.setToolTip("The camera folder currently being reviewed.")
        self.folder_label.setStyleSheet(
            "background: #24272d; color: #dce1e8; border: 1px solid #383d46; "
            "border-radius: 5px; padding: 7px 10px; font-weight: 600;"
        )
        toolbar.addWidget(source_caption)
        toolbar.addWidget(self.folder_label, 1)
        toolbar.addSpacing(8)
        view_caption = QLabel("VIEW MODE")
        view_caption.setStyleSheet(
            "color: #8f96a3; font-size: 10px; font-weight: 800; letter-spacing: 1px;"
        )
        toolbar.addWidget(view_caption)
        self.view_selector = QComboBox()
        self.view_selector.addItems(["Single photo", "Image panel"])
        self.view_selector.setMinimumWidth(140)
        self.view_selector.setToolTip("Switch between one large photo and a resizable thumbnail panel.")
        self.view_selector.currentIndexChanged.connect(self._change_view)
        toolbar.addWidget(self.view_selector)
        self.columns_label = QLabel("Images per row:")
        self.columns_spin = QSpinBox()
        self.columns_spin.setRange(2, 10)
        self.columns_spin.setValue(4)
        self.columns_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        self.columns_spin.setMinimumWidth(72)
        self.columns_spin.setToolTip("Change how many images appear in each row of the image panel.")
        self.columns_spin.valueChanged.connect(self._set_gallery_columns)
        toolbar.addWidget(self.columns_label)
        toolbar.addWidget(self.columns_spin)
        layout.addLayout(toolbar)

        top = QHBoxLayout()
        self.name_label = QLabel("No folder selected")
        self.name_label.setStyleSheet("font-size: 16px; font-weight: 600;")
        self.state_label = QLabel("")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        top.addWidget(self.name_label, 1)
        top.addWidget(self.state_label)

        shortcut_legend = QLabel(
            "Toggle keep: Space / K    •    Next: Right / D    •    Previous: Left / A"
            "    •    Export: E    •    Open folder: Ctrl+O"
        )
        shortcut_legend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shortcut_legend.setWordWrap(True)
        shortcut_legend.setStyleSheet(
            "QLabel { background: #2b2d31; color: #d7dae0; border-radius: 4px; "
            "padding: 6px 10px; font-size: 12px; }"
        )
        shortcut_legend.setToolTip(
            "In the image panel, click a thumbnail to focus it, then press Space or K to toggle keep."
        )
        layout.addWidget(shortcut_legend)

        self.metadata_label = QLabel("Metadata: open a photo folder to begin")
        self.metadata_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.metadata_label.setWordWrap(True)
        self.metadata_label.setStyleSheet(
            "QLabel { background: #202329; color: #c8ccd4; border: 1px solid #30353d; "
            "border-radius: 4px; padding: 5px 8px; font-size: 12px; }"
        )
        layout.addWidget(self.metadata_label)

        self.view_stack = QStackedWidget()
        self.viewer = ImageViewer()
        self.viewer.setToolTip("Space/K: toggle keep  •  Right/D: next  •  Left/A: previous")
        self.gallery = GalleryViewer()
        self.gallery.photo_clicked.connect(self.focus_photo)
        self.view_stack.addWidget(self.viewer)
        self.view_stack.addWidget(self.gallery)
        layout.addWidget(self.view_stack, 1)
        layout.addLayout(top)
        bottom = QHBoxLayout()
        self.raw_label = QLabel("")
        self.count_label = QLabel("Selected: 0")
        self.position_label = QLabel("Photo: 0 / 0")
        for widget in (self.raw_label, self.count_label, self.position_label):
            widget.setObjectName("statusChip")
            bottom.addWidget(widget)
        bottom.addStretch()
        open_button = QPushButton("Open Folder")
        open_button.setToolTip("Choose a folder containing JPG and CR3 files (Ctrl+O).")
        open_button.clicked.connect(self.open_folder)
        export_button = QPushButton("Export Selected")
        export_button.setObjectName("exportButton")
        export_button.setToolTip("Copy selected JPG and matching RAW files to an export folder (E).")
        export_button.clicked.connect(self.export_selected)
        bottom.addWidget(open_button)
        bottom.addWidget(export_button)
        layout.addLayout(bottom)
        self.setCentralWidget(root)
        self._change_view(0)

    def _change_view(self, index: int) -> None:
        self.view_stack.setCurrentIndex(index)
        visible = index == 1
        self.columns_label.setVisible(visible)
        self.columns_spin.setVisible(visible)
        if visible and self.photos:
            self.gallery.update_statuses(self.states, self.index)
            self.gallery.start_loading()
        elif self.photos:
            self.viewer.show_image(self.photos[self.index].jpg)
        if self.photos:
            self._update_state_styling(self.states[self.index])

    def _update_state_styling(self, state: PhotoState) -> None:
        colors = {
            PhotoState.PENDING: ("#f0c75e", "#3b3522"),
            PhotoState.SELECTED: ("#39d353", "#203a2a"),
            PhotoState.REJECTED: ("#ff5c5c", "#412626"),
        }
        color, background = colors[state]
        if self.view_stack.currentIndex() == 0:
            self.name_label.setStyleSheet(
                f"font-size: 16px; font-weight: 600; padding: 8px; "
                f"border-left: 6px solid {color}; border-radius: 4px; "
                f"background: {background};"
            )
            self.state_label.setStyleSheet(
                f"font-size: 16px; font-weight: 800; color: {color}; "
                f"background: {background}; border: 2px solid {color}; "
                "border-radius: 5px; padding: 6px 12px;"
            )
        else:
            self.name_label.setStyleSheet("font-size: 16px; font-weight: 600;")
            self.state_label.setStyleSheet(
                f"font-size: 16px; font-weight: 700; color: {color};"
            )

    def _set_gallery_columns(self, columns: int) -> None:
        self.gallery.set_columns(columns)

    def _add_shortcut(self, text: str, shortcuts: list[str], callback) -> None:
        action = QAction(text, self)
        action.setShortcuts([QKeySequence(key) for key in shortcuts])
        action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        action.triggered.connect(callback)
        self.addAction(action)

    def _build_actions(self) -> None:
        self._add_shortcut("Toggle keep", ["Space", "K"], self.keep)
        self._add_shortcut("Next", ["Right", "D"], self.next_photo)
        self._add_shortcut("Previous", ["Left", "A"], self.previous_photo)
        self._add_shortcut("Export", ["E"], self.export_selected)
        self._add_shortcut("Open", ["Ctrl+O"], self.open_folder)

    def open_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Select Camera Folder", str(self.source or Path.home()))
        if chosen:
            self.load_folder(Path(chosen))

    def load_folder(self, folder: Path) -> None:
        try:
            photos = scan_folder(folder)
        except OSError as error:
            QMessageBox.critical(self, "Could not open folder", str(error))
            return
        if not photos:
            QMessageBox.information(self, "No JPG files", "This folder contains no JPG or JPEG files.")
            return
        self.source, self.photos = folder.resolve(), photos
        self.folder_label.setText(str(self.source))
        self.folder_label.setToolTip(str(self.source))
        self.setWindowTitle(f"RAW IMG Sorter — {self.source.name}")
        self.index, self.states = self.sessions.load(self.source, photos)
        self.gallery.set_photos(photos)
        if self.view_selector.currentIndex() == 1:
            self.gallery.start_loading()
        self.refresh()
        self.save_session()

    def save_session(self) -> None:
        if self.source and self.photos:
            try:
                self.sessions.save(self.source, self.index, self.photos, self.states)
            except OSError as error:
                self.statusBar().showMessage(f"Could not save session: {error}", 5000)

    def keep(self) -> None:
        if not self.photos:
            return
        self.states[self.index] = (
            PhotoState.PENDING
            if self.states[self.index] == PhotoState.SELECTED
            else PhotoState.SELECTED
        )
        if self.index < len(self.photos) - 1:
            self.index += 1
        self.save_session()
        self.refresh()

    def next_photo(self) -> None:
        if not self.photos:
            return
        if self.states[self.index] == PhotoState.PENDING:
            self.states[self.index] = PhotoState.REJECTED
        if self.index < len(self.photos) - 1:
            self.index += 1
        self.save_session()
        self.refresh()

    def previous_photo(self) -> None:
        if not self.photos or self.index == 0:
            return
        self.index -= 1
        self.save_session()
        self.refresh()

    def focus_photo(self, index: int) -> None:
        if 0 <= index < len(self.photos):
            self.index = index
            self.save_session()
            self.refresh()

    def refresh(self) -> None:
        if not self.photos:
            return
        photo, state = self.photos[self.index], self.states[self.index]
        self.name_label.setText(photo.jpg.name)
        self.state_label.setText(state.value.upper())
        self._update_state_styling(state)
        self.raw_label.setText("RAW ✓" if photo.raw else "RAW MISSING ⚠")
        self.raw_label.setStyleSheet("color: #e5c07b;" if photo.raw is None else "color: #63d17b;")
        selected = self.states.count(PhotoState.SELECTED)
        rejected = self.states.count(PhotoState.REJECTED)
        pending = len(self.states) - selected - rejected
        self.count_label.setText(
            f"Selected: {selected}    •    Rejected: {rejected}    •    Pending: {pending}"
        )
        self.position_label.setText(f"Photo: {self.index + 1} / {len(self.photos)}")
        self.metadata_label.setText(describe_image(photo.jpg))
        self.viewer.set_state(state)
        if self.view_stack.currentIndex() == 0:
            self.viewer.show_image(photo.jpg)
        else:
            self.gallery.update_statuses(self.states, self.index)

    def export_selected(self) -> None:
        if self.export_thread is not None:
            return
        selected = [photo for photo, state in zip(self.photos, self.states) if state == PhotoState.SELECTED]
        if not selected:
            QMessageBox.information(self, "Nothing selected", "Select at least one photo before exporting.")
            return
        chosen = QFileDialog.getExistingDirectory(self, "Select Export Folder", str(self.source or Path.home()))
        if not chosen:
            return
        destination = Path(chosen).resolve()
        if self.source and (destination == self.source or self.source in destination.parents):
            QMessageBox.warning(self, "Unsafe export folder", "Choose a destination outside the source photo folder.")
            return
        self.progress = QProgressDialog("Copying selected photos…", None, 0, 0, self)
        self.progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress.setMinimumDuration(0)
        self.export_thread = QThread(self)
        self.export_worker = ExportWorker(selected, destination)
        self.export_worker.moveToThread(self.export_thread)
        self.export_thread.started.connect(self.export_worker.run)
        self.export_worker.finished.connect(self._export_finished)
        self.export_worker.finished.connect(self.export_thread.quit)
        self.export_thread.finished.connect(self._export_cleanup)
        self.export_thread.start()

    def _export_finished(self, result: ExportResult) -> None:
        self.progress.close()
        details = [
            "Export complete", "", f"Selected: {result.selected}", f"JPG copied: {result.jpg_copied}",
            f"RAW copied: {result.raw_copied}", f"Missing RAW: {len(result.missing_raw)}",
            f"Copy failures: {len(result.failures)}",
        ]
        if result.missing_raw:
            details += ["", "Missing RAW files:", *result.missing_raw]
        if result.failures:
            details += ["", "Copy failures:", *result.failures]
        QMessageBox.information(self, "Export summary", "\n".join(details))

    def _export_cleanup(self) -> None:
        if self.export_worker:
            self.export_worker.deleteLater()
        if self.export_thread:
            self.export_thread.deleteLater()
        self.export_worker = None
        self.export_thread = None

    def closeEvent(self, event) -> None:
        self.save_session()
        if self.export_thread and self.export_thread.isRunning():
            QMessageBox.information(self, "Export in progress", "Please wait for the export to finish before closing.")
            event.ignore()
            return
        event.accept()
