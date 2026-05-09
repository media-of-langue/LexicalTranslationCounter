from __future__ import annotations

from typing import Protocol, Sequence

from ltc.schema import AlignmentEdge, AnalyzedSentence


class AlignmentBackend(Protocol):
    """Backend contract for word alignment implementations."""

    name: str

    def align(
        self,
        source: AnalyzedSentence,
        target: AnalyzedSentence,
    ) -> Sequence[AlignmentEdge]:
        ...

    def align_batch(
        self,
        sources: Sequence[AnalyzedSentence],
        targets: Sequence[AnalyzedSentence],
    ) -> Sequence[Sequence[AlignmentEdge]]:
        ...
