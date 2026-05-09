from __future__ import annotations

from typing import Protocol, Sequence

from ltc.schema import AnalyzedSentence


class LinguisticBackend(Protocol):
    """Backend contract for tokenization, POS tagging, and lemmatization."""

    name: str

    def analyze(self, sentence: str, language: str) -> AnalyzedSentence:
        ...

    def analyze_batch(
        self,
        sentences: Sequence[str],
        language: str,
    ) -> Sequence[AnalyzedSentence]:
        ...
