from collections.abc import Iterator
from pathlib import PurePosixPath

import pytest

from codeindex.chunking import (
    LINE_CHUNKING_STRATEGY_VERSION,
    ChunkBudgetError,
    ChunkingConfig,
    TextMeasurementError,
    chunk_file,
    iter_chunks,
)
from codeindex.repository import DiscoveredFile


def discovered(path: str, text: str) -> DiscoveredFile:
    return DiscoveredFile(
        relative_path=PurePosixPath(path),
        text=text,
        size_bytes=len(text.encode("utf-8")),
    )


def source_slice(
    source: str,
    *,
    start_line: int,
    start_column: int,
    end_line: int,
    end_column: int,
) -> str:
    lines = source.splitlines(keepends=True)
    if start_line == end_line:
        return lines[start_line - 1][start_column:end_column]
    return "".join(
        (
            lines[start_line - 1][start_column:],
            *lines[start_line:end_line - 1],
            lines[end_line - 1][:end_column],
        )
    )


def test_short_file_becomes_one_traceable_chunk() -> None:
    source = "alpha = 1\nbeta = 2\n"

    chunks = list(chunk_file(discovered("src/app.py", source)))

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.relative_path == PurePosixPath("src/app.py")
    assert chunk.text == source
    assert (
        chunk.start_line,
        chunk.start_column,
        chunk.end_line,
        chunk.end_column,
    ) == (1, 0, 2, len("beta = 2\n"))
    assert chunk.strategy_version == LINE_CHUNKING_STRATEGY_VERSION
    assert len(chunk.chunk_id) == 64
    assert source_slice(
        source,
        start_line=chunk.start_line,
        start_column=chunk.start_column,
        end_line=chunk.end_line,
        end_column=chunk.end_column,
    ) == chunk.text


@pytest.mark.parametrize("source", ["", " \n\t\n"])
def test_empty_and_whitespace_only_text_produce_no_chunks(source: str) -> None:
    assert list(chunk_file(discovered("empty.txt", source))) == []


def test_line_boundary_and_overlap_are_exact() -> None:
    source = "".join(f"line {number}\n" for number in range(1, 52))
    config = ChunkingConfig(max_lines=50, overlap_lines=10, max_units=2_000)

    chunks = list(chunk_file(discovered("large.py", source), config=config))

    assert [(chunk.start_line, chunk.end_line) for chunk in chunks] == [
        (1, 50),
        (41, 51),
    ]
    assert chunks[0].text.endswith("line 50\n")
    assert chunks[1].text.startswith("line 41\n")


def test_budget_accepts_exact_size_and_splits_one_code_point_over() -> None:
    exact = list(
        chunk_file(
            discovered("exact.txt", "abcde"),
            config=ChunkingConfig(
                max_lines=50,
                overlap_lines=0,
                max_units=5,
            ),
        )
    )
    split = list(
        chunk_file(
            discovered("split.txt", "abcdef"),
            config=ChunkingConfig(
                max_lines=50,
                overlap_lines=0,
                max_units=5,
            ),
        )
    )

    assert [chunk.text for chunk in exact] == ["abcde"]
    assert [chunk.text for chunk in split] == ["abcde", "f"]
    assert [
        (chunk.start_column, chunk.end_column)
        for chunk in split
    ] == [(0, 5), (5, 6)]


def test_long_unicode_line_splits_with_exact_columns_and_line_endings() -> None:
    source = "αβγδε\r\n"
    config = ChunkingConfig(max_lines=10, overlap_lines=2, max_units=4)

    chunks = list(
        chunk_file(
            discovered("unicode.py", source),
            config=config,
        )
    )

    assert [chunk.text for chunk in chunks] == ["αβγδ", "ε\r\n"]
    assert [
        (
            chunk.start_line,
            chunk.start_column,
            chunk.end_line,
            chunk.end_column,
        )
        for chunk in chunks
    ] == [(1, 0, 1, 4), (1, 4, 1, 7)]
    assert "".join(chunk.text for chunk in chunks) == source


