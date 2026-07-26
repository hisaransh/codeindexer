"""Command-line interface for codeindex."""

from collections.abc import Iterable, Iterator
import json
from pathlib import Path
from typing import Annotated

import typer

from codeindex.repository import (
    DiscoveryDecision,
    RepositoryError,
    SkippedFile,
    discover_files,
    resolve_repository,
    summarize_discovery,
)


app = typer.Typer(
    help="Index and search local source repositories.",
    no_args_is_help=True,
)

RepositoryPath = Annotated[
    Path,
    typer.Argument(help="Exact root of the Git repository.", metavar="PATH"),
]


def _validate_and_render(path: Path, placeholder: str) -> None:
    """Validate one repository path, then print a command placeholder."""

    try:
        resolve_repository(path)
    except RepositoryError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=2) from error

    typer.echo(placeholder)


def _discover_and_render(path: Path, *, verbose: bool) -> None:
    """Run tracked-file discovery and print its deterministic summary."""

    skipped_files: list[SkippedFile] = []
    try:
        repository = resolve_repository(path)
        decisions = discover_files(repository)
        if verbose:
            decisions = _record_skipped_files(decisions, skipped_files)
        summary = summarize_discovery(decisions)
    except RepositoryError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=2) from error

    typer.echo(f"Candidates: {summary.candidate_count}")
    typer.echo(f"Accepted: {summary.accepted_count}")
    typer.echo(f"Skipped: {summary.skipped_count}")
    if summary.skipped_by_reason:
        reason_counts = ", ".join(
            f"{reason.value}={count}"
            for reason, count in summary.skipped_by_reason
        )
    else:
        reason_counts = "none"
    typer.echo(f"Skipped by reason: {reason_counts}")
    if verbose:
        _render_skipped_files(skipped_files)
    typer.echo("Index creation is not implemented yet.")


def _record_skipped_files(
    decisions: Iterable[DiscoveryDecision],
    skipped_files: list[SkippedFile],
) -> Iterator[DiscoveryDecision]:
    """Retain only skipped path metadata while streaming file decisions."""

    for decision in decisions:
        if isinstance(decision, SkippedFile):
            skipped_files.append(decision)
        yield decision


def _render_skipped_files(skipped_files: list[SkippedFile]) -> None:
    """Print safely escaped skipped paths grouped deterministically by reason."""

    if not skipped_files:
        typer.echo("Skipped files: none")
        return

    typer.echo("Skipped files:")
    for skipped_file in sorted(
        skipped_files,
        key=lambda item: (item.reason.value, item.relative_path.as_posix()),
    ):
        escaped_path = json.dumps(
            skipped_file.relative_path.as_posix(),
            ensure_ascii=True,
        )
        typer.echo(f"  {skipped_file.reason.value}: {escaped_path}")


@app.command()
def index(
    path: RepositoryPath = Path("."),
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="List every skipped repository-relative path and reason.",
        ),
    ] = False,
) -> None:
    """Discover files eligible for indexing."""

    _discover_and_render(path, verbose=verbose)


@app.command()
def search(
    query: Annotated[
        str,
        typer.Argument(help="Natural-language search query.", metavar="QUERY"),
    ],
    path: RepositoryPath = Path("."),
) -> None:
    """Prepare to search a repository."""

    _validate_and_render(path, "The search command is not implemented yet.")


@app.command()
def status(path: RepositoryPath = Path(".")) -> None:
    """Prepare to show repository index status."""

    _validate_and_render(path, "The status command is not implemented yet.")


def main() -> None:
    """Run the Typer application."""

    app()
