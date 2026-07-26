# Codebase Indexing: Product and Technical Vision

Status: Draft

Last updated: July 26, 2026

## Product vision

Build a local-first command-line tool that indexes source repositories and lets
developers find relevant code using natural-language queries.

The core product is a search tool, not initially an AI agent or repository
chatbot.

An example experience:

```text
codeindex index ~/projects/payments

codeindex search "where do we retry failed payments?"
```

Search results should point back to actual source locations:

```text
1. src/payments/retry.py:42-86       score: 0.84
2. src/workers/payment_worker.py:18-57
3. tests/test_payment_retry.py:91-130
```

## Product principles

- Local-first: source code, chunk text, and embeddings remain on the user's
  machine.
- Traceable: every result includes a file path and accurate line range.
- Search before generation: retrieval quality must be useful and measurable
  before adding LLM-generated answers.
- Safe by default: secrets, binaries, generated files, and ignored files should
  not be indexed accidentally.
- Repository-neutral: indexing must not modify or pollute the target
  repository.
- Replaceable components: embedding, chunking, storage, and ranking choices
  should be isolated behind clear boundaries.

## MVP

The MVP should prove one capability: semantic search returns useful, traceable
code results from a local repository.

### `index <path>`

- Enumerate Git-tracked paths and read their current working-tree contents.
- Ignore untracked files, deleted paths, symlinks, and submodule entries.
- Skip binaries, generated directories, dependency directories, secrets, and
  oversized files.
- Break files into line-aware chunks.
- Generate embeddings locally.
- Persist chunks and embeddings in ChromaDB.

### `search <query>`

- Embed the natural-language query.
- Retrieve the top matching chunks.
- Print the relative file path, line range, relevance score, and an excerpt.

### `status <path>`

- Show whether the repository is indexed.
- Show file and chunk counts.
- Show the last indexing time.
- Show the embedding model and chunking version.

### Safe full reindexing

- Re-running `index` must not create duplicate chunks.
- Rebuilding the complete repository is acceptable for the MVP.
- Incremental updates are intentionally deferred.

### Tracked-file discovery decision

The MVP discovers unique paths from Git's index and reads their current
working-tree contents. Modified tracked files are included. Untracked files,
deleted tracked paths, symlinks, submodules, and unresolved merge entries are
not indexed.

Discovery targets repositories containing up to 10,000 tracked paths and
approximately 250 MiB of accepted text. Paths may be held as metadata, but file
contents must be processed one at a time rather than loading a repository into
memory.

The default per-file limit is 1 MiB. Files must contain non-whitespace UTF-8
text, with an optional UTF-8 byte-order mark. NUL-containing files are treated
as binary.

The initial curated file set includes common:

- Source-code and shell extensions
- Web, markup, and documentation extensions
- Configuration and infrastructure extensions
- Extensionless build and project files such as `Dockerfile`, `Makefile`,
  `CMakeLists.txt`, `Gemfile`, `Jenkinsfile`, Bazel files, `README`, and
  `LICENSE`
- Extensionless scripts with a shebang

The supported suffixes are:

```text
.adoc .asm .bash .c .cc .cfg .cjs .clj .cljs .cljc .cmake .conf
.cpp .cs .css .cxx .dart .erb .ex .exs .fs .fsx .go .gql .graphql
.groovy .h .hbs .hh .hpp .hrl .hs .htm .html .hxx .ini .java .jl
.js .json .jsonc .jsx .kt .kts .less .lua .m .md .mdx .mjs .mm
.nix .php .pl .pm .properties .proto .ps1 .py .pyi .r .rb .rs .rst
.sass .scala .scss .sh .sol .sql .svelte .swift .tex .tf .tfvars
.toml .ts .tsx .txt .vue .yaml .yml .zig
```

The recognized filenames are:

```text
.dockerignore .editorconfig .env.example .env.sample .env.template
.eslintignore .gitattributes .gitignore .npmignore .prettierignore
.python-version .ruby-version .tool-versions Brewfile BUILD BUILD.bazel
CMakeLists.txt Dockerfile Gemfile GNUmakefile Jenkinsfile Justfile LICENSE
Makefile MODULE.bazel Procfile Rakefile README Vagrantfile WORKSPACE
WORKSPACE.bazel
```

Matching is case-insensitive, and names beginning with `Dockerfile.` are also
supported. SVG and XML files are intentionally excluded.

Unknown text formats are skipped as unsupported rather than indexed
automatically.

The built-in exclusion policy is conservative:

- Dependency directories: `.bundle`, `.direnv`, `.gradle`, `.m2`, `.nox`,
  `.terraform`, `.tox`, `.venv`, `bower_components`, `env`, `node_modules`,
  `Pods`, `vendor`, and `venv`
