"""Replaceable text-size measurement for model input budgets."""

from typing import Protocol


class TextMeasurer(Protocol):
    """Measure text in deterministic, prefix-monotonic units."""

    name: str

    def measure(self, text: str) -> int:
        """Return a nonnegative size for *text*."""


class UnicodeCodePointMeasurer:
    """Measure text using Python Unicode code-point offsets."""

    name = "unicode-code-points-v1"

    def measure(self, text: str) -> int:
        """Return the number of Unicode code points in *text*."""

        return len(text)


DEFAULT_TEXT_MEASURER = UnicodeCodePointMeasurer()
