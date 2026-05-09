"""Helpers for inspecting the en_ja alignment path on one sentence pair."""

from __future__ import annotations

from dataclasses import dataclass

from alignment.en_ja import inspect_sentence_pair
from ltc.evaluation.en_ja_quality import load_quality_cases
from ltc.observations.en_ja import build_observation_payload


@dataclass(frozen=True)
class EnJaInspectionRequest:
    source: str
    target: str
    name: str | None = None
    notes: str | None = None


def resolve_inspection_request(
    *,
    source=None,
    target=None,
    case_name=None,
    cases_path=None,
):
    if case_name:
        cases = load_quality_cases(cases_path)
        for case in cases:
            if case.name == case_name:
                return EnJaInspectionRequest(
                    source=case.source,
                    target=case.target,
                    name=case.name,
                    notes=case.notes,
                )
        raise ValueError(f"unknown en_ja quality case: {case_name!r}")

    if source and target:
        return EnJaInspectionRequest(source=source, target=target)

    raise ValueError("provide --case or both --source and --target")


def inspect_request(request):
    payload = inspect_sentence_pair(request.source, request.target, wordlist="", test=True)
    payload.update(build_observation_payload(payload))
    payload["request"] = {
        "name": request.name,
        "notes": request.notes,
        "source": request.source,
        "target": request.target,
    }
    return payload
