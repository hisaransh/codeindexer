"""Command-line interface for codeindex."""

from pathlib import Path
from typing import Annotated

import typer

from codeindex.repository.errors import RepositoryError
from codeindex.repository.resolver import resolve_repository


app = typer.Typer(
    help="Index and search local source repositories.",
    no_args_is_help=True,
)

RepositoryPath = Annotated[
    Path,
    typer.Argument(help="Exact root of the Git repository.", metavar="PATH"),
]


def _validate_and_render(path: Path, placeholder: str) -> None:
    try:
        resolve_repository(path)
    except RepositoryError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=2) from error

    typer.echo(placeholder)


@app.command()
def index(path: RepositoryPath = Path(".")) -> None:
    """Prepare to index a repository."""

    _validate_and_render(path, "The index command is not implemented yet.")


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
    app()
