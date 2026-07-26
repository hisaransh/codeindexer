"""Repository domain values."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class Repository:
    """A Git repository identified by its canonical root."""

    root: Path


@dataclass(frozen=True)
class TrackedFile:
    """A path and mode reported by Git's index."""

    relative_path: PurePosixPath
    mode: str
    stage: int


class SkipReason(StrEnum):
    """Why a tracked path was not accepted for indexing."""

    DELETED = "deleted"
    SYMLINK = "symlink"
    SUBMODULE = "submodule"
    UNMERGED = "unmerged"
    UNSUPPORTED_GIT_ENTRY = "unsupported_git_entry"
    UNSAFE_PATH = "unsafe_path"
    SECRET = "secret"
    DEPENDENCY = "dependency"
    GENERATED = "generated"
    OVERSIZED = "oversized"
    BINARY = "binary"
    UNSUPPORTED_ENCODING = "unsupported_encoding"
    EMPTY = "empty"
    UNSUPPORTED_TYPE = "unsupported_type"
    UNREADABLE = "unreadable"


@dataclass(frozen=True)
class DiscoveredFile:
    """An accepted tracked file using its current working-tree text."""

    relative_path: PurePosixPath
    text: str
    size_bytes: int


@dataclass(frozen=True)
class SkippedFile:
    """A tracked path excluded from indexing for one reason."""

    relative_path: PurePosixPath
    reason: SkipReason


type DiscoveryDecision = DiscoveredFile | SkippedFile


@dataclass(frozen=True)
class DiscoverySummary:
    """Counts produced after consuming repository discovery."""

    candidate_count: int
    accepted_count: int
    skipped_by_reason: tuple[tuple[SkipReason, int], ...]

    @property
    def skipped_count(self) -> int:
        """Return the number of candidates that were skipped."""

        return self.candidate_count - self.accepted_count
