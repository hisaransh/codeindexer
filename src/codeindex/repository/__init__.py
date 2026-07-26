"""Public repository validation and discovery API."""

from codeindex.repository.discovery import (
    DEFAULT_MAX_FILE_BYTES,
    discover_files,
    summarize_discovery,
)
from codeindex.repository.errors import (
    GitUnavailableError,
    NestedRepositoryPathError,
    NotGitRepositoryError,
    RepositoryError,
    RepositoryInspectionError,
    RepositoryPathNotDirectoryError,
    RepositoryPathNotFoundError,
    TrackedFilesInspectionError,
    TrackedFilesOutputError,
)
from codeindex.repository.gitops import find_git_root, list_tracked_files
from codeindex.repository.models import (
    DiscoveredFile,
    DiscoveryDecision,
    DiscoverySummary,
    Repository,
    SkipReason,
    SkippedFile,
    TrackedFile,
)
from codeindex.repository.resolver import resolve_repository

__all__ = [
    "DEFAULT_MAX_FILE_BYTES",
    "DiscoveredFile",
    "DiscoveryDecision",
    "DiscoverySummary",
    "GitUnavailableError",
    "NestedRepositoryPathError",
    "NotGitRepositoryError",
    "Repository",
    "RepositoryError",
    "RepositoryInspectionError",
    "RepositoryPathNotDirectoryError",
    "RepositoryPathNotFoundError",
    "SkipReason",
    "SkippedFile",
    "TrackedFile",
    "TrackedFilesInspectionError",
    "TrackedFilesOutputError",
    "discover_files",
    "find_git_root",
    "list_tracked_files",
    "resolve_repository",
    "summarize_discovery",
]
