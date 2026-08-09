import shutil
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from .models import Photo


@dataclass
class ExportResult:
    selected: int
    jpg_copied: int = 0
    raw_copied: int = 0
    missing_raw: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


class ExportWorker(QObject):
    finished = Signal(object)

    def __init__(self, photos: list[Photo], destination: Path) -> None:
        super().__init__()
        self.photos = photos
        self.destination = destination

    @Slot()
    def run(self) -> None:
        result = ExportResult(selected=len(self.photos))
        jpg_dir, raw_dir = self.destination / "JPG", self.destination / "RAW"
        try:
            jpg_dir.mkdir(parents=True, exist_ok=True)
            raw_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            result.failures.append(f"Could not create export folders: {error}")
            self.finished.emit(result)
            return

        for photo in self.photos:
            try:
                shutil.copy2(photo.jpg, jpg_dir / photo.jpg.name)
                result.jpg_copied += 1
            except OSError as error:
                result.failures.append(f"{photo.jpg.name}: {error}")
            if photo.raw is None:
                result.missing_raw.append(f"{photo.jpg.stem}.CR3")
            else:
                try:
                    shutil.copy2(photo.raw, raw_dir / photo.raw.name)
                    result.raw_copied += 1
                except OSError as error:
                    result.failures.append(f"{photo.raw.name}: {error}")
        self.finished.emit(result)
