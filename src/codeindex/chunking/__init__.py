"""Public deterministic chunking API."""

from codeindex.chunking.budget import (
    DEFAULT_TEXT_MEASURER,
    TextMeasurer,
    UnicodeCodePointMeasurer,
)
from codeindex.chunking.errors import (
    ChunkBudgetError,
    ChunkingError,
    TextMeasurementError,
)
from codeindex.chunking.models import (
    DEFAULT_CHUNKING_CONFIG,
    LINE_CHUNKING_STRATEGY_VERSION,
    CodeChunk,
    ChunkingConfig,
)
from codeindex.chunking.strategy import chunk_file, iter_chunks

__all__ = [
    "DEFAULT_CHUNKING_CONFIG",
    "DEFAULT_TEXT_MEASURER",
    "LINE_CHUNKING_STRATEGY_VERSION",
    "ChunkBudgetError",
    "ChunkingConfig",
    "ChunkingError",
    "CodeChunk",
    "TextMeasurementError",
    "TextMeasurer",
    "UnicodeCodePointMeasurer",
    "chunk_file",
    "iter_chunks",
]
