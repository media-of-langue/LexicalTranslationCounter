"""Export en_ja observation documents without changing the legacy count path."""

from __future__ import annotations

import csv
from dataclasses import asdict
import json
from pathlib import Path

from ltc.evaluation.en_ja_quality import (
    QualityCase,
    load_quality_cases,
    select_cases_for_suite,
)
from ltc.inspection.en_ja import EnJaInspectionRequest, inspect_request
from ltc.observations.en_ja import summarize_observation_documents


def build_observation_document(request, payload):
    return {
        "request": dict(payload.get("request", {})) or {
            "name": request.name,
            "notes": request.notes,
            "source": request.source,
            "target": request.target,
        },
        "runtime": dict(payload.get("runtime", {})),
        "word_observations": list(payload.get("word_observations", [])),
        "phrase_observations": list(payload.get("phrase_observations", [])),
        "lexicalization_decisions": list(payload.get("lexicalization_decisions", [])),
    }


def build_bundle_from_documents(documents, *, suite=None, cases_path=None):
    summary = summarize_observation_documents(documents)
    candidate_tables = build_candidate_tables(documents)
    return {
        "suite": suite,
        "cases_path": str(cases_path) if cases_path is not None else None,
        "summary": summary,
        "candidate_tables": candidate_tables,
        "staging_tables": build_staging_tables(documents, candidate_tables),
        "documents": list(documents),
    }


def build_document_for_request(request):
    payload = inspect_request(request)
    return build_observation_document(request, payload)


def build_bundle_for_request(request):
    document = build_document_for_request(request)
    return build_bundle_from_documents([document], suite=None, cases_path=None)


def build_bundle_for_quality_suite(*, path=None, selected_case_names=None, suite="core"):
    cases = load_quality_cases(path)
    selected_cases = select_cases_for_suite(cases, suite)
    if selected_case_names:
        wanted = set(selected_case_names)
        selected_cases = tuple(case for case in selected_cases if case.name in wanted)
    documents = [
        build_document_for_request(request_from_quality_case(case))
        for case in selected_cases
    ]
    return build_bundle_from_documents(documents, suite=suite, cases_path=path)


def request_from_quality_case(case):
    if not isinstance(case, QualityCase):
        raise TypeError("expected QualityCase")
    return EnJaInspectionRequest(
        source=case.source,
        target=case.target,
        name=case.name,
        notes=case.notes,
    )


def bundle_to_dict(bundle):
    return asdict(bundle) if hasattr(bundle, "__dataclass_fields__") else bundle


def build_candidate_tables(documents):
    return {
        "phrase_network_candidates": build_phrase_network_candidates(documents),
        "auto_component_word_candidates": build_auto_component_word_candidates(documents),
        "review_queue": build_review_queue(documents),
    }


def build_staging_tables(documents, candidate_tables):
    auto_supported_phrase_pairs = build_auto_supported_phrase_pairs(documents)
    return {
        "phrase_network_staging": build_phrase_network_staging(
            candidate_tables["phrase_network_candidates"]
        ),
        "auto_component_word_staging": build_auto_component_word_staging(
            candidate_tables["auto_component_word_candidates"]
        ),
        "review_queue_staging": build_review_queue_staging(
            candidate_tables["review_queue"],
            auto_supported_phrase_pairs=auto_supported_phrase_pairs,
        ),
    }


def build_auto_supported_phrase_pairs(documents):
    pairs = set()
    for document in documents:
        for decision in document.get("lexicalization_decisions", []):
            if decision.get("recommended_action") != "project_components_auto":
                continue
            pairs.add(
                (
                    decision.get("source_normalized", ""),
                    decision.get("target_normalized", ""),
                )
            )
    return pairs


def build_phrase_network_candidates(documents):
    buckets = {}
    for document in documents:
        request = document.get("request", {})
        case_name = request.get("name")
        for decision in document.get("lexicalization_decisions", []):
            if decision.get("recommended_action") != "register_phrase":
                continue
            key = (
                decision.get("pos_tag", ""),
                decision.get("source_normalized", ""),
                decision.get("target_normalized", ""),
            )
            bucket = buckets.setdefault(
                key,
                {
                    "pos_tag": decision.get("pos_tag", ""),
                    "source_normalized": decision.get("source_normalized", ""),
                    "target_normalized": decision.get("target_normalized", ""),
                    "occurrences": 0,
                    "source_surfaces": set(),
                    "target_surfaces": set(),
                    "case_names": set(),
                    "reasons": set(),
                },
            )
            bucket["occurrences"] += 1
            bucket["source_surfaces"].add(decision.get("source_surface", ""))
            bucket["target_surfaces"].add(decision.get("target_surface", ""))
            if case_name:
                bucket["case_names"].add(case_name)
            if decision.get("reason"):
                bucket["reasons"].add(decision["reason"])
    return finalize_candidate_bucket_list(buckets.values())


