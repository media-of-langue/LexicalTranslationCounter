"""Small curated quality checks for the en_ja alignment path."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from alignment.en_ja import alignment, runtime_metadata
from normalizer.en_normalizer import en_normalizer
from ltc.japanese.normalization import ja_normalizer


@dataclass(frozen=True)
class NormalizedPair:
    pos: str
    src: str
    tgt: str

    @classmethod
    def from_sequence(cls, values):
        pos, src, tgt = values
        return cls(pos=pos, src=src, tgt=tgt)

    def as_tuple(self):
        return (self.pos, self.src, self.tgt)


@dataclass(frozen=True)
class ObservedAlignment:
    pos: str
    src_surface: str
    src_normalized: str
    tgt_surface: str
    tgt_normalized: str
    best_alignment_score: float | None = None
    average_alignment_score: float | None = None
    alignment_evidence_count: int | None = None

    def normalized_pair(self):
        return NormalizedPair(pos=self.pos, src=self.src_normalized, tgt=self.tgt_normalized)

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class QualityCase:
    name: str
    source: str
    target: str
    required_pairs: tuple[NormalizedPair, ...]
    forbidden_pairs: tuple[NormalizedPair, ...]
    tier: str = "core"
    allow_extra_pairs: bool = True
    notes: str | None = None


@dataclass(frozen=True)
class CaseResult:
    name: str
    tier: str
    passed: bool
    required_pairs: tuple[NormalizedPair, ...]
    forbidden_pairs: tuple[NormalizedPair, ...]
    actual_alignments: tuple[ObservedAlignment, ...]
    actual_pairs: tuple[NormalizedPair, ...]
    missing_pairs: tuple[NormalizedPair, ...]
    forbidden_hits: tuple[NormalizedPair, ...]
    unexpected_pairs: tuple[NormalizedPair, ...]
    allow_extra_pairs: bool
    notes: str | None = None

    def as_dict(self):
        return {
            "name": self.name,
            "tier": self.tier,
            "passed": self.passed,
            "required_pairs": [asdict(item) for item in self.required_pairs],
            "forbidden_pairs": [asdict(item) for item in self.forbidden_pairs],
            "actual_alignments": [item.as_dict() for item in self.actual_alignments],
            "actual_pairs": [asdict(item) for item in self.actual_pairs],
            "missing_pairs": [asdict(item) for item in self.missing_pairs],
            "forbidden_hits": [asdict(item) for item in self.forbidden_hits],
            "unexpected_pairs": [asdict(item) for item in self.unexpected_pairs],
            "allow_extra_pairs": self.allow_extra_pairs,
            "notes": self.notes,
        }


def default_cases_path():
    return (
        Path(__file__).resolve().parents[3]
        / "projects"
        / "quality"
        / "en_ja"
        / "cases.json"
    )


def load_quality_cases(path=None):
    cases_path = default_cases_path() if path is None else Path(path)
    payload = json.loads(cases_path.read_text())
    return tuple(
        QualityCase(
            name=item["name"],
            source=item["source"],
            target=item["target"],
            required_pairs=tuple(
                NormalizedPair.from_sequence(pair)
                for pair in item.get("required_pairs", [])
            ),
            forbidden_pairs=tuple(
                NormalizedPair.from_sequence(pair)
                for pair in item.get("forbidden_pairs", [])
            ),
            tier=item.get("tier", "core"),
            allow_extra_pairs=item.get("allow_extra_pairs", True),
            notes=item.get("notes"),
        )
        for item in payload
    )


def observe_alignment_output(output_l):
    observed_alignments = []
    for item in output_l:
        pos_tag, src_surface, tgt_surface = item[0], item[2], item[4]
        metadata = item[5] if len(item) > 5 else {}
        observed_alignments.append(
            ObservedAlignment(
                pos=pos_tag,
                src_surface=src_surface,
                src_normalized=metadata.get("source_normalized")
                or en_normalizer(src_surface, pos_tag, {}, test=True),
                tgt_surface=tgt_surface,
                tgt_normalized=metadata.get("target_normalized")
                or ja_normalizer(tgt_surface, pos_tag, {}, test=True),
                best_alignment_score=metadata.get("best_alignment_score"),
                average_alignment_score=metadata.get("average_alignment_score"),
                alignment_evidence_count=metadata.get("alignment_evidence_count"),
            )
        )
    return tuple(observed_alignments)


def select_cases_for_suite(cases, suite):
    if suite == "core":
        return tuple(case for case in cases if case.tier == "core")
    if suite == "extended":
        return tuple(case for case in cases if case.tier in {"core", "extended"})
    raise ValueError(f"Unsupported en_ja quality suite: {suite}")


def run_quality_case(case):
    corpus_row = ["0", case.source, case.target, "{null}", "False"]
    actual_alignments = observe_alignment_output(alignment(corpus_row, "", test=True))
    actual_pairs = tuple(item.normalized_pair() for item in actual_alignments)
    actual_pair_set = {pair.as_tuple() for pair in actual_pairs}
    required_pair_set = {pair.as_tuple() for pair in case.required_pairs}
    forbidden_pair_set = {pair.as_tuple() for pair in case.forbidden_pairs}
    missing_pairs = tuple(
        pair for pair in case.required_pairs if pair.as_tuple() not in actual_pair_set
    )
    forbidden_hits = tuple(
        pair for pair in case.forbidden_pairs if pair.as_tuple() in actual_pair_set
    )
    unexpected_pairs = ()
    if not case.allow_extra_pairs:
        unexpected_pairs = tuple(
            pair
            for pair in actual_pairs
            if pair.as_tuple() not in required_pair_set
            and pair.as_tuple() not in forbidden_pair_set
        )
    return CaseResult(
        name=case.name,
        tier=case.tier,
        passed=not missing_pairs and not forbidden_hits and not unexpected_pairs,
        required_pairs=case.required_pairs,
        forbidden_pairs=case.forbidden_pairs,
        actual_alignments=actual_alignments,
        actual_pairs=actual_pairs,
        missing_pairs=missing_pairs,
        forbidden_hits=forbidden_hits,
        unexpected_pairs=unexpected_pairs,
        allow_extra_pairs=case.allow_extra_pairs,
        notes=case.notes,
    )


def run_quality_suite(path=None, selected_case_names=None, suite="core"):
    cases = load_quality_cases(path)
    cases = select_cases_for_suite(cases, suite)
    if selected_case_names:
        selected = set(selected_case_names)
        cases = tuple(case for case in cases if case.name in selected)
    results = tuple(run_quality_case(case) for case in cases)
    return {
        "runtime": runtime_metadata(),
        "suite": suite,
        "cases": results,
        "passed": sum(1 for result in results if result.passed),
        "failed": sum(1 for result in results if not result.passed),
    }
