"""Expected repository validation failures."""

from pathlib import Path


class RepositoryError(Exception):
    """Base class for expected repository validation failures."""


class RepositoryPathNotFoundError(RepositoryError):
    def __init__(self, path: Path) -> None:
        super().__init__(f"Path does not exist: {path}")


class RepositoryPathNotDirectoryError(RepositoryError):
    def __init__(self, path: Path) -> None:
        super().__init__(f"Path is not a directory: {path}")


class NotGitRepositoryError(RepositoryError):
    def __init__(self, path: Path) -> None:
        super().__init__(f"Not a Git repository: {path}")


class NestedRepositoryPathError(RepositoryError):
    def __init__(self, path: Path, root: Path) -> None:
        super().__init__(f"Path must be the repository root: {path} (root: {root})")


class GitUnavailableError(RepositoryError):
    def __init__(self) -> None:
        super().__init__("Git executable is not available.")


class RepositoryInspectionError(RepositoryError):
    def __init__(self, path: Path) -> None:
        super().__init__(f"Unable to inspect Git repository: {path}")
