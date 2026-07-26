# AGENTS.md

## Start here

This file is the operational guide for AI agents working in this repository.
Use it to navigate the checkout, make code changes, and verify work.

Read [`docs/vision.md`](docs/vision.md) before making decisions about product
behavior, architecture, dependencies, persistence, or scope. The vision is the
source of truth for those decisions; do not duplicate or reinterpret its product
scope here.

Before changing anything:

1. Run `git status --short` and preserve unrelated work.
2. Inspect `pyproject.toml` for the supported Python version, dependencies, and
   configured tools.
3. Use `rg --files` to understand the current tree rather than assuming a
   package layout.
4. Read the files on the execution path being changed.
5. Search for tests, fixtures, documentation, and callers related to that path.

## Current repository map

The checkout is still intentionally small. Keep this section accurate as the
structure changes.

| Path | Role |
| --- | --- |
| `src/codeindex/cli.py` | Typer command definitions, terminal rendering, and CLI exit-status translation. |
| `src/codeindex/repository/errors.py` | Expected repository validation and discovery error hierarchy and user-facing messages. |
| `src/codeindex/repository/models.py` | Typed repository, tracked-file, discovery-decision, skip-reason, and summary values. |
| `src/codeindex/repository/resolver.py` | Filesystem path validation and exact-root enforcement. |
| `src/codeindex/repository/gitops.py` | Git root lookup, deterministic index enumeration, output parsing, and entry classification. |
| `src/codeindex/repository/policy.py` | Curated supported-file and default exclusion policy. |
| `src/codeindex/repository/discovery.py` | Lazy working-tree inspection, filtering, and discovery summarization. |
| `src/codeindex/__main__.py` | `python -m codeindex` entry point. |
| `tests/` | Pytest unit, CLI, and Git adapter integration coverage. |
| `README.md` | Prerequisites, editable installation, command examples, limitations, and test command. |
| `pyproject.toml` | Python and package metadata, Hatchling build configuration, dependencies, console script, and pytest configuration. |
| `docs/vision.md` | Product, scope, architecture, and open-decision source of truth. |
| `.gitignore` | Repository exclusions for Python artifacts, local environments, secrets, editor files, and local index data. |

The project uses Typer at the CLI boundary, Hatchling for builds, and pytest for
tests. Git remains the tracked-file discovery adapter; no ignore-matching
dependency is currently installed. Run `python -m pytest` for the configured
automated verification. There is currently no formatter, linter, type checker,
or committed dependency lock file. Do not refer to one as if it exists. When
adding any of these, update this map and document the exact commands
contributors should run.

## How to navigate a task

Trace changes through the relevant technical path instead of editing only the
most visible file:

```text
CLI input
  -> argument validation
  -> application operation
  -> filesystem / embedding / persistence boundary
  -> typed result or domain error
  -> CLI rendering and exit status
```

For indexing work, inspect discovery, validation, chunking, embedding, storage,
and rebuild behavior.

For search work, inspect query embedding, vector retrieval, result mapping, and
output formatting.

For status work, inspect repository identity, persisted metadata, and CLI
presentation.

If the named module does not exist yet, identify the smallest technical boundary
the change needs. Do not scaffold unrelated layers in anticipation of future
work.

## Code boundaries

Keep these concerns separable and independently testable:

- CLI parsing and terminal presentation
- application orchestration
- repository identity and filesystem discovery
- file safety checks and text decoding
- deterministic, line-aware chunking
- embedding generation
- vector persistence and retrieval
- result and status formatting

The CLI layer should translate user input into application calls and render
results. It should not contain discovery, chunking, embedding, or persistence
logic.

Keep terminal output out of business logic. Return typed values from normal
operations and raise specific domain errors for expected failures; translate
those errors to concise messages and non-zero exit codes only at the CLI
boundary.

Use small protocols or injected callables at filesystem, embedder, clock, and
vector-store boundaries when doing so makes tests deterministic. Avoid service
locators, global mutable clients, deep class hierarchies, and abstractions with
only hypothetical consumers.

Keep external-library types inside their adapters where practical. Core models
should use standard Python types so discovery, chunking, IDs, and formatting can
be unit-tested without loading embedding or database libraries.

When a domain grows beyond a focused module, promote it to a package and
separate errors, typed values, and boundary logic into focused modules. Preserve
a small, stable public API through the package's `__init__.py` so callers do not
depend on its internal layout. For example, `codeindex.repository` keeps
validation errors in `errors.py`, typed values in `models.py`, and Git and
filesystem inspection in `resolver.py`, while its `__init__.py` exposes the
public repository API.

## Data and persistence rules

