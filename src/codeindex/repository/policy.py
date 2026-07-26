"""Default safety and usefulness policy for tracked files."""

from pathlib import PurePosixPath
import re

from codeindex.repository.models import SkipReason


DEPENDENCY_DIRECTORIES = frozenset(
    {
        ".bundle",
        ".direnv",
        ".gradle",
        ".m2",
        ".nox",
        ".terraform",
        ".tox",
        ".venv",
        "bower_components",
        "env",
        "node_modules",
        "pods",
        "vendor",
        "venv",
    }
)

GENERATED_DIRECTORIES = frozenset(
    {
        ".cache",
        ".idea",
        ".mypy_cache",
        ".next",
        ".nuxt",
        ".parcel-cache",
        ".pytest_cache",
        ".ruff_cache",
        ".svelte-kit",
        ".vscode",
        "__pycache__",
        "__snapshots__",
        "build",
        "coverage",
        "dist",
        "htmlcov",
        "out",
        "site",
        "target",
    }
)

SAFE_ENVIRONMENT_TEMPLATES = frozenset(
    {".env.example", ".env.sample", ".env.template"}
)

SECRET_FILENAMES = frozenset(
    {
        ".env",
        ".envrc",
        ".netrc",
        ".npmrc",
        ".pypirc",
        "credentials.json",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "id_rsa",
        "secrets.json",
        "service-account.json",
    }
)

SECRET_SUFFIXES = (
    ".jks",
    ".key",
    ".keystore",
    ".p12",
    ".pem",
    ".pfx",
    ".tfstate",
    ".tfstate.backup",
)

GENERATED_FILENAMES = frozenset(
    {
        "bun.lock",
        "bun.lockb",
        "cargo.lock",
        "composer.lock",
        "gemfile.lock",
        "package-lock.json",
        "pnpm-lock.yaml",
        "poetry.lock",
        "uv.lock",
        "yarn.lock",
    }
)

GENERATED_SUFFIXES = (".map", ".min.css", ".min.js", ".snap")

GENERATED_DIRECTIVE_PATTERN = re.compile(
    r"(?m)^\s*(?:#|//|/\*+|\*|<!--)\s*@generated(?:\s|$)"
)

SUPPORTED_SUFFIXES = frozenset(
    {
        ".adoc",
        ".asm",
        ".bash",
        ".c",
        ".cc",
        ".cfg",
        ".clj",
        ".cljs",
        ".cljc",
        ".cmake",
        ".cjs",
        ".conf",
        ".cpp",
        ".cs",
        ".css",
        ".cxx",
        ".dart",
        ".erb",
        ".ex",
        ".exs",
        ".fs",
        ".fsx",
        ".go",
        ".gql",
        ".graphql",
        ".groovy",
        ".h",
        ".hbs",
        ".hh",
        ".hpp",
        ".hrl",
        ".hs",
        ".htm",
        ".html",
        ".hxx",
        ".ini",
        ".java",
        ".jl",
        ".js",
        ".json",
        ".jsonc",
        ".jsx",
        ".kt",
        ".kts",
        ".less",
        ".lua",
        ".m",
        ".md",
        ".mdx",
        ".mjs",
        ".mm",
        ".nix",
        ".php",
        ".pl",
        ".pm",
        ".properties",
        ".proto",
        ".ps1",
        ".py",
        ".pyi",
        ".r",
        ".rb",
        ".rs",
        ".rst",
        ".sass",
        ".scala",
        ".scss",
        ".sh",
        ".sol",
        ".sql",
        ".svelte",
        ".swift",
        ".tex",
        ".tf",
        ".tfvars",
        ".toml",
        ".ts",
        ".tsx",
        ".txt",
        ".vue",
        ".yaml",
        ".yml",
        ".zig",
    }
)

SUPPORTED_FILENAMES = frozenset(
    {
        ".dockerignore",
        ".editorconfig",
        ".env.example",
        ".env.sample",
        ".env.template",
        ".eslintignore",
        ".gitattributes",
        ".gitignore",
        ".npmignore",
        ".prettierignore",
        ".python-version",
        ".ruby-version",
        ".tool-versions",
        "brewfile",
        "build",
        "build.bazel",
        "cmakelists.txt",
        "dockerfile",
        "gemfile",
        "gnumakefile",
        "jenkinsfile",
        "justfile",
        "license",
        "makefile",
        "module.bazel",
        "procfile",
        "rakefile",
        "readme",
        "vagrantfile",
        "workspace",
        "workspace.bazel",
    }
)


def classify_path(relative_path: PurePosixPath) -> SkipReason | None:
    """Return a path-based exclusion reason, if one applies.

    Examples:
    - ``.env`` returns ``secret``.
    - ``vendor/library.py`` returns ``dependency``.
    - ``dist/app.js`` returns ``generated``.
    - ``src/app.py`` returns ``None`` and continues to content checks.
    """

    name = relative_path.name.casefold()
    parent_parts = {part.casefold() for part in relative_path.parts[:-1]}

    if _is_secret_name(name):
        return SkipReason.SECRET
    if parent_parts & DEPENDENCY_DIRECTORIES:
        return SkipReason.DEPENDENCY
    if parent_parts & GENERATED_DIRECTORIES:
        return SkipReason.GENERATED
    if (
        name in GENERATED_FILENAMES
        or name.endswith(GENERATED_SUFFIXES)
    ):
        return SkipReason.GENERATED
    return None


def is_generated_text(text: str) -> bool:
    """Return whether the beginning of text declares generated content.

    Examples:
    - ``"// @generated"`` returns ``True``.
    - ``"// Code generated by tool. DO NOT EDIT."`` returns ``True``.
    - ``"@generated_report = report"`` returns ``False``.
    - ``"# Hand-written application code"`` returns ``False``.
    """

    beginning = text[:4096].casefold()
    if GENERATED_DIRECTIVE_PATTERN.search(beginning):
        return True
    return "do not edit" in beginning and any(
        marker in beginning
        for marker in (
            "automatically generated",
            "code generated",
            "generated file",
        )
    )


def is_supported_file(relative_path: PurePosixPath, text: str) -> bool:
    """Return whether a decoded text file belongs to the curated file set.

    Examples that pass:
    - ``src/app.py`` because ``.py`` is a supported suffix.
    - ``app/views/users/show.html.erb`` because ``.erb`` is supported.
    - ``Dockerfile.dev`` because Dockerfile variants are recognized.
    - ``bin/codeindex`` when its text starts with a ``#!`` shebang.

    Examples that do not pass:
    - ``fixtures/events.data`` because ``.data`` is not supported.
    - ``assets/icon.svg`` and ``config/schema.xml`` are intentionally excluded.
    - ``NOTICE`` because an unknown extensionless file needs a shebang.
    """

    name = relative_path.name.casefold()
    if name in SUPPORTED_FILENAMES or name.startswith("dockerfile."):
        return True
    if relative_path.suffix.casefold() in SUPPORTED_SUFFIXES:
        return True
    return "." not in name and text.startswith("#!")


def _is_secret_name(name: str) -> bool:
    """Return whether a case-folded filename is secret by default.

    Examples:
    - ``".env.production"`` and ``"server.pem"`` return ``True``.
    - ``".env.example"`` and ``"settings.toml"`` return ``False``.
    """

    if name in SAFE_ENVIRONMENT_TEMPLATES:
        return False
    return (
        name in SECRET_FILENAMES
        or name.startswith(".env.")
        or name.endswith(SECRET_SUFFIXES)
    )
