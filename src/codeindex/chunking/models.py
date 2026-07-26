"""Typed values for deterministic source chunks."""

from dataclasses import dataclass
from pathlib import PurePosixPath


# Bump this when defaults or implementation behavior can change chunk output.
LINE_CHUNKING_STRATEGY_VERSION = "line-v1"


@dataclass(frozen=True)
class ChunkingConfig:
    """Configuration that can change line-aware chunk boundaries."""

    max_lines: int = 50
    overlap_lines: int = 10
    max_units: int = 2_000

    def __post_init__(self) -> None:
        if self.max_lines < 1:
            raise ValueError("max_lines must be positive")
        if self.overlap_lines < 0:
            raise ValueError("overlap_lines cannot be negative")
        if self.overlap_lines >= self.max_lines:
            raise ValueError("overlap_lines must be less than max_lines")
        if self.max_units < 1:
            raise ValueError("max_units must be positive")


DEFAULT_CHUNKING_CONFIG = ChunkingConfig()


@dataclass(frozen=True)
class CodeChunk:
    """A traceable piece of one repository-relative source file."""

    chunk_id: str
    relative_path: PurePosixPath
    text: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    strategy_version: str
