from pathlib import Path
import subprocess

import pytest

import codeindex.repository.resolver as resolver_module
from codeindex.repository.errors import (
    GitUnavailableError,
    NestedRepositoryPathError,
    NotGitRepositoryError,
    RepositoryInspectionError,
    RepositoryPathNotDirectoryError,
    RepositoryPathNotFoundError,
)
from codeindex.repository.resolver import (
    find_git_root,
    resolve_repository,
)


def test_resolves_valid_repository_root(tmp_path: Path) -> None:
    observed_paths: list[Path] = []

    def lookup(path: Path) -> Path:
        observed_paths.append(path)
        return path

    repository = resolve_repository(tmp_path, git_root_lookup=lookup)

    assert repository.root == tmp_path.resolve()
    assert observed_paths == [tmp_path.resolve()]


def test_rejects_missing_path_before_git_lookup(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing"

    with pytest.raises(
        RepositoryPathNotFoundError,
        match=r"^Path does not exist:",
    ):
        resolve_repository(
            missing_path,
            git_root_lookup=lambda path: pytest.fail("Git lookup was called"),
        )


def test_rejects_file_before_git_lookup(tmp_path: Path) -> None:
    file_path = tmp_path / "file.py"
    file_path.write_text("content", encoding="utf-8")

    with pytest.raises(
        RepositoryPathNotDirectoryError,
        match=r"^Path is not a directory:",
    ):
        resolve_repository(
            file_path,
            git_root_lookup=lambda path: pytest.fail("Git lookup was called"),
        )


def test_rejects_non_git_directory(tmp_path: Path) -> None:
    def lookup(path: Path) -> Path:
        raise NotGitRepositoryError(path)

    with pytest.raises(NotGitRepositoryError, match=r"^Not a Git repository:"):
        resolve_repository(tmp_path, git_root_lookup=lookup)


def test_rejects_nested_repository_path(tmp_path: Path) -> None:
    nested_path = tmp_path / "src"
    nested_path.mkdir()

    with pytest.raises(
        NestedRepositoryPathError,
        match=r"^Path must be the repository root:",
    ):
        resolve_repository(
            nested_path,
            git_root_lookup=lambda path: tmp_path,
        )


def test_accepts_symlink_that_resolves_to_repository_root(tmp_path: Path) -> None:
    repository_root = tmp_path / "repository"
    repository_root.mkdir()
    symlink = tmp_path / "repository-link"
    symlink.symlink_to(repository_root, target_is_directory=True)

    repository = resolve_repository(
        symlink,
        git_root_lookup=lambda path: repository_root,
    )

    assert repository.root == repository_root.resolve()


def test_reports_unavailable_git(tmp_path: Path) -> None:
    def lookup(path: Path) -> Path:
        raise GitUnavailableError

    with pytest.raises(
        GitUnavailableError,
        match=r"^Git executable is not available\.$",
    ):
        resolve_repository(tmp_path, git_root_lookup=lookup)


def test_reports_failed_git_inspection(tmp_path: Path) -> None:
    def lookup(path: Path) -> Path:
        raise RepositoryInspectionError(path)

    with pytest.raises(
        RepositoryInspectionError,
        match=r"^Unable to inspect Git repository:",
    ):
        resolve_repository(tmp_path, git_root_lookup=lookup)


def test_git_adapter_reports_missing_executable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def unavailable(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError

    monkeypatch.setattr(resolver_module.subprocess, "run", unavailable)

    with pytest.raises(GitUnavailableError):
        find_git_root(tmp_path)


def test_git_adapter_distinguishes_non_git_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    completed = subprocess.CompletedProcess(
        args=[],
        returncode=128,
        stdout="",
        stderr="fatal: not a git repository",
    )
    monkeypatch.setattr(
        resolver_module.subprocess,
        "run",
        lambda *args, **kwargs: completed,
    )

    with pytest.raises(NotGitRepositoryError):
        find_git_root(tmp_path)


def test_git_adapter_reports_unexpected_failed_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    completed = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="",
        stderr="fatal: unexpected failure",
    )
    monkeypatch.setattr(
        resolver_module.subprocess,
        "run",
        lambda *args, **kwargs: completed,
    )

    with pytest.raises(RepositoryInspectionError):
        find_git_root(tmp_path)
