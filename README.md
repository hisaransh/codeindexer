# codebase-indexing

`codebase-indexing` is a local-first semantic code-search project. Its
installable command is named `codeindex`.

The current milestone provides command shells and validates that a supplied path
is the exact root of a Git worktree. It does not yet discover files, create an
index, persist data, search code, or report index status.

## Prerequisites

- Python 3.12 or newer
- Git available on `PATH`

## Development setup

Create and activate a virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
```

Install the project in editable mode with its test dependency:

```sh
python -m pip install -e ".[dev]"
```

## Commands

Each repository path is optional and defaults to the current directory. The
path must resolve to the repository root; a nested directory is rejected.

```sh
codeindex index [PATH]
codeindex search QUERY [PATH]
codeindex status [PATH]
```

The same CLI can be run as a module:

```sh
python -m codeindex --help
python -m codeindex index .
python -m codeindex search "where are failed jobs retried?" .
python -m codeindex status .
```

After validating the repository, each command currently prints a
`not implemented yet` placeholder and exits successfully.

## Tests

```sh
python -m pytest
```
