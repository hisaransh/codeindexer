from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from codeindex import cli
from codeindex.repository.errors import (
    GitUnavailableError,
    NestedRepositoryPathError,
    NotGitRepositoryError,
    RepositoryInspectionError,
    RepositoryPathNotDirectoryError,
    RepositoryPathNotFoundError,
)
from codeindex.repository.models import Repository


runner = CliRunner()


@pytest.mark.parametrize(
    ("arguments", "expected_text"),
    [
        (["--help"], "Index and search local source repositories."),
        (["index", "--help"], "Prepare to index a repository."),
        (["search", "--help"], "Prepare to search a repository."),
        (["status", "--help"], "Prepare to show repository index status."),
    ],
)
def test_help(arguments: list[str], expected_text: str) -> None:
    result = runner.invoke(cli.app, arguments)

    assert result.exit_code == 0
    assert expected_text in result.stdout
    assert result.stderr == ""


def test_search_requires_query() -> None:
    result = runner.invoke(cli.app, ["search"])

    assert result.exit_code == 2
    assert "Missing argument" in result.stderr
    assert "QUERY" in result.stderr
    assert result.stdout == ""
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    ("command", "expected_usage"),
    [
        ("index", "[PATH]"),
        ("search", "{QUERY} [PATH]"),
        ("status", "[PATH]"),
    ],
)
def test_command_help_shows_positional_interface(
    command: str,
    expected_usage: str,
) -> None:
    result = runner.invoke(cli.app, [command, "--help"])

    assert result.exit_code == 0
    assert expected_usage in result.stdout


@pytest.mark.parametrize(
    ("arguments", "expected_path", "placeholder"),
    [
        (
            ["index"],
            Path("."),
            "The index command is not implemented yet.\n",
        ),
        (
            ["index", "/repository"],
            Path("/repository"),
            "The index command is not implemented yet.\n",
        ),
        (
            ["search", "retry failures"],
            Path("."),
            "The search command is not implemented yet.\n",
        ),
        (
            ["search", "retry failures", "/repository"],
            Path("/repository"),
            "The search command is not implemented yet.\n",
        ),
        (
            ["status"],
            Path("."),
            "The status command is not implemented yet.\n",
        ),
        (
            ["status", "/repository"],
            Path("/repository"),
            "The status command is not implemented yet.\n",
        ),
    ],
)
def test_successful_commands_use_expected_path_and_placeholder(
    monkeypatch: pytest.MonkeyPatch,
    arguments: list[str],
    expected_path: Path,
    placeholder: str,
) -> None:
    observed_paths: list[Path] = []

    def resolve(path: str | Path) -> Repository:
        observed_paths.append(Path(path))
        return Repository(root=Path("/repository"))

    monkeypatch.setattr(cli, "resolve_repository", resolve)

    result = runner.invoke(cli.app, arguments)

    assert result.exit_code == 0
    assert result.stdout == placeholder
    assert result.stderr == ""
    assert observed_paths == [expected_path]


@pytest.mark.parametrize(
    ("error_factory", "expected_message"),
    [
        (
            lambda path: RepositoryPathNotFoundError(path),
            "Path does not exist:",
        ),
        (
            lambda path: RepositoryPathNotDirectoryError(path),
            "Path is not a directory:",
        ),
        (
            lambda path: NotGitRepositoryError(path),
            "Not a Git repository:",
        ),
        (
            lambda path: NestedRepositoryPathError(path, path.parent),
            "Path must be the repository root:",
        ),
        (
            lambda path: GitUnavailableError(),
            "Git executable is not available.",
        ),
        (
            lambda path: RepositoryInspectionError(path),
            "Unable to inspect Git repository:",
        ),
    ],
)
def test_expected_repository_errors_are_stderr_without_tracebacks(
    monkeypatch: pytest.MonkeyPatch,
    error_factory: Callable[[Path], Exception],
    expected_message: str,
) -> None:
    def reject(path: str | Path) -> Repository:
        raise error_factory(Path(path))

    monkeypatch.setattr(cli, "resolve_repository", reject)

    result = runner.invoke(cli.app, ["status", "/repository"])

    assert result.exit_code == 2
    assert result.stdout == ""
    assert expected_message in result.stderr
    assert "Traceback" not in result.stderr
