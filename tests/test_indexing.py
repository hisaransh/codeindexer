from collections.abc import Iterable
from pathlib import PurePosixPath

from codeindex.chunking import CodeChunk, ChunkingConfig, TextMeasurer
from codeindex.indexing import prepare_index
from codeindex.repository import (
    DiscoveredFile,
    Repository,
    SkipReason,
    SkippedFile,
)


def test_prepares_discovery_and_chunk_counts_in_one_pass(tmp_path) -> None:
    decisions = [
        DiscoveredFile(PurePosixPath("short.py"), "x = 1\n", 6),
        DiscoveredFile(PurePosixPath("long.py"), "abcdefgh", 8),
        SkippedFile(PurePosixPath("dist/app.js"), SkipReason.GENERATED),
    ]

    summary = prepare_index(
        Repository(tmp_path),
        collect_skipped=True,
        config=ChunkingConfig(
            max_lines=10,
            overlap_lines=0,
            max_units=4,
        ),
        discovery_operation=lambda repository: decisions,
    )

    assert summary.discovery.candidate_count == 3
    assert summary.discovery.accepted_count == 2
    assert summary.discovery.skipped_count == 1
    assert summary.discovery.skipped_by_reason == (
        (SkipReason.GENERATED, 1),
    )
    assert summary.chunk_count == 4
    assert summary.skipped_files == (
        SkippedFile(PurePosixPath("dist/app.js"), SkipReason.GENERATED),
    )


def test_does_not_retain_skipped_paths_unless_requested(tmp_path) -> None:
    skipped = SkippedFile(PurePosixPath("image.bin"), SkipReason.BINARY)

    summary = prepare_index(
        Repository(tmp_path),
        discovery_operation=lambda repository: [skipped],
    )

    assert summary.skipped_files == ()


def test_chunks_each_file_before_discovering_the_next(tmp_path) -> None:
    observations: list[str] = []

    def discover(repository: Repository) -> Iterable[DiscoveredFile]:
        observations.append("discover:first.py")
        yield DiscoveredFile(PurePosixPath("first.py"), "first\n", 6)
        observations.append("discover:second.py")
        yield DiscoveredFile(PurePosixPath("second.py"), "second\n", 7)

    def chunk(
        source_file: DiscoveredFile,
        *,
        config: ChunkingConfig,
        measurer: TextMeasurer,
    ) -> Iterable[CodeChunk]:
        observations.append(f"chunk:{source_file.relative_path.as_posix()}")
        return []

    prepare_index(
        Repository(tmp_path),
        discovery_operation=discover,
        file_chunker=chunk,
    )

    assert observations == [
        "discover:first.py",
        "chunk:first.py",
        "discover:second.py",
        "chunk:second.py",
    ]
