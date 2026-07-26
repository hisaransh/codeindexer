"""Repository identity and validation."""

from codeindex.repository.errors import (
    GitUnavailableError,
    NestedRepositoryPathError,
    NotGitRepositoryError,
    RepositoryError,
    RepositoryInspectionError,
    RepositoryPathNotDirectoryError,
    RepositoryPathNotFoundError,
)
from codeindex.repository.models import Repository
from codeindex.repository.resolver import find_git_root, resolve_repository

__all__ = [
    "GitUnavailableError",
    "NestedRepositoryPathError",
    "NotGitRepositoryError",
    "Repository",
    "RepositoryError",
    "RepositoryInspectionError",
    "RepositoryPathNotDirectoryError",
    "RepositoryPathNotFoundError",
    "find_git_root",
    "resolve_repository",
]
