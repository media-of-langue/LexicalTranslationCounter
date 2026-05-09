"""Canonical data structures for the LTC pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple


@dataclass(frozen=True)
class Token:
    text: str
    pos_tag: str = ""
    lemma: str = ""
    start: Optional[int] = None
    end: Optional[int] = None


@dataclass(frozen=True)
class AnalyzedSentence:
    language: str
    text: str
    tokens: Tuple[Token, ...]


@dataclass(frozen=True)
class AlignmentEdge:
    source_indices: Tuple[int, ...]
    target_indices: Tuple[int, ...]
    source_tokens: Tuple[str, ...]
    target_tokens: Tuple[str, ...]
    pos_tag: str = ""
    score: Optional[float] = None
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ComponentProjection:
    pos_tag: str
    source_surface: str
    source_normalized: str
    target_surface: str
    target_normalized: str
    confidence: Optional[float] = None
    reason: str = ""
    promotion_status: str = "needs_review"


@dataclass(frozen=True)
class TranslationObservation:
    pos_tag: str
    source_surface: str
    source_normalized: str
    target_surface: str
    target_normalized: str
    source_indices: Tuple[int, ...] = ()
    target_indices: Tuple[int, ...] = ()
    source_pos_tags: Tuple[str, ...] = ()
    target_pos_tags: Tuple[str, ...] = ()
    unit_level: str = "word"
    lexicalization_action: str = "register_word"
    lexicalization_reason: str = ""
    best_alignment_score: Optional[float] = None
    average_alignment_score: Optional[float] = None
    alignment_evidence_count: Optional[int] = None
    component_projections: Tuple[ComponentProjection, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class LexicalizationDecision:
    pos_tag: str
    source_surface: str
    source_normalized: str
    target_surface: str
    target_normalized: str
    observation_unit_level: str = "word"
    recommended_action: str = "register_word"
    reason: str = ""
    confidence: Optional[float] = None
    component_projections: Tuple[ComponentProjection, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CountCommandConfig:
    start_id: int
    la1: str
    la2: str
    input_dir: str
    output_dir: str
    batch_size: int
    checkpoint_interval_rows: int
    input_csv_path: Optional[str] = None
    end_id: Optional[int] = None
    max_rows: Optional[int] = None
    skip_resume: bool = False

    @property
    def language_pair(self) -> str:
        return f"{self.la1}_{self.la2}"

    @property
    def resume_active(self) -> bool:
        return (self.start_id != 0) and not self.skip_resume
