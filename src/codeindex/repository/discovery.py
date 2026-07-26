"""Lazy discovery of safe, useful Git-tracked files."""

from collections import Counter
from collections.abc import Callable, Iterable, Iterator
import os
from pathlib import Path, PurePosixPath
import stat

from codeindex.repository.gitops import (
    classify_git_entry,
    list_tracked_files,
)
from codeindex.repository.models import (
    DiscoveredFile,
    DiscoveryDecision,
    DiscoverySummary,
    Repository,
    SkipReason,
    SkippedFile,
    TrackedFile,
)
from codeindex.repository.policy import (
    classify_path,
    is_generated_text,
    is_supported_file,
)


DEFAULT_MAX_FILE_BYTES = 1024 * 1024
TrackedFilesLookup = Callable[[Path], Iterable[TrackedFile]]
FileReader = Callable[[Path, int], bytes]


def discover_files(
    repository: Repository,
    *,
    tracked_files_lookup: TrackedFilesLookup = list_tracked_files,
    file_reader: FileReader | None = None,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> Iterator[DiscoveryDecision]:
    """Yield one accepted or skipped decision per tracked repository path."""

    if max_file_bytes < 1:
        raise ValueError("max_file_bytes must be positive")

    read_file = file_reader or _read_file
    for tracked_file in tracked_files_lookup(repository.root):
        yield _inspect_tracked_file(
            repository,
            tracked_file,
            file_reader=read_file,
            max_file_bytes=max_file_bytes,
        )


def summarize_discovery(
    decisions: Iterable[DiscoveryDecision],
) -> DiscoverySummary:
    """Consume discovery decisions and return deterministic counts."""

    candidate_count = 0
    accepted_count = 0
    skipped_counts: Counter[SkipReason] = Counter()

    for decision in decisions:
        candidate_count += 1
        if isinstance(decision, DiscoveredFile):
            accepted_count += 1
        else:
            skipped_counts[decision.reason] += 1

    return DiscoverySummary(
        candidate_count=candidate_count,
        accepted_count=accepted_count,
        skipped_by_reason=tuple(
            sorted(skipped_counts.items(), key=lambda item: item[0].value)
        ),
    )


def _inspect_tracked_file(
    repository: Repository,
    tracked_file: TrackedFile,
    *,
    file_reader: FileReader,
    max_file_bytes: int,
) -> DiscoveryDecision:
    """Apply the ordered safety policy and return exactly one decision."""

    relative_path = tracked_file.relative_path

    entry_reason = classify_git_entry(tracked_file)
    if entry_reason is not None:
        return SkippedFile(relative_path, entry_reason)
    if not _is_safe_relative_path(relative_path):
        return SkippedFile(relative_path, SkipReason.UNSAFE_PATH)

    path = repository.root.joinpath(*relative_path.parts)
    try:
        path_stat = _lstat_without_symlinks(repository.root, relative_path)
    except FileNotFoundError:
        return SkippedFile(relative_path, SkipReason.DELETED)
    except OSError:
        return SkippedFile(relative_path, SkipReason.UNREADABLE)

    if path_stat is None:
        return SkippedFile(relative_path, SkipReason.SYMLINK)
    if not stat.S_ISREG(path_stat.st_mode):
        return SkippedFile(relative_path, SkipReason.UNSUPPORTED_GIT_ENTRY)

    path_reason = classify_path(relative_path)
    if path_reason is not None:
        return SkippedFile(relative_path, path_reason)
    if path_stat.st_size == 0:
        return SkippedFile(relative_path, SkipReason.EMPTY)
    if path_stat.st_size > max_file_bytes:
        return SkippedFile(relative_path, SkipReason.OVERSIZED)

    try:
        content = file_reader(path, max_file_bytes + 1)
    except OSError:
        return SkippedFile(relative_path, SkipReason.UNREADABLE)

    if len(content) > max_file_bytes:
        return SkippedFile(relative_path, SkipReason.OVERSIZED)
    if b"\0" in content:
        return SkippedFile(relative_path, SkipReason.BINARY)

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return SkippedFile(relative_path, SkipReason.UNSUPPORTED_ENCODING)

    if not text.strip():
        return SkippedFile(relative_path, SkipReason.EMPTY)
    if is_generated_text(text):
        return SkippedFile(relative_path, SkipReason.GENERATED)
    if not is_supported_file(relative_path, text):
        return SkippedFile(relative_path, SkipReason.UNSUPPORTED_TYPE)

    return DiscoveredFile(
        relative_path=relative_path,
        text=text,
        size_bytes=len(content),
    )


def _is_safe_relative_path(relative_path: PurePosixPath) -> bool:
    """Reject absolute, empty, root, and parent-traversing Git paths.

    For example, ``src/app.py`` is safe while ``../outside.py`` is not.
    """

    return (
        not relative_path.is_absolute()
        and bool(relative_path.parts)
        and relative_path != PurePosixPath(".")
        and ".." not in relative_path.parts
    )


def _lstat_without_symlinks(
    root: Path,
    relative_path: PurePosixPath,
) -> os.stat_result | None:
    """Inspect each path component and return ``None`` upon any symlink."""

    current = root
    current_stat: os.stat_result | None = None
    for part in relative_path.parts:
        current = current / part
        current_stat = current.lstat()
        if stat.S_ISLNK(current_stat.st_mode):
            return None

    return current_stat


def _read_file(path: Path, byte_limit: int) -> bytes:
    """Read at most *byte_limit* bytes from one working-tree file."""

    with path.open("rb") as file:
        return file.read(byte_limit)
