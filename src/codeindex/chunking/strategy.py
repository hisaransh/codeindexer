"""Deterministic, parser-independent line-aware chunking."""

from collections.abc import Iterable, Iterator
import hashlib
import json
from pathlib import PurePosixPath

from codeindex.chunking.budget import (
    DEFAULT_TEXT_MEASURER,
    TextMeasurer,
)
from codeindex.chunking.errors import (
    ChunkBudgetError,
    TextMeasurementError,
)
from codeindex.chunking.models import (
    DEFAULT_CHUNKING_CONFIG,
    LINE_CHUNKING_STRATEGY_VERSION,
    CodeChunk,
    ChunkingConfig,
)
from codeindex.repository.models import DiscoveredFile


def chunk_file(
    discovered_file: DiscoveredFile,
    *,
    config: ChunkingConfig = DEFAULT_CHUNKING_CONFIG,
    measurer: TextMeasurer = DEFAULT_TEXT_MEASURER,
) -> Iterator[CodeChunk]:
    """Yield deterministic chunks from one accepted source file."""

    relative_path = PurePosixPath(discovered_file.relative_path)
    lines = discovered_file.text.splitlines(keepends=True)
    start_line_index = 0
    start_column = 0

    while start_line_index < len(lines):
        chunk_text, end_line_index, end_column = _next_chunk_text(
            lines,
            start_line_index=start_line_index,
            start_column=start_column,
            relative_path=relative_path,
            config=config,
            measurer=measurer,
        )

        if chunk_text.strip():
            yield _create_chunk(
                relative_path=relative_path,
                text=chunk_text,
                start_line=start_line_index + 1,
                start_column=start_column,
                end_line=end_line_index + 1,
                end_column=end_column,
                config=config,
                measurer=measurer,
            )

        if (
            end_line_index == len(lines) - 1
            and end_column == len(lines[end_line_index])
        ):
            break

        if end_column < len(lines[end_line_index]):
            start_line_index = end_line_index
            start_column = end_column
            continue

        spanned_lines = end_line_index - start_line_index + 1
        overlap_lines = min(config.overlap_lines, spanned_lines - 1)
        start_line_index = end_line_index - overlap_lines + 1
        start_column = 0


def iter_chunks(
    discovered_files: Iterable[DiscoveredFile],
    *,
    config: ChunkingConfig = DEFAULT_CHUNKING_CONFIG,
    measurer: TextMeasurer = DEFAULT_TEXT_MEASURER,
) -> Iterator[CodeChunk]:
    """Yield chunks file by file without combining source files."""

    for discovered_file in discovered_files:
        yield from chunk_file(
            discovered_file,
            config=config,
            measurer=measurer,
        )


def _next_chunk_text(
    lines: list[str],
    *,
    start_line_index: int,
    start_column: int,
    relative_path: PurePosixPath,
    config: ChunkingConfig,
    measurer: TextMeasurer,
) -> tuple[str, int, int]:
    """Return the next fitting source slice and its exclusive end column."""

    pieces: list[str] = []
    last_line_index = start_line_index
    last_end_column = start_column
    stop_line_index = min(
        len(lines),
        start_line_index + config.max_lines,
    )

    for line_index in range(start_line_index, stop_line_index):
        line_start = start_column if line_index == start_line_index else 0
        piece = lines[line_index][line_start:]
        candidate = "".join(pieces) + piece
        if _measure(candidate, measurer) <= config.max_units:
            pieces.append(piece)
            last_line_index = line_index
            last_end_column = len(lines[line_index])
            continue

        if pieces:
            break

        prefix_length = _largest_fitting_prefix(
            piece,
            max_units=config.max_units,
            measurer=measurer,
        )
        if prefix_length == 0:
            raise ChunkBudgetError(relative_path, start_line_index + 1)
        return (
            piece[:prefix_length],
            line_index,
            line_start + prefix_length,
        )

    return "".join(pieces), last_line_index, last_end_column


def _largest_fitting_prefix(
    text: str,
    *,
    max_units: int,
    measurer: TextMeasurer,
) -> int:
    """Return the longest fitting prefix for a prefix-monotonic measurer."""

    lower = 1
    upper = len(text)
    best = 0

    while lower <= upper:
        midpoint = (lower + upper) // 2
        if _measure(text[:midpoint], measurer) <= max_units:
            best = midpoint
            lower = midpoint + 1
        else:
            upper = midpoint - 1

    return best


def _measure(text: str, measurer: TextMeasurer) -> int:
    """Validate and return one external text measurement."""

    size = measurer.measure(text)
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise TextMeasurementError(measurer.name)
    return size


def _create_chunk(
    *,
    relative_path: PurePosixPath,
    text: str,
    start_line: int,
    start_column: int,
    end_line: int,
    end_column: int,
    config: ChunkingConfig,
    measurer: TextMeasurer,
) -> CodeChunk:
    """Create one chunk with an ID derived from its stable inputs."""

    identifier_payload = {
        "budget": {
            "max_units": config.max_units,
            "measurer": measurer.name,
        },
        "path": relative_path.as_posix(),
        "span": {
            "end_column": end_column,
            "end_line": end_line,
            "start_column": start_column,
            "start_line": start_line,
        },
        "strategy": {
            "max_lines": config.max_lines,
            "overlap_lines": config.overlap_lines,
            "version": LINE_CHUNKING_STRATEGY_VERSION,
        },
        "text": text,
    }
    encoded_payload = json.dumps(
        identifier_payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    chunk_id = hashlib.sha256(encoded_payload).hexdigest()

    return CodeChunk(
        chunk_id=chunk_id,
        relative_path=relative_path,
        text=text,
        start_line=start_line,
        start_column=start_column,
        end_line=end_line,
        end_column=end_column,
        strategy_version=LINE_CHUNKING_STRATEGY_VERSION,
    )
