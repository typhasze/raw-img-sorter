import hashlib
import json
import os
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from .models import Photo, PhotoState


class SessionManager:
    def __init__(self) -> None:
        root = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        self.root = Path(root) if root else Path.home() / ".raw_img_sorter"
        self.root.mkdir(parents=True, exist_ok=True)
        self.last_file = self.root / "last_source.json"

    @staticmethod
    def _source_key(source: Path) -> str:
        normalized = os.path.normcase(str(source.resolve()))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _session_file(self, source: Path) -> Path:
        return self.root / f"session-{self._source_key(source)}.json"

    def save(self, source: Path, index: int, photos: list[Photo], states: list[PhotoState]) -> None:
        data = {
            "source_folder": str(source),
            "current_index": index,
            "states": {photo.jpg.name: state.value for photo, state in zip(photos, states)},
        }
        destination = self._session_file(source)
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temporary.replace(destination)
        self.last_file.write_text(json.dumps({"source_folder": str(source)}), encoding="utf-8")

    def load(self, source: Path, photos: list[Photo]) -> tuple[int, list[PhotoState]]:
        states = [PhotoState.PENDING] * len(photos)
        try:
            data = json.loads(self._session_file(source).read_text(encoding="utf-8"))
            saved = data.get("states", {})
            states = [PhotoState(saved.get(photo.jpg.name, PhotoState.PENDING.value)) for photo in photos]
            index = max(0, min(int(data.get("current_index", 0)), max(0, len(photos) - 1)))
            return index, states
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return 0, states

    def last_source(self) -> Path | None:
        try:
            folder = Path(json.loads(self.last_file.read_text(encoding="utf-8"))["source_folder"])
            return folder if folder.is_dir() else None
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            return None
