"""Filesystem validation for exact repository roots."""

from collections.abc import Callable
from pathlib import Path

from codeindex.repository.errors import (
    NestedRepositoryPathError,
    RepositoryPathNotDirectoryError,
    RepositoryPathNotFoundError,
)
from codeindex.repository.gitops import find_git_root
from codeindex.repository.models import Repository


GitRootLookup = Callable[[Path], Path]


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