- Generated or noisy directories: `.cache`, `.idea`, `.mypy_cache`, `.next`,
  `.nuxt`, `.parcel-cache`, `.pytest_cache`, `.ruff_cache`, `.svelte-kit`,
  `.vscode`, `__pycache__`, `__snapshots__`, `build`, `coverage`, `dist`,
  `htmlcov`, `out`, `site`, and `target`
- Generated files: `bun.lock`, `bun.lockb`, `Cargo.lock`, `composer.lock`,
  `Gemfile.lock`, `package-lock.json`, `pnpm-lock.yaml`, `poetry.lock`,
  `uv.lock`, `yarn.lock`, source maps, snapshots, minified JavaScript and CSS,
  and files declaring a generated-code marker
- Secret filenames: `.env`, `.env.*`, `.envrc`, `.netrc`, `.npmrc`, `.pypirc`,
  `credentials.json`, `secrets.json`, `service-account.json`, `id_dsa`,
  `id_ecdsa`, `id_ed25519`, and `id_rsa`
- Secret suffixes: `.jks`, `.key`, `.keystore`, `.p12`, `.pem`, `.pfx`,
  `.tfstate`, and `.tfstate.backup`

`.env.example`, `.env.sample`, and `.env.template` are explicitly safe
configuration templates. Secret filtering is filename-based protection, not a
guarantee that arbitrary source or configuration text contains no credentials.
Every excluded tracked path receives one stable skip reason for reporting.
`codeindex index --verbose` prints each skipped repository-relative path and
reason using terminal-safe escaping.

### Deliberate MVP limitations

- One explicitly supported embedding model.
- Plain text and line-aware chunking rather than syntax-tree chunking.
- Semantic retrieval only.
- No file watcher.
- No LLM-generated answers.
- No dependency or call graph.
- No remote repositories.
- macOS and Linux first.
- Search one repository at a time.

## High-level architecture

```text
Repository
    |
    v
File discovery and ignore rules
    |
    v
Text and binary validation
    |
    v
Chunking with line-number preservation
    |
    v
Local embedding model
    |
    v
ChromaDB persistent collection
    |
    v
Top-k retrieval
    |
    v
CLI result formatting
```

The indexing and search flows share the same embedding model:

```text
Indexing:
source chunk -> embedder -> vector -> ChromaDB

Searching:
query text   -> embedder -> vector -> ChromaDB nearest-neighbour query
```

## Stored chunk model

Each indexed chunk should retain enough information to reproduce and explain a
search result:

- Repository identifier
- Relative file path
- Start and end line numbers
- Programming language or file type
- File content hash
- Chunk text
- Deterministic chunk identifier
- Embedding model name and version
- Chunking strategy version

Chunk identifiers should be derived from stable inputs such as repository,
relative path, and content or chunk hash. This enables duplicate prevention and
safe replacement during reindexing.

## Semantic search

Semantic search embeds repository chunks and queries into the same vector space,
then retrieves the closest chunks.

It is useful for conceptual questions such as:

- "Where is authentication checked?"
- "How are failed jobs retried?"
- "Which code refreshes expired tokens?"

### Embedding model

The MVP should use a small local Sentence Transformers model. A lightweight
general-purpose model is sufficient to prove the indexing and retrieval
pipeline. Code-specific models should be evaluated later rather than assumed to
be better.

The embedding layer should be owned by the application rather than hidden
inside ChromaDB:

- The application explicitly embeds both documents and queries.
- ChromaDB receives and searches vectors.
- Model changes are visible and versioned.
- Indexing and querying cannot silently use different models.
- The embedder can be replaced without redesigning storage or CLI code.

"Local" means inference is performed on the user's machine. The model may still
need to be downloaded once unless it is bundled or already cached.

### Chunking

The MVP should use line-aware chunks:

- Approximately 30-60 lines per chunk.
- A small overlap between adjacent chunks.
- Exact source line ranges are preserved.
- Chunks never combine content from different files.
- Abnormally large functions or lines cannot exceed the embedding model's input
  limit.

This strategy may split functions or separate a method from its class. That
tradeoff is acceptable while validating retrieval.

The final version should use Tree-sitter to chunk around language constructs
such as functions, methods, classes, and modules.

### Semantic and keyword search

Pure semantic search is not sufficient for source code.

Semantic search is strong for concepts and intent. Keyword search is often
stronger for exact identifiers, error messages, configuration keys, and symbol
names.

Examples that favor exact search:

- `PaymentRetryWorker`
- `ERR_CONNECTION_RESET`
- `refresh_access_token`

The MVP will start with semantic retrieval. The final product should combine
semantic and lexical result lists using a straightforward fusion strategy such
as reciprocal-rank fusion. Reranking should only be added after evaluation shows
that first-stage retrieval needs it.

