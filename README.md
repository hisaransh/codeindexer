# `codeindex`

> Find code by intent—locally, safely, and with a trail back to the exact lines.

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`codeindex` is an open-source, local-first semantic search tool for source
repositories. The goal is simple: ask questions in plain language and get
useful code locations instead of generated guesses.

```text
$ codeindex search "where do we retry failed payments?" ~/projects/payments

1. src/payments/retry.py:42-86              score: 0.84
2. src/workers/payment_worker.py:18-57
3. tests/test_payment_retry.py:91-130
```

The example above is the destination. The project is currently building the
foundation: safe Git-tracked file discovery and deterministic, line-aware
chunking are working; embedding, persistence, search results, and index status
are the next milestones.

## Why `codeindex`?

Code search usually makes you choose between exact text matching and sending a
repository to a hosted service. `codeindex` is designed for a different middle
ground:

- **Search by meaning.** Find a retry path without knowing that it is called
  `PaymentRetryWorker`.
- **Stay local.** Source, chunks, embeddings, and indexes remain on your
  machine.
- **Verify every result.** Matches point to repository-relative paths and exact
  line ranges.
- **Treat repositories as untrusted.** Secret-shaped files, binaries, generated
  output, oversized files, symlinks, and submodules are excluded by default.
- **Leave no footprint.** Index data belongs outside the repository being
  searched.

## What works today

| Capability | Status |
| --- | --- |
| Exact Git repository-root validation | Ready |
| Safe, deterministic tracked-file discovery | Ready |
| Skip summaries and verbose per-file reasons | Ready |
| Traceable `line-v1` chunking | Ready |
| Local embeddings and vector persistence | Planned |
| Natural-language search results | Planned |
| Repository index status | Planned |

The current pipeline is:

```text
Git index
   │
   ▼
tracked paths ──► safety policy ──► working-tree text ──► line-aware chunks
                      │
                      └──► stable skip reasons
```

## Try the current milestone

### Requirements

- Python 3.12 or newer
- Git available on `PATH`

### Install for development

Clone the repository, then use the committed lockfile:

```sh
uv sync --extra dev
uv run codeindex --help
```

Or use a standard virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
codeindex --help
```

### Prepare a repository

Pass the exact root of a local Git worktree. Omitting the path uses the current
directory.

```sh
codeindex index ~/projects/payments
```

The command reads current working-tree content for tracked files, including
unstaged edits, and prints a deterministic summary:

```text
Candidates: 18
Accepted: 12
Chunks: 47
Skipped: 6
Skipped by reason: binary=1, generated=3, secret=2
Embedding and index persistence are not implemented yet.
```

Want to audit the safety decisions? Add `--verbose` (or `-v`):

```sh
codeindex index --verbose ~/projects/payments
```

```text
Skipped files:
  binary: "assets/logo.png"
  generated: "dist/app.min.js"
  unsupported_type: "fixtures/events.data"
```

Paths are quoted and control characters are escaped, so unusual filenames
cannot manipulate terminal output.

## How discovery stays safe

`codeindex` starts from Git's index and reads one accepted working-tree file at
a time. It includes modified tracked files, while untracked files and deleted
tracked paths are ignored.

The default policy skips:

- symlinks, submodules, and unresolved merge entries;
- secrets and private-key-shaped filenames;
- dependency, cache, build, and generated content;
- files larger than 1 MiB;
- binary, empty, non-UTF-8, and unsupported files.

The accepted set is deliberately curated across common source, script, web,
markup, documentation, configuration, and infrastructure formats. Safe
templates such as `.env.example` are accepted. Secret filtering is
filename-based protection, however, and cannot guarantee that arbitrary source
text contains no credentials.

## Traceable chunking

Accepted files flow into the versioned `line-v1` strategy. Each chunk preserves
its repository-relative path, exact text, line range, and—when a long line must
be split—its column span.

- At most 50 source lines per chunk
- A 2,000 Unicode code-point budget
- Up to 10 complete overlapping lines between neighboring chunks
- Deterministic identifiers derived from the path, span, text, configuration,
  budget measurer, and strategy version
- Streaming file-by-file processing instead of retaining repository contents

The code-point budget is a dependency-free placeholder. The embedding milestone
will replace it with the selected model's tokenizer and version the resulting
strategy change.

## Command reference

```sh
codeindex index [PATH]
codeindex index --verbose [PATH]
codeindex search QUERY [PATH]
codeindex status [PATH]
```

You can also run the package as a module:

```sh
python -m codeindex --help
python -m codeindex index .
```

`search` and `status` currently validate the repository and then report that
their implementation is still pending.

## Develop and verify

Run the complete test suite with the locked environment:

```sh
uv run python -m pytest
```

Or, from an activated development environment:

```sh
python -m pytest
```

The product direction, architectural boundaries, deliberate limitations, and
open decisions live in [`docs/vision.md`](docs/vision.md).

## License

`codeindex` is available under the [MIT License](LICENSE).