def build_auto_component_word_candidates(documents):
    buckets = {}
    for document in documents:
        request = document.get("request", {})
        case_name = request.get("name")
        for decision in document.get("lexicalization_decisions", []):
            if decision.get("recommended_action") != "project_components_auto":
                continue
            phrase_key = (
                decision.get("source_normalized", ""),
                decision.get("target_normalized", ""),
            )
            for projection in decision.get("component_projections", []):
                key = (
                    projection.get("pos_tag", ""),
                    projection.get("source_normalized", ""),
                    projection.get("target_normalized", ""),
                )
                bucket = buckets.setdefault(
                    key,
                    {
                        "pos_tag": projection.get("pos_tag", ""),
                        "source_normalized": projection.get("source_normalized", ""),
                        "target_normalized": projection.get("target_normalized", ""),
                        "occurrences": 0,
                        "source_surfaces": set(),
                        "target_surfaces": set(),
                        "case_names": set(),
                        "parent_phrases": set(),
                        "reasons": set(),
                        "confidence_values": [],
                    },
                )
                bucket["occurrences"] += 1
                bucket["source_surfaces"].add(projection.get("source_surface", ""))
                bucket["target_surfaces"].add(projection.get("target_surface", ""))
                bucket["parent_phrases"].add(" -> ".join(phrase_key))
                if case_name:
                    bucket["case_names"].add(case_name)
                if projection.get("reason"):
                    bucket["reasons"].add(projection["reason"])
                if projection.get("confidence") is not None:
                    bucket["confidence_values"].append(projection["confidence"])
    rows = []
    for bucket in buckets.values():
        rows.append(
            {
                "pos_tag": bucket["pos_tag"],
                "source_normalized": bucket["source_normalized"],
                "target_normalized": bucket["target_normalized"],
                "occurrences": bucket["occurrences"],
                "source_surfaces": sorted(text for text in bucket["source_surfaces"] if text),
                "target_surfaces": sorted(text for text in bucket["target_surfaces"] if text),
                "case_names": sorted(bucket["case_names"]),
                "parent_phrases": sorted(bucket["parent_phrases"]),
                "reasons": sorted(bucket["reasons"]),
                "average_confidence": average_or_none(bucket["confidence_values"]),
            }
        )
    return sort_candidate_rows(rows)


def build_review_queue(documents):
    rows = []
    for document in documents:
        request = document.get("request", {})
        case_name = request.get("name")
        source_text = request.get("source", "")
        target_text = request.get("target", "")
        for decision in document.get("lexicalization_decisions", []):
            if decision.get("recommended_action") != "project_components_needs_review":
                continue
            rows.append(
                {
                    "case_name": case_name,
                    "pos_tag": decision.get("pos_tag", ""),
                    "source_normalized": decision.get("source_normalized", ""),
                    "target_normalized": decision.get("target_normalized", ""),
                    "source_surface": decision.get("source_surface", ""),
                    "target_surface": decision.get("target_surface", ""),
                    "reason": decision.get("reason", ""),
                    "confidence": decision.get("confidence"),
                    "source_text": source_text,
                    "target_text": target_text,
                    "component_projections": list(decision.get("component_projections", [])),
                }
            )
    return rows


def finalize_candidate_bucket_list(buckets):
    rows = []
    for bucket in buckets:
        rows.append(
            {
                "pos_tag": bucket["pos_tag"],
                "source_normalized": bucket["source_normalized"],
                "target_normalized": bucket["target_normalized"],
                "occurrences": bucket["occurrences"],
                "source_surfaces": sorted(text for text in bucket["source_surfaces"] if text),
                "target_surfaces": sorted(text for text in bucket["target_surfaces"] if text),
                "case_names": sorted(bucket["case_names"]),
                "reasons": sorted(bucket["reasons"]),
            }
        )
    return sort_candidate_rows(rows)


