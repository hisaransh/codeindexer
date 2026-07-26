"""Expected chunking failures."""

import json
from pathlib import PurePosixPath


class ChunkingError(Exception):
    """Base class for expected chunking failures."""


class ChunkBudgetError(ChunkingError):
    """Source text cannot make progress within the configured budget."""

    def __init__(self, relative_path: PurePosixPath, line: int) -> None:
        escaped_path = json.dumps(relative_path.as_posix(), ensure_ascii=True)
        super().__init__(
            "Unable to fit source text within the configured chunk budget at "
            f"{escaped_path}:{line}."
        )


class TextMeasurementError(ChunkingError):
    """A text measurer violated the chunking boundary contract."""

    def __init__(self, measurer_name: str) -> None:
        super().__init__(
            f"Text measurer returned an invalid size: {measurer_name}."
        )