def test_every_chunk_matches_its_recorded_source_span() -> None:
    source = "".join(
        (
            "first\r\n",
            "x" * 13,
            "\n",
            "third\n",
            "fourth",
        )
    )
    config = ChunkingConfig(max_lines=2, overlap_lines=1, max_units=10)

    chunks = list(chunk_file(discovered("mixed.txt", source), config=config))

    assert chunks
    for chunk in chunks:
        assert source_slice(
            source,
            start_line=chunk.start_line,
            start_column=chunk.start_column,
            end_line=chunk.end_line,
            end_column=chunk.end_column,
        ) == chunk.text
        assert len(chunk.text) <= config.max_units


def test_large_function_uses_default_fifty_line_windows() -> None:
    source = "".join(f"statement_{line}\n" for line in range(1, 121))

    chunks = list(chunk_file(discovered("service.py", source)))

    assert [(chunk.start_line, chunk.end_line) for chunk in chunks] == [
        (1, 50),
        (41, 90),
        (81, 120),
    ]


def test_repeated_chunking_produces_identical_chunks_and_ids() -> None:
    source_file = discovered(
        "src/retry.py",
        "".join(f"attempt_{line}\n" for line in range(1, 70)),
    )

    first = list(chunk_file(source_file))
    second = list(chunk_file(source_file))

    assert first == second


def test_configuration_and_text_changes_change_chunk_ids() -> None:
    source_file = discovered("src/app.py", "app = True\n")

    default_chunk = next(chunk_file(source_file))
    configured_chunk = next(
        chunk_file(
            source_file,
            config=ChunkingConfig(
                max_lines=40,
                overlap_lines=5,
                max_units=1_500,
            ),
        )
    )
    changed_text_chunk = next(
        chunk_file(discovered("src/app.py", "app = False\n"))
    )

    assert len(
        {
            default_chunk.chunk_id,
            configured_chunk.chunk_id,
            changed_text_chunk.chunk_id,
        }
    ) == 3


def test_iter_chunks_remains_lazy_and_never_combines_files() -> None:
    observations: list[str] = []

    def files() -> Iterator[DiscoveredFile]:
        observations.append("first")
        yield discovered("first.py", "first = True\n")
        observations.append("second")
        yield discovered("second.py", "second = True\n")

    chunks = iter_chunks(files())
    first_chunk = next(chunks)

    assert observations == ["first"]
    assert first_chunk.relative_path == PurePosixPath("first.py")

    remaining_chunks = list(chunks)

    assert observations == ["first", "second"]
    assert {
        chunk.relative_path for chunk in remaining_chunks
    } == {PurePosixPath("second.py")}


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_lines": 0}, "max_lines must be positive"),
        ({"overlap_lines": -1}, "overlap_lines cannot be negative"),
        (
            {"max_lines": 10, "overlap_lines": 10},
            "overlap_lines must be less than max_lines",
        ),
        ({"max_units": 0}, "max_units must be positive"),
    ],
)
def test_rejects_invalid_configuration(
    kwargs: dict[str, int],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        ChunkingConfig(**kwargs)


def test_reports_when_no_nonempty_prefix_fits_the_budget() -> None:
    class FixedOverheadMeasurer:
        name = "fixed-overhead-v1"

        def measure(self, text: str) -> int:
            return 2 if text else 0

    with pytest.raises(
        ChunkBudgetError,
        match='"too-large.py":1',
    ):
        list(
            chunk_file(
                discovered("too-large.py", "x"),
                config=ChunkingConfig(
                    max_lines=1,
                    overlap_lines=0,
                    max_units=1,
                ),
                measurer=FixedOverheadMeasurer(),
            )
        )


def test_rejects_invalid_external_measurements() -> None:
    class NegativeMeasurer:
        name = "negative-v1"

        def measure(self, text: str) -> int:
            return -1

    with pytest.raises(TextMeasurementError, match="negative-v1"):
        list(
            chunk_file(
                discovered("app.py", "x"),
                measurer=NegativeMeasurer(),
            )
        )
