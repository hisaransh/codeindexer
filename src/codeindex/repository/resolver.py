"""Filesystem validation and Git repository inspection."""

from collections.abc import Callable
from pathlib import Path
import subprocess

from codeindex.repository.errors import (
    GitUnavailableError,
    NestedRepositoryPathError,
    NotGitRepositoryError,
    RepositoryInspectionError,
    RepositoryPathNotDirectoryError,
    RepositoryPathNotFoundError,
)
from codeindex.repository.models import Repository


GitRootLookup = Callable[[Path], Path]

# git -C /Users/saransh/Desktop/uh/coolapp/app/controllers/performance rev-parse --show-toplevel
# /Users/saransh/Desktop/uh/coolapp
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


def resolve_repository(
    path: str | Path,
    *,
    git_root_lookup: GitRootLookup = find_git_root,
) -> Repository:
    """Resolve *path* and require it to be the exact root of a Git worktree."""

    canonical_path = Path(path).expanduser().resolve()

    if not canonical_path.exists():
        raise RepositoryPathNotFoundError(canonical_path)
    if not canonical_path.is_dir():
        raise RepositoryPathNotDirectoryError(canonical_path)

    root = git_root_lookup(canonical_path).expanduser().resolve()
    if canonical_path != root:
        raise NestedRepositoryPathError(canonical_path, root)

    return Repository(root=root)
