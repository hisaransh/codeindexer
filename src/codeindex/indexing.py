"""Application orchestration for preparing repository chunks."""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from codeindex.chunking import (
    DEFAULT_CHUNKING_CONFIG,
    DEFAULT_TEXT_MEASURER,
    CodeChunk,
    ChunkingConfig,
    TextMeasurer,
    chunk_file,
)
from codeindex.repository import (
    DiscoveredFile,
    DiscoveryDecision,
    DiscoverySummary,
    Repository,
    SkipReason,
    SkippedFile,
    discover_files,
)


class DiscoveryOperation(Protocol):
    """Discover repository paths lazily."""

    def __call__(
        self,
        repository: Repository,
    ) -> Iterable[DiscoveryDecision]:
        """Yield accepted and skipped repository paths."""


class FileChunker(Protocol):
    """Produce chunks lazily for one accepted file."""

    def __call__(
        self,
        discovered_file: DiscoveredFile,
        *,
        config: ChunkingConfig,
        measurer: TextMeasurer,
    ) -> Iterable[CodeChunk]:
        """Yield chunks for one file."""


@dataclass(frozen=True)
class IndexPreparationSummary:
    """Counts and optional skipped-path metadata from index preparation."""

    discovery: DiscoverySummary
    chunk_count: int
    skipped_files: tuple[SkippedFile, ...]


def prepare_index(
    repository: Repository,
    *,
    collect_skipped: bool = False,
    config: ChunkingConfig = DEFAULT_CHUNKING_CONFIG,
    measurer: TextMeasurer = DEFAULT_TEXT_MEASURER,
    discovery_operation: DiscoveryOperation = discover_files,
    file_chunker: FileChunker = chunk_file,
) -> IndexPreparationSummary:
    """Discover and chunk one repository without retaining source contents."""

    candidate_count = 0
    accepted_count = 0
    chunk_count = 0
    skipped_counts: Counter[SkipReason] = Counter()
    skipped_files: list[SkippedFile] = []

    for decision in discovery_operation(repository):
        candidate_count += 1
        if isinstance(decision, SkippedFile):
            skipped_counts[decision.reason] += 1
            if collect_skipped:
                skipped_files.append(decision)
            continue

        accepted_count += 1
        for _chunk in file_chunker(
            decision,
            config=config,
            measurer=measurer,
        ):
            chunk_count += 1

    discovery_summary = DiscoverySummary(
        candidate_count=candidate_count,
        accepted_count=accepted_count,
        skipped_by_reason=tuple(
            sorted(skipped_counts.items(), key=lambda item: item[0].value)
        ),
    )
    return IndexPreparationSummary(
        discovery=discovery_summary,
        chunk_count=chunk_count,
        skipped_files=tuple(skipped_files),
    )
