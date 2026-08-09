from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class PhotoState(str, Enum):
    PENDING = "pending"
    SELECTED = "selected"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Photo:
    jpg: Path
    raw: Path | None
