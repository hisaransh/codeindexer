"""Repository domain values."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Repository:
    """A Git repository identified by its canonical root."""

    root: Path