## Index storage

Indexes should be stored outside the target repository in a platform-appropriate
application data directory, conceptually:

```text
~/.local/share/codeindex/
```

This avoids:

- Polluting Git status.
- Accidentally indexing the vector database.
- Requiring changes to the source repository.
- Scattering indexes across multiple repositories.

The initial design should use one ChromaDB collection per repository and keep a
mapping from the canonical repository path to a stable repository identifier.

The index metadata must record the embedding model and chunking strategy
versions. Changing either should require a rebuild.

## Final scope

A mature local code-search tool should include:

- Multiple indexed repositories.
- Incremental indexing using file hashes.
- Detection and removal of deleted or renamed files.
- `.gitignore` plus user-defined include and exclude rules.
- Syntax-aware chunking through Tree-sitter.
- Hybrid semantic and exact-text search.
- Language, directory, and file-type filters.
- Configurable embedding models.
- Result reranking where evaluation supports it.
- Human-readable and JSON output.
- Progress reporting and useful diagnostics.
- Repository index listing, inspection, and deletion.
- Model and chunking version migrations.
- macOS, Linux, and Windows support.
- A repeatable relevance evaluation suite.
- Strong handling of binaries, encodings, symlinks, and large files.

## Good-to-have features

- `--include` and `--exclude` search filters.
- `--language python`.
- `--path src/payments`.
- Configurable surrounding context lines.
- Interactive selection that opens a result in an editor.
- `--json` output for scripts and editor integrations.
- Index statistics by language and directory.
- User configuration with optional repository overrides.
- Background incremental updates.
- Search across several selected repositories.
- Shell completion.
- Optional code-specific embedding models.

## Brownie features

- Generate answers with file and line citations.
- Build a repository graph for imports, definitions, references, and callers.
- Find code similar to a selected snippet.
- Search changes between two Git revisions.
- Include Git blame and commit history in results.
- Provide IDE extensions.
- Offer a terminal UI with live search.
- Watch repositories and update their indexes immediately.
- Run a local reranking model.
- Support natural-language filters such as "only Python tests."
- Expose an MCP or server interface for coding agents.
- Generate a navigable map of modules and their relationships.

## Security and privacy

The persisted index can contain source text and secrets even when everything
runs locally.

Safe defaults should:

- Exclude `.env`, private keys, credentials, and common secret files.
- Restrict initial discovery to paths already tracked by Git.
- Avoid following symlinks outside the selected repository.
- Enforce file-size limits.
- Store indexes with user-only permissions.
- Make index deletion explicit and reliable.
- Tell users that raw chunk text is persisted to support result excerpts.

If generated answers are added later, repository content must also be treated as
untrusted input because it may contain prompt-injection instructions. That
threat is outside the search-only MVP.

## Proposed Python stack

- Python 3.12+
- ChromaDB for vector persistence and nearest-neighbour retrieval
- Sentence Transformers for the initial local embedder
- `pathspec` for future Git-style user include and exclude rules
- Typer for a multi-command CLI
- `platformdirs` for platform-appropriate index storage
- `pytest` for verification
- Tree-sitter after the MVP for syntax-aware chunking

`argparse` remains a viable alternative if minimizing CLI dependencies is more
important than Typer's command structure and user experience.

### CLI framework decision

The initial CLI uses Typer. Its multi-command help and type-driven interface
outweigh the cost of one additional runtime dependency for this project.
Repository validation remains independent of Typer so it can be tested and
reused without loading the CLI framework.

## MVP success criteria

The MVP is successful when:

- A repository can be indexed without modifying it.
- Binary, ignored, generated, and secret files are excluded.
- Reindexing creates no duplicate chunks.
- Every result has the correct relative file path and line range.
- Search works offline after the embedding model is available locally.
- A small benchmark of real repository questions finds an acceptable result in
  the top five.
- Unsupported encodings, unreadable paths, corrupt indexes, and other expected
  failures produce understandable CLI errors.

Retrieval quality should be evaluated with a small, versioned collection of
queries and expected files or code regions. New features should improve this
benchmark rather than merely make the architecture more sophisticated.

## Current product decision

The MVP returns ranked search results with excerpts and line citations. It does
not generate answers.

This keeps retrieval quality measurable and gives future question-answering
features a dependable foundation.

## Open decisions

The following decisions remain:

1. Which embedding model will be the first supported default?
2. What benchmark repositories and questions will measure retrieval quality?

## References

- [Chroma collection API](https://docs.trychroma.com/reference/python/collection)
- [Sentence Transformers semantic search](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html)
- [Tree-sitter documentation](https://tree-sitter.github.io/tree-sitter/)
