"""Git subprocess operations and index-entry interpretation."""

import os
from pathlib import Path, PurePosixPath
import subprocess

from codeindex.repository.errors import (
    GitUnavailableError,
    NotGitRepositoryError,
    RepositoryInspectionError,
    TrackedFilesInspectionError,
    TrackedFilesOutputError,
)
from codeindex.repository.models import SkipReason, TrackedFile


def find_git_root(path: Path) -> Path:
    """Return Git's canonical top-level directory for *path*."""

    try:
        completed = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            capture_output=True,
            check=False,
            text=True,
        )
    except FileNotFoundError as error:
        raise GitUnavailableError() from error
    except OSError as error:
        raise RepositoryInspectionError(path) from error

    if completed.returncode != 0:
        if "not a git repository" in completed.stderr.casefold():
            raise NotGitRepositoryError(path)
        raise RepositoryInspectionError(path)

    root_text = completed.stdout.strip()
    if not root_text:
        raise RepositoryInspectionError(path)

    return Path(root_text).expanduser().resolve()


def list_tracked_files(root: Path) -> tuple[TrackedFile, ...]:
    """Return deterministic metadata for unique paths in Git's index."""

    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "--cached",
                "--stage",
                "--full-name",
                "-z",
            ],
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as error:
        raise GitUnavailableError() from error
    except OSError as error:
        raise TrackedFilesInspectionError(root) from error

    if completed.returncode != 0:
        raise TrackedFilesInspectionError(root)

    return _parse_tracked_files(completed.stdout)


def classify_git_entry(tracked_file: TrackedFile) -> SkipReason | None:
    """Return why a Git index entry cannot be inspected as a regular file.

    Examples:
    - Mode ``120000`` returns ``symlink``.
    - Mode ``160000`` returns ``submodule``.
    - A nonzero stage returns ``unmerged``.
    - A stage-zero mode ``100644`` or ``100755`` returns ``None``.
    """

    if tracked_file.stage != 0:
        return SkipReason.UNMERGED
    if tracked_file.mode == "120000":
        return SkipReason.SYMLINK
    if tracked_file.mode == "160000":
        return SkipReason.SUBMODULE
    if tracked_file.mode not in {"100644", "100755"}:
        return SkipReason.UNSUPPORTED_GIT_ENTRY
    return None


def _parse_tracked_files(output: bytes) -> tuple[TrackedFile, ...]:
    """Parse NUL-delimited stage output and collapse duplicate index paths."""

    entries_by_path: dict[bytes, TrackedFile] = {}

    for record in output.split(b"\0"):
        if not record:
            continue

        header, separator, path_bytes = record.partition(b"\t")
        fields = header.split()
        if not separator or len(fields) != 3 or not path_bytes:
            raise TrackedFilesOutputError()

        mode_bytes, _object_id, stage_bytes = fields
        try:
            mode = mode_bytes.decode("ascii")
            stage = int(stage_bytes)
        except (UnicodeDecodeError, ValueError) as error:
            raise TrackedFilesOutputError() from error

        if stage not in {0, 1, 2, 3}:
            raise TrackedFilesOutputError()

        relative_path = PurePosixPath(os.fsdecode(path_bytes))
        entry = TrackedFile(
            relative_path=relative_path,
            mode=mode,
            stage=stage,
        )
        existing = entries_by_path.get(path_bytes)
        if existing is None or (existing.stage != 0 and stage == 0):
            entries_by_path[path_bytes] = entry

    return tuple(entries_by_path[path] for path in sorted(entries_by_path))
