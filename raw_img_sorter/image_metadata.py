from datetime import datetime
from pathlib import Path

from PIL import Image


def _number(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _shutter(value) -> str | None:
    seconds = _number(value)
    if not seconds or seconds <= 0:
        return None
    if seconds < 1:
        denominator = round(1 / seconds)
        return f"1/{denominator} s"
    return f"{seconds:g} s"


def _captured_date(value) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        captured = datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
        return captured.strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return raw


def describe_image(path: Path) -> str:
    """Return a compact EXIF summary without decoding image pixels."""
    try:
        with Image.open(path) as image:
            exif = image.getexif()
    except (OSError, ValueError):
        return "Metadata: unavailable"

    try:
        camera_exif = exif.get_ifd(34665)  # ExifOffset / Exif IFD
    except (KeyError, TypeError):
        camera_exif = {}

    def value(tag: int):
        return camera_exif.get(tag, exif.get(tag))

    parts: list[str] = []
    aperture = _number(value(33437))  # FNumber
    exposure = _shutter(value(33434))  # ExposureTime
    iso = value(34855)  # PhotographicSensitivity
    focal_length = _number(value(37386))
    model = str(exif.get(272, "")).strip()
    captured = _captured_date(value(36867))

    if aperture:
        parts.append(f"Aperture: f/{aperture:g}")
    if exposure:
        parts.append(f"Shutter: {exposure}")
    if iso:
        parts.append(f"ISO: {iso}")
    if focal_length:
        parts.append(f"Focal length: {focal_length:g} mm")
    if model:
        parts.append(f"Camera: {model}")
    if captured:
        parts.append(f"Captured: {captured}")
    return "    •    ".join(parts) if parts else "Metadata: no EXIF information found"
