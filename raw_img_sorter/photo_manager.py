from pathlib import Path

from .models import Photo


JPG_EXTENSIONS = {".jpg", ".jpeg"}


def scan_folder(folder: Path) -> list[Photo]:
    """Scan one directory (not recursively), matching CR3 files by stem."""
    files = [entry for entry in folder.iterdir() if entry.is_file()]
    raws: dict[str, Path] = {}
    for path in files:
        if path.suffix.lower() == ".cr3":
            raws.setdefault(path.stem.casefold(), path)

    jpgs = sorted(
        (path for path in files if path.suffix.lower() in JPG_EXTENSIONS),
        key=lambda path: (path.name.casefold(), path.name),
    )
    return [Photo(jpg=jpg, raw=raws.get(jpg.stem.casefold())) for jpg in jpgs]