Treat persisted data as a compatibility boundary:

- Centralize schema and metadata keys rather than scattering string literals.
- Version behavior that affects generated chunks or embeddings.
- Make identifiers deterministic from documented stable inputs.
- Keep repository-level metadata separate from chunk-level metadata.
- Store repository-relative paths in chunk and result records.
- Define rebuild failure behavior at the persistence boundary and ensure a
  successful rebuild cannot retain stale records.
- Validate model name, vector dimension, and strategy versions before querying
  an existing index.

Any change that alters persisted fields, identifier inputs, collection layout,
or compatibility behavior requires corresponding tests and documentation.

## Filesystem trust boundary

Assume repository contents are untrusted.

- Use `pathlib.Path` for paths.
- Resolve the repository root once and make containment checks explicit.
- Do not mutate the repository being indexed.
- Do not follow a symlink until its resolved target is known to remain within
  the root.
- Apply ignore, directory, secret, size, binary, and decoding checks in a
  predictable order.
- Distinguish an intentionally skipped file from an unexpected read failure.
- Avoid logging raw source content, secrets, embeddings, or full absolute paths.
- Keep index data, model caches, and temporary artifacts outside the indexed
  repository.

Filesystem tests should use temporary directories and cover both accepted and
rejected paths. Do not rely on the developer's real repositories or global Git
configuration.

## Python conventions

- Support the Python version declared in `pyproject.toml`.
- Prefer the standard library when it is clear and sufficient.
- Add type hints to public functions and meaningful internal boundaries.
- Prefer frozen dataclasses or other small typed records for values passed
  between pipeline stages.
- Keep functions focused and names explicit.
- Catch only exceptions that can be translated, enriched with useful context,
  or recovered from at that boundary.
- Preserve exception chaining with `raise ... from error` when translating an
  error.
- Avoid broad `except Exception` in domain code.
- Use explicit text encodings.
- Avoid import-time filesystem access, model loading, database connections, or
  other expensive side effects.

Add dependencies deliberately through `pyproject.toml`. Before introducing one,
check whether the standard library is sufficient, whether it works offline
after installation, and whether it belongs at a replaceable external boundary.
Do not introduce a package manager or development tool without configuring and
documenting it.

## Testing strategy

Every behavior change needs proportionate automated verification.

- Unit-test pure transformations such as filtering, chunk ranges, identifiers,
  metadata conversion, and formatting.
- Test expected failures and public error messages, not only successful paths.
- Use fakes for embedders and vector stores in the default unit suite.
- Keep model downloads and network access out of default tests.
- Add adapter-level integration tests for external libraries.
- Test rebuild idempotency and removal of stale records at the persistence
  boundary.
- Assert exact repository-relative paths and line ranges in search results.

Before reporting completion, inspect `pyproject.toml` and repository
documentation again, then run only the test, format, lint, and type-check
commands actually configured there. If no relevant automated command exists,
say so explicitly and report the narrower verification performed.

## CLI changes

When changing the command line:

- Check `--help`, successful output, invalid input, stderr, and exit status.
- Keep parsing and presentation thin.
- Send normal results to stdout and diagnostics to stderr.
- Do not expose tracebacks for expected user errors.
- Use repository-relative paths in user-facing results when possible.
- Keep examples synchronized with actual behavior.

## Documentation ownership

Put information in the document that owns it:

- Product behavior, scope, architecture decisions, and open decisions:
  `docs/vision.md`
- Setup, installation, and user-facing command examples: `README.md` once it
  exists
- Dependency and tool configuration: `pyproject.toml`
- Persisted schema and compatibility notes: a dedicated technical document once
  persistence exists
- Agent navigation, implementation constraints, and verification workflow:
  `AGENTS.md`

Do not silently settle an open decision from `docs/vision.md` in code. If a task
depends on one, present the concrete technical tradeoff and request direction.

## Git and workspace hygiene

- Preserve unrelated user changes, including untracked files.
- Keep generated indexes, caches, models, virtual environments, IDE metadata,
  environment files, and secrets out of source control.
- Do not commit, amend, rebase, push, or open a pull request unless explicitly
  asked.
- Avoid destructive Git commands.
- Review the final diff for accidental absolute paths, credentials, generated
  files, and unrelated edits.

## Completion checklist

Before handing work back:

1. Re-read the changed execution path and its callers.
2. Confirm new behavior is covered by focused tests.
3. Run every relevant configured verification command.
4. Check expected CLI failures if the CLI changed.
5. Review `git diff --check` and `git diff`.
6. Update the repository map or technical documentation if structure,
   commands, or persistence changed.
7. Report what changed, what was verified, and any unresolved decision or risk.
