# codebase-indexing

`codebase-indexing` is a local-first semantic code-search project. Its
installable command is named `codeindex`.

The current milestone validates that a supplied path is the exact root of a Git
worktree, discovers safe Git-tracked text files, and reports why other tracked
paths were skipped. It does not yet chunk files, create or persist an index,
search code, or report index status.

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

Alternatively, use the committed `uv.lock` for a reproducible environment:

```sh
uv sync --extra dev
```

## Commands

Each repository path is optional and defaults to the current directory. The
path must resolve to the repository root; a nested directory is rejected.

```sh
codeindex index [PATH]
codeindex index --verbose [PATH]
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

`index` reads current working-tree contents for tracked paths, including
unstaged modifications. It ignores untracked files and skips deleted paths,
symlinks, submodules, unresolved merge entries, secrets, dependency and
generated content, files over 1 MiB, binaries, unsupported encodings, empty
files, and unknown file types.

Its output is a deterministic summary:

```text
Candidates: 18
Accepted: 12
Skipped: 6
Skipped by reason: binary=1, generated=3, secret=2
Index creation is not implemented yet.
```

Use `--verbose` or `-v` to list every skipped repository-relative path and its
reason:

```text
Skipped files:
  binary: "assets/logo.png"
  generated: "dist/app.min.js"
  unsupported_type: "fixtures/events.data"
```

Paths are quoted and control characters are escaped so unusual repository
filenames cannot alter terminal output.

The accepted file set is a curated collection of common source, script, web,
markup, documentation, configuration, and infrastructure formats. Safe
environment templates such as `.env.example` are accepted, but secret
filtering remains filename-based and cannot guarantee that arbitrary source
files contain no credentials. Rails ERB templates are supported; SVG and XML
files remain excluded.

`search` and `status` continue to print their `not implemented yet`
placeholders after repository validation.

## Tests

```sh
python -m pytest
```

With `uv`:

```sh
uv run python -m pytest
```
