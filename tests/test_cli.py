from collections.abc import Callable, Iterable
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
    TrackedFilesInspectionError,
)
from codeindex.repository.models import (
    DiscoveredFile,
    Repository,
    SkipReason,
    SkippedFile,
)


runner = CliRunner()


@pytest.mark.parametrize(
    ("arguments", "expected_text"),
    [
        (["--help"], "Index and search local source repositories."),
        (["index", "--help"], "Discover files eligible for indexing."),
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


def test_index_help_shows_verbose_option() -> None:
    result = runner.invoke(cli.app, ["index", "--help"])

    assert result.exit_code == 0
    assert "--verbose" in result.stdout
    assert "-v" in result.stdout
    assert "List every skipped repository-relative path and reason." in result.stdout


@pytest.mark.parametrize(
    ("arguments", "expected_path", "placeholder"),
    [
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
    ("arguments", "expected_path"),
    [
        (["index"], Path(".")),
        (["index", "/repository"], Path("/repository")),
    ],
)
def test_index_discovers_expected_path_and_prints_summary(
    monkeypatch: pytest.MonkeyPatch,
    arguments: list[str],
    expected_path: Path,
) -> None:
    observed_paths: list[Path] = []
    repository = Repository(root=Path("/repository"))

    def resolve(path: str | Path) -> Repository:
        observed_paths.append(Path(path))
        return repository

    monkeypatch.setattr(cli, "resolve_repository", resolve)
    monkeypatch.setattr(
        cli,
        "discover_files",
        lambda resolved_repository: [
            DiscoveredFile(Path("src/app.py"), "app = True\n", 11),
            SkippedFile(Path("dist/app.js"), SkipReason.GENERATED),
            SkippedFile(Path("image.bin"), SkipReason.BINARY),
        ],
    )

    result = runner.invoke(cli.app, arguments)

    assert result.exit_code == 0
    assert result.stdout == (
        "Candidates: 3\n"
        "Accepted: 1\n"
        "Skipped: 2\n"
        "Skipped by reason: binary=1, generated=1\n"
        "Index creation is not implemented yet.\n"
    )
    assert result.stderr == ""
    assert observed_paths == [expected_path]


def test_index_prints_none_when_no_files_are_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli,
        "resolve_repository",
        lambda path: Repository(root=Path("/repository")),
    )
    monkeypatch.setattr(
        cli,
        "discover_files",
        lambda repository: [
            DiscoveredFile(Path("README.md"), "read me\n", 8)
        ],
    )

    result = runner.invoke(cli.app, ["index", "/repository"])

    assert result.exit_code == 0
    assert "Skipped: 0\n" in result.stdout
    assert "Skipped by reason: none\n" in result.stdout
    assert result.stderr == ""


def test_index_verbose_lists_skipped_paths_by_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli,
        "resolve_repository",
        lambda path: Repository(root=Path("/repository")),
    )
    monkeypatch.setattr(
        cli,
        "discover_files",
        lambda repository: [
            SkippedFile(
                Path("fixtures/events.data"),
                SkipReason.UNSUPPORTED_TYPE,
            ),
            DiscoveredFile(Path("src/app.py"), "app = True\n", 11),
            SkippedFile(Path("assets/odd\nname.bin"), SkipReason.BINARY),
            SkippedFile(Path("assets/logo.bin"), SkipReason.BINARY),
        ],
    )

    result = runner.invoke(
        cli.app,
        ["index", "--verbose", "/repository"],
    )

    assert result.exit_code == 0
    assert result.stdout == (
        "Candidates: 4\n"
        "Accepted: 1\n"
        "Skipped: 3\n"
        "Skipped by reason: binary=2, unsupported_type=1\n"
        "Skipped files:\n"
        '  binary: "assets/logo.bin"\n'
        '  binary: "assets/odd\\nname.bin"\n'
        '  unsupported_type: "fixtures/events.data"\n'
        "Index creation is not implemented yet.\n"
    )
    assert result.stderr == ""


def test_index_verbose_reports_when_nothing_is_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli,
        "resolve_repository",
        lambda path: Repository(root=Path("/repository")),
    )
    monkeypatch.setattr(
        cli,
        "discover_files",
        lambda repository: [
            DiscoveredFile(Path("src/app.py"), "app = True\n", 11)
        ],
    )

    result = runner.invoke(cli.app, ["index", "-v", "/repository"])

    assert result.exit_code == 0
    assert "Skipped files: none\n" in result.stdout
    assert result.stderr == ""


def test_index_discovery_error_is_stderr_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = Repository(root=Path("/repository"))
    monkeypatch.setattr(cli, "resolve_repository", lambda path: repository)

    def fail_discovery(
        resolved_repository: Repository,
    ) -> Iterable[DiscoveredFile]:
        raise TrackedFilesInspectionError(resolved_repository.root)

    monkeypatch.setattr(cli, "discover_files", fail_discovery)

    result = runner.invoke(cli.app, ["index", "/repository"])

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "Unable to enumerate Git-tracked files:" in result.stderr
    assert "Traceback" not in result.stderr


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