def build_phrase_network_staging(candidate_rows):
    rows = []
    for item in candidate_rows:
        rows.append(
            {
                "staging_action": "stage_phrase_candidate",
                "pos_tag": item["pos_tag"],
                "source_normalized": item["source_normalized"],
                "target_normalized": item["target_normalized"],
                "occurrences": item["occurrences"],
                "case_count": len(item["case_names"]),
                "source_surfaces": " | ".join(item["source_surfaces"]),
                "target_surfaces": " | ".join(item["target_surfaces"]),
                "case_names": " | ".join(item["case_names"]),
                "reasons": " | ".join(item["reasons"]),
            }
        )
    return sort_staging_rows(rows)


def build_auto_component_word_staging(candidate_rows):
    rows = []
    for item in candidate_rows:
        rows.append(
            {
                "staging_action": "stage_auto_component_candidate",
                "pos_tag": item["pos_tag"],
                "source_normalized": item["source_normalized"],
                "target_normalized": item["target_normalized"],
                "occurrences": item["occurrences"],
                "average_confidence": item["average_confidence"],
                "case_count": len(item["case_names"]),
                "parent_phrase_count": len(item["parent_phrases"]),
                "source_surfaces": " | ".join(item["source_surfaces"]),
                "target_surfaces": " | ".join(item["target_surfaces"]),
                "parent_phrases": " | ".join(item["parent_phrases"]),
                "case_names": " | ".join(item["case_names"]),
                "reasons": " | ".join(item["reasons"]),
            }
        )
    return sort_staging_rows(rows)


def build_review_queue_staging(review_rows, *, auto_supported_phrase_pairs):
    rows = []
    for item in review_rows:
        if (
            item.get("source_normalized", ""),
            item.get("target_normalized", ""),
        ) in auto_supported_phrase_pairs:
            continue
        component_pairs = " | ".join(
            f"{projection.get('source_normalized', '')}->{projection.get('target_normalized', '')}"
            for projection in item.get("component_projections", [])
        )
        rows.append(
            {
                "staging_action": "needs_human_review",
                "case_name": item.get("case_name", ""),
                "pos_tag": item.get("pos_tag", ""),
                "source_normalized": item.get("source_normalized", ""),
                "target_normalized": item.get("target_normalized", ""),
                "confidence": item.get("confidence"),
                "reason": item.get("reason", ""),
                "component_projection_pairs": component_pairs,
                "source_text": item.get("source_text", ""),
                "target_text": item.get("target_text", ""),
            }
        )
    return rows


def sort_candidate_rows(rows):
    return sorted(
        rows,
        key=lambda item: (
            -item.get("occurrences", 0),
            item.get("pos_tag", ""),
            item.get("source_normalized", ""),
            item.get("target_normalized", ""),
        ),
    )


def sort_staging_rows(rows):
    return sorted(
        rows,
        key=lambda item: (
            item.get("staging_action", ""),
            -item.get("occurrences", 0),
            item.get("pos_tag", ""),
            item.get("source_normalized", ""),
            item.get("target_normalized", ""),
        ),
    )


def average_or_none(values):
    if not values:
        return None
    return sum(values) / len(values)


def write_bundle_directory(bundle, output_dir):
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "bundle.json").write_text(
        json.dumps(bundle, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    )
    (path / "documents.jsonl").write_text(
        "\n".join(
            json.dumps(document, ensure_ascii=False, sort_keys=True)
            for document in bundle["documents"]
        )
        + "\n"
    )
    candidate_tables = bundle["candidate_tables"]
    for filename, table_name in (
        ("phrase-network-candidates.jsonl", "phrase_network_candidates"),
        ("auto-component-word-candidates.jsonl", "auto_component_word_candidates"),
        ("review-queue.jsonl", "review_queue"),
    ):
        rows = candidate_tables[table_name]
        (path / filename).write_text(
            ("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n")
            if rows
            else ""
        )
    staging_tables = bundle["staging_tables"]
    write_csv_rows(path / "phrase-network-staging.csv", staging_tables["phrase_network_staging"])
    write_csv_rows(
        path / "auto-component-word-staging.csv",
        staging_tables["auto_component_word_staging"],
    )
    write_csv_rows(path / "review-queue.csv", staging_tables["review_queue_staging"])


def write_csv_rows(path, rows):
    if not rows:
        path.write_text("")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
