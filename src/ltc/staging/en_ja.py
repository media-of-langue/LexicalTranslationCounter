"""Aggregate en_ja observation bundles into separate staging network tables."""

from __future__ import annotations

import csv
import json
from pathlib import Path


def load_bundle_payload(path):
    return json.loads(Path(path).read_text())


def load_staging_snapshot(input_dir):
    path = Path(input_dir)
    bundle_path = path / "bundle.json"
    summary_path = path / "summary.json"
    lexical_path = path / "lexical-network-staging.csv"
    if summary_path.exists() and lexical_path.exists():
        ready_auto_component_rows = load_csv_rows(
            path / "ready-auto-component-word-relations.csv"
        )
        candidate_auto_component_rows = load_csv_rows(
            path / "candidate-auto-component-word-relations.csv"
        )
        existing_word_network_rows = load_csv_rows(path / "existing-word-network.csv")
        promotion_ready_word_network_rows = load_csv_rows(
            path / "promotion-ready-word-network.csv"
        ) or build_promotion_ready_word_network_rows(ready_auto_component_rows)
        return {
            "source_kind": "aggregated_dir",
            "input_dir": str(path),
            "summary": json.loads(summary_path.read_text()),
            "phrase_network_rows": load_csv_rows(path / "phrase-network-relations.csv"),
            "auto_component_rows": load_csv_rows(
                path / "auto-component-word-relations.csv"
            ),
            "ready_auto_component_rows": ready_auto_component_rows,
            "candidate_auto_component_rows": candidate_auto_component_rows,
            "existing_word_network_rows": existing_word_network_rows,
            "promotion_ready_word_network_rows": promotion_ready_word_network_rows,
            "promotion_diff_rows": load_csv_rows(path / "promotion-ready-diff.csv")
            or build_promotion_diff_rows(
                promotion_ready_word_network_rows,
                existing_word_network_rows,
            ),
            "promotion_proposal_rows": load_csv_rows(path / "promotion-ready-proposals.csv")
            or build_promotion_proposal_rows(
                load_csv_rows(path / "promotion-ready-diff.csv")
                or build_promotion_diff_rows(
                    promotion_ready_word_network_rows,
                    existing_word_network_rows,
                )
            ),
            "promotion_followup_rows": load_csv_rows(path / "promotion-followup.csv")
            or build_promotion_followup_rows(
                load_csv_rows(path / "promotion-ready-diff.csv")
                or build_promotion_diff_rows(
                    promotion_ready_word_network_rows,
                    existing_word_network_rows,
                )
            ),
            "combined_network_rows": load_csv_rows(lexical_path),
            "review_rows": load_csv_rows(path / "review-queue.csv"),
        }
    if bundle_path.exists():
        aggregated = aggregate_bundle_payloads([load_bundle_payload(bundle_path)])
        aggregated["source_kind"] = "bundle_dir"
        aggregated["input_dir"] = str(path)
        return aggregated
    raise FileNotFoundError(
        f"could not find bundle.json or summary.json in staging input dir: {path}"
    )


def aggregate_bundle_payloads(bundle_payloads):
    phrase_rows = merge_phrase_network_candidates(bundle_payloads)
    auto_component_rows = merge_auto_component_candidates(bundle_payloads)
    ready_auto_component_rows = select_rows_by_promotion_bucket(
        auto_component_rows, "ready"
    )
    candidate_auto_component_rows = select_rows_by_promotion_bucket(
        auto_component_rows, "candidate"
    )
    existing_word_network_rows = merge_existing_word_network_rows(bundle_payloads)
    promotion_ready_word_network_rows = build_promotion_ready_word_network_rows(
        ready_auto_component_rows
    )
    promotion_diff_rows = build_promotion_diff_rows(
        promotion_ready_word_network_rows,
        existing_word_network_rows,
    )
    promotion_proposal_rows = build_promotion_proposal_rows(promotion_diff_rows)
    promotion_followup_rows = build_promotion_followup_rows(promotion_diff_rows)
    review_rows = merge_review_queue_rows(bundle_payloads)
    combined_rows = build_combined_network_rows(phrase_rows, auto_component_rows)
    return {
        "summary": {
            "bundles": len(bundle_payloads),
            "phrase_network_rows": len(phrase_rows),
            "auto_component_rows": len(auto_component_rows),
            "ready_auto_component_rows": len(ready_auto_component_rows),
            "candidate_auto_component_rows": len(candidate_auto_component_rows),
            "existing_word_network_rows": len(existing_word_network_rows),
            "promotion_ready_word_network_rows": len(
                promotion_ready_word_network_rows
            ),
            "promotion_exact_match_rows": count_promotion_status(
                promotion_diff_rows, "exact_match"
            ),
            "promotion_source_overlap_rows": count_promotion_status(
                promotion_diff_rows, "source_overlap_different_target"
            ),
            "promotion_target_overlap_rows": count_promotion_status(
                promotion_diff_rows, "target_overlap_different_source"
            ),
            "promotion_source_and_target_overlap_rows": count_promotion_status(
                promotion_diff_rows, "source_and_target_overlap"
            ),
            "promotion_novel_rows": count_promotion_status(
                promotion_diff_rows, "novel"
            ),
            "promotion_proposal_rows": len(promotion_proposal_rows),
            "promotion_followup_rows": len(promotion_followup_rows),
            "combined_network_rows": len(combined_rows),
            "review_rows": len(review_rows),
        },
        "phrase_network_rows": phrase_rows,
        "auto_component_rows": auto_component_rows,
        "ready_auto_component_rows": ready_auto_component_rows,
        "candidate_auto_component_rows": candidate_auto_component_rows,
        "existing_word_network_rows": existing_word_network_rows,
        "promotion_ready_word_network_rows": promotion_ready_word_network_rows,
        "promotion_diff_rows": promotion_diff_rows,
        "promotion_proposal_rows": promotion_proposal_rows,
        "promotion_followup_rows": promotion_followup_rows,
        "combined_network_rows": combined_rows,
        "review_rows": review_rows,
    }


def merge_phrase_network_candidates(bundle_payloads):
    buckets = {}
    for bundle in bundle_payloads:
        for row in bundle.get("staging_tables", {}).get("phrase_network_staging", []):
            key = (
                row.get("pos_tag", ""),
                row.get("source_normalized", ""),
                row.get("target_normalized", ""),
            )
            bucket = buckets.setdefault(
                key,
                {
                    "candidate_kind": "phrase",
                    "pos_tag": row.get("pos_tag", ""),
                    "source_normalized": row.get("source_normalized", ""),
                    "target_normalized": row.get("target_normalized", ""),
                    "occurrences": 0,
                    "case_names": set(),
                    "source_surfaces": set(),
                    "target_surfaces": set(),
                    "reasons": set(),
                },
            )
            bucket["occurrences"] += int(row.get("occurrences", 0))
            add_pipe_separated(bucket["case_names"], row.get("case_names", ""))
            add_pipe_separated(bucket["source_surfaces"], row.get("source_surfaces", ""))
            add_pipe_separated(bucket["target_surfaces"], row.get("target_surfaces", ""))
            add_pipe_separated(bucket["reasons"], row.get("reasons", ""))
    rows = []
    for row_id, bucket in enumerate(sort_bucket_values(buckets.values())):
        rows.append(
            {
                "staging_id": row_id,
                "candidate_kind": bucket["candidate_kind"],
                "pos_tag": bucket["pos_tag"],
                "source_normalized": bucket["source_normalized"],
                "target_normalized": bucket["target_normalized"],
                "occurrences": bucket["occurrences"],
                "case_count": len(bucket["case_names"]),
                "source_surfaces": " | ".join(sorted(bucket["source_surfaces"])),
                "target_surfaces": " | ".join(sorted(bucket["target_surfaces"])),
                "case_names": " | ".join(sorted(bucket["case_names"])),
                "reasons": " | ".join(sorted(bucket["reasons"])),
            }
        )
    return rows


def merge_auto_component_candidates(bundle_payloads):
    buckets = {}
    for bundle in bundle_payloads:
        for row in bundle.get("staging_tables", {}).get("auto_component_word_staging", []):
            key = (
                row.get("pos_tag", ""),
                row.get("source_normalized", ""),
                row.get("target_normalized", ""),
            )
            bucket = buckets.setdefault(
                key,
                {
                    "candidate_kind": "auto_component_word",
                    "pos_tag": row.get("pos_tag", ""),
                    "source_normalized": row.get("source_normalized", ""),
                    "target_normalized": row.get("target_normalized", ""),
                    "occurrences": 0,
                    "case_names": set(),
                    "parent_phrases": set(),
                    "source_surfaces": set(),
                    "target_surfaces": set(),
                    "reasons": set(),
                    "confidence_weighted_sum": 0.0,
                    "confidence_occurrences": 0,
                },
            )
            occurrences = int(row.get("occurrences", 0))
            bucket["occurrences"] += occurrences
            add_pipe_separated(bucket["case_names"], row.get("case_names", ""))
            add_pipe_separated(bucket["parent_phrases"], row.get("parent_phrases", ""))
            add_pipe_separated(bucket["source_surfaces"], row.get("source_surfaces", ""))
            add_pipe_separated(bucket["target_surfaces"], row.get("target_surfaces", ""))
            add_pipe_separated(bucket["reasons"], row.get("reasons", ""))
            average_confidence = row.get("average_confidence")
            if average_confidence not in ("", None):
                bucket["confidence_weighted_sum"] += float(average_confidence) * occurrences
                bucket["confidence_occurrences"] += occurrences
    rows = []
    for row_id, bucket in enumerate(sort_bucket_values(buckets.values())):
        rows.append(
            {
                "staging_id": row_id,
                "candidate_kind": bucket["candidate_kind"],
                "pos_tag": bucket["pos_tag"],
                "source_normalized": bucket["source_normalized"],
                "target_normalized": bucket["target_normalized"],
                "occurrences": bucket["occurrences"],
                "average_confidence": compute_average_confidence(bucket),
                "promotion_bucket": classify_auto_component_promotion_bucket(bucket),
                "case_count": len(bucket["case_names"]),
                "parent_phrase_count": len(bucket["parent_phrases"]),
                "source_surfaces": " | ".join(sorted(bucket["source_surfaces"])),
                "target_surfaces": " | ".join(sorted(bucket["target_surfaces"])),
                "parent_phrases": " | ".join(sorted(bucket["parent_phrases"])),
                "case_names": " | ".join(sorted(bucket["case_names"])),
                "reasons": " | ".join(sorted(bucket["reasons"])),
            }
        )
    return rows


def merge_review_queue_rows(bundle_payloads):
    rows = []
    seen = set()
    for bundle in bundle_payloads:
        for row in bundle.get("staging_tables", {}).get("review_queue_staging", []):
            key = (
                row.get("case_name", ""),
                row.get("source_normalized", ""),
                row.get("target_normalized", ""),
                row.get("component_projection_pairs", ""),
            )
            if key in seen:
                continue
            seen.add(key)
            item = dict(row)
            item["review_id"] = len(rows)
            rows.append(item)
    return rows


def merge_existing_word_network_rows(bundle_payloads):
    buckets = {}
    for bundle in bundle_payloads:
        for document in bundle.get("documents", []):
            request = document.get("request", {})
            case_name = request.get("name")
            for decision in document.get("lexicalization_decisions", []):
                if decision.get("recommended_action") != "register_word":
                    continue
                key = (
                    decision.get("pos_tag", ""),
                    decision.get("source_normalized", ""),
                    decision.get("target_normalized", ""),
                )
                bucket = buckets.setdefault(
                    key,
                    {
                        "candidate_kind": "existing_word",
                        "pos_tag": decision.get("pos_tag", ""),
                        "source_normalized": decision.get("source_normalized", ""),
                        "target_normalized": decision.get("target_normalized", ""),
                        "occurrences": 0,
                        "case_names": set(),
                        "source_surfaces": set(),
                        "target_surfaces": set(),
                        "reasons": set(),
                        "confidence_weighted_sum": 0.0,
                        "confidence_occurrences": 0,
                    },
                )
                bucket["occurrences"] += 1
                add_pipe_separated(bucket["case_names"], case_name or "")
                add_pipe_separated(
                    bucket["source_surfaces"], decision.get("source_surface", "")
                )
                add_pipe_separated(
                    bucket["target_surfaces"], decision.get("target_surface", "")
                )
                add_pipe_separated(bucket["reasons"], decision.get("reason", ""))
                confidence = decision.get("confidence")
                if confidence not in ("", None):
                    bucket["confidence_weighted_sum"] += float(confidence)
                    bucket["confidence_occurrences"] += 1
    rows = []
    for row_id, bucket in enumerate(sort_bucket_values(buckets.values())):
        rows.append(
            {
                "existing_id": row_id,
                "candidate_kind": bucket["candidate_kind"],
                "pos_tag": bucket["pos_tag"],
                "source_normalized": bucket["source_normalized"],
                "target_normalized": bucket["target_normalized"],
                "occurrences": bucket["occurrences"],
                "average_confidence": compute_average_confidence(bucket),
                "case_count": len(bucket["case_names"]),
                "source_surfaces": " | ".join(sorted(bucket["source_surfaces"])),
                "target_surfaces": " | ".join(sorted(bucket["target_surfaces"])),
                "case_names": " | ".join(sorted(bucket["case_names"])),
                "reasons": " | ".join(sorted(bucket["reasons"])),
            }
        )
    return rows


def build_combined_network_rows(phrase_rows, auto_component_rows):
    rows = []
    for item in phrase_rows:
        rows.append(
            {
                "staging_id": len(rows),
                "candidate_kind": item["candidate_kind"],
                "pos_tag": item["pos_tag"],
                "source_normalized": item["source_normalized"],
                "target_normalized": item["target_normalized"],
                "occurrences": item["occurrences"],
                "average_confidence": "",
                "promotion_bucket": "",
                "support": item["case_count"],
                "notes": item["reasons"],
            }
        )
    for item in auto_component_rows:
        rows.append(
            {
                "staging_id": len(rows),
                "candidate_kind": item["candidate_kind"],
                "pos_tag": item["pos_tag"],
                "source_normalized": item["source_normalized"],
                "target_normalized": item["target_normalized"],
                "occurrences": item["occurrences"],
                "average_confidence": item["average_confidence"],
                "promotion_bucket": item.get("promotion_bucket", ""),
                "support": item["case_count"],
                "notes": item["reasons"],
            }
        )
    return rows


def build_promotion_ready_word_network_rows(ready_auto_component_rows):
    rows = []
    for item in ready_auto_component_rows:
        rows.append(
            {
                "promotion_id": len(rows),
                "promotion_source": "ready_auto_component",
                "pos_tag": item["pos_tag"],
                "source_normalized": item["source_normalized"],
                "target_normalized": item["target_normalized"],
                "occurrences": item["occurrences"],
                "average_confidence": item["average_confidence"],
                "support": item["case_count"],
                "parent_phrase_count": item["parent_phrase_count"],
                "source_surfaces": item["source_surfaces"],
                "target_surfaces": item["target_surfaces"],
                "parent_phrases": item["parent_phrases"],
                "case_names": item["case_names"],
                "notes": item["reasons"],
            }
        )
    return rows


def build_promotion_diff_rows(promotion_ready_word_network_rows, existing_word_network_rows):
    exact_keys = {
        (
            row.get("pos_tag", ""),
            row.get("source_normalized", ""),
            row.get("target_normalized", ""),
        )
        for row in existing_word_network_rows
    }
    existing_targets_by_source = {}
    existing_sources_by_target = {}
    for row in existing_word_network_rows:
        source_key = (row.get("pos_tag", ""), row.get("source_normalized", ""))
        target_key = (row.get("pos_tag", ""), row.get("target_normalized", ""))
        existing_targets_by_source.setdefault(source_key, set()).add(
            row.get("target_normalized", "")
        )
        existing_sources_by_target.setdefault(target_key, set()).add(
            row.get("source_normalized", "")
        )
    rows = []
    for row in promotion_ready_word_network_rows:
        pos_tag = row.get("pos_tag", "")
        source_normalized = row.get("source_normalized", "")
        target_normalized = row.get("target_normalized", "")
        exact_key = (pos_tag, source_normalized, target_normalized)
        source_targets = sorted(
            target
            for target in existing_targets_by_source.get((pos_tag, source_normalized), set())
            if target != target_normalized
        )
        target_sources = sorted(
            source
            for source in existing_sources_by_target.get((pos_tag, target_normalized), set())
            if source != source_normalized
        )
        status = classify_promotion_diff_status(
            exact_key in exact_keys,
            bool(source_targets),
            bool(target_sources),
        )
        rows.append(
            {
                "diff_id": len(rows),
                "status": status,
                "pos_tag": pos_tag,
                "source_normalized": source_normalized,
                "target_normalized": target_normalized,
                "occurrences": row.get("occurrences", ""),
                "average_confidence": row.get("average_confidence", ""),
                "support": row.get("support", ""),
                "source_surfaces": row.get("source_surfaces", ""),
                "target_surfaces": row.get("target_surfaces", ""),
                "parent_phrases": row.get("parent_phrases", ""),
                "case_names": row.get("case_names", ""),
                "existing_targets_for_source": " | ".join(source_targets),
                "existing_sources_for_target": " | ".join(target_sources),
            }
        )
    return rows


def build_promotion_proposal_rows(promotion_diff_rows):
    rows = []
    for row in promotion_diff_rows:
        if row.get("status", "") != "novel":
            continue
        rows.append(
            {
                "proposal_id": len(rows),
                "candidate_kind": "promotion_proposal",
                "proposal_action": "propose_promote_to_word_network",
                "pos_tag": row.get("pos_tag", ""),
                "source_normalized": row.get("source_normalized", ""),
                "target_normalized": row.get("target_normalized", ""),
                "occurrences": row.get("occurrences", ""),
                "average_confidence": row.get("average_confidence", ""),
                "support": row.get("support", ""),
                "source_surfaces": row.get("source_surfaces", ""),
                "target_surfaces": row.get("target_surfaces", ""),
                "parent_phrases": row.get("parent_phrases", ""),
                "case_names": row.get("case_names", ""),
                "notes": "novel_ready_component_projection",
            }
        )
    return rows


def build_promotion_followup_rows(promotion_diff_rows):
    rows = []
    for row in promotion_diff_rows:
        status = row.get("status", "")
        if status in ("", "exact_match", "novel"):
            continue
        rows.append(
            {
                "followup_id": len(rows),
                "candidate_kind": "promotion_followup",
                "followup_action": "requires_existing_network_decision",
                "status": status,
                "pos_tag": row.get("pos_tag", ""),
                "source_normalized": row.get("source_normalized", ""),
                "target_normalized": row.get("target_normalized", ""),
                "occurrences": row.get("occurrences", ""),
                "average_confidence": row.get("average_confidence", ""),
                "support": row.get("support", ""),
                "source_surfaces": row.get("source_surfaces", ""),
                "target_surfaces": row.get("target_surfaces", ""),
                "parent_phrases": row.get("parent_phrases", ""),
                "case_names": row.get("case_names", ""),
                "existing_targets_for_source": row.get(
                    "existing_targets_for_source", ""
                ),
                "existing_sources_for_target": row.get(
                    "existing_sources_for_target", ""
                ),
                "notes": status,
            }
        )
    return rows


def classify_promotion_diff_status(has_exact_match, has_source_overlap, has_target_overlap):
    if has_exact_match:
        return "exact_match"
    if has_source_overlap and has_target_overlap:
        return "source_and_target_overlap"
    if has_source_overlap:
        return "source_overlap_different_target"
    if has_target_overlap:
        return "target_overlap_different_source"
    return "novel"


def count_promotion_status(rows, status):
    return sum(1 for row in rows if row.get("status", "") == status)


def inspect_staging_snapshot(
    snapshot,
    *,
    kind="all",
    query=None,
    min_occurrences=1,
    min_support=1,
    promotion_bucket=None,
    limit=20,
):
    sections = {}
    if kind in ("all", "existing"):
        sections["existing_word_network_rows"] = select_network_rows(
            snapshot.get("existing_word_network_rows", []),
            query=query,
            min_occurrences=min_occurrences,
            min_support=min_support,
            promotion_bucket=None,
            limit=limit,
        )
    if kind in ("all", "auto"):
        sections["auto_component_rows"] = select_network_rows(
            snapshot.get("auto_component_rows", []),
            query=query,
            min_occurrences=min_occurrences,
            min_support=min_support,
            promotion_bucket=promotion_bucket,
            limit=limit,
        )
    if kind in ("all", "promotion"):
        sections["promotion_ready_word_network_rows"] = select_network_rows(
            snapshot.get("promotion_ready_word_network_rows", []),
            query=query,
            min_occurrences=min_occurrences,
            min_support=min_support,
            promotion_bucket=None,
            limit=limit,
        )
    if kind in ("all", "promotion-diff"):
        sections["promotion_diff_rows"] = select_plain_rows(
            snapshot.get("promotion_diff_rows", []),
            query=query,
            limit=limit,
        )
    if kind in ("all", "promotion-proposal"):
        sections["promotion_proposal_rows"] = select_network_rows(
            snapshot.get("promotion_proposal_rows", []),
            query=query,
            min_occurrences=min_occurrences,
            min_support=min_support,
            promotion_bucket=None,
            limit=limit,
        )
    if kind in ("all", "promotion-followup"):
        sections["promotion_followup_rows"] = select_plain_rows(
            snapshot.get("promotion_followup_rows", []),
            query=query,
            limit=limit,
        )
    if kind in ("all", "phrase"):
        sections["phrase_network_rows"] = select_network_rows(
            snapshot.get("phrase_network_rows", []),
            query=query,
            min_occurrences=min_occurrences,
            min_support=min_support,
            promotion_bucket=promotion_bucket,
            limit=limit,
        )
    if kind in ("all", "combined"):
        sections["combined_network_rows"] = select_network_rows(
            snapshot.get("combined_network_rows", []),
            query=query,
            min_occurrences=min_occurrences,
            min_support=min_support,
            promotion_bucket=promotion_bucket,
            limit=limit,
        )
    if kind in ("all", "review"):
        sections["review_rows"] = select_review_rows(
            snapshot.get("review_rows", []),
            query=query,
            limit=limit,
        )
    return {
        "source_kind": snapshot.get("source_kind", "aggregated"),
        "input_dir": snapshot.get("input_dir", ""),
        "summary": snapshot["summary"],
        "selection": {
            "kind": kind,
            "query": query or "",
            "min_occurrences": min_occurrences,
            "min_support": min_support,
            "promotion_bucket": promotion_bucket or "",
            "limit": limit,
        },
        "sections": sections,
    }


def select_network_rows(
    rows,
    *,
    query=None,
    min_occurrences=1,
    min_support=1,
    promotion_bucket=None,
    limit=20,
):
    filtered = []
    for row in rows:
        occurrences = int_or_zero(row.get("occurrences"))
        support = int_or_zero(row.get("support", row.get("case_count")))
        if occurrences < min_occurrences or support < min_support:
            continue
        if promotion_bucket and row.get("promotion_bucket", "") != promotion_bucket:
            continue
        if query and query.lower() not in build_search_blob(row):
            continue
        filtered.append(row)
    return {
        "matching_count": len(filtered),
        "displayed_count": len(filtered[:limit]),
        "rows": filtered[:limit],
    }


def select_review_rows(rows, *, query=None, limit=20):
    filtered = []
    for row in rows:
        if query and query.lower() not in build_search_blob(row):
            continue
        filtered.append(row)
    return {
        "matching_count": len(filtered),
        "displayed_count": len(filtered[:limit]),
        "rows": filtered[:limit],
    }


def select_plain_rows(rows, *, query=None, limit=20):
    filtered = []
    for row in rows:
        if query and query.lower() not in build_search_blob(row):
            continue
        filtered.append(row)
    return {
        "matching_count": len(filtered),
        "displayed_count": len(filtered[:limit]),
        "rows": filtered[:limit],
    }


def format_inspection_text(report):
    lines = [
        "[source]",
        f"kind: {report['source_kind']}",
        f"path: {report['input_dir']}",
        "",
        "[summary]",
        f"phrase rows total: {report['summary'].get('phrase_network_rows', 0)}",
        f"auto component rows total: {report['summary'].get('auto_component_rows', 0)}",
        f"ready auto rows total: {report['summary'].get('ready_auto_component_rows', 0)}",
        "candidate auto rows total: "
        f"{report['summary'].get('candidate_auto_component_rows', 0)}",
        "existing word rows total: "
        f"{report['summary'].get('existing_word_network_rows', 0)}",
        "promotion-ready word rows total: "
        f"{report['summary'].get('promotion_ready_word_network_rows', 0)}",
        "promotion diff exact/source/target/novel: "
        f"{report['summary'].get('promotion_exact_match_rows', 0)}/"
        f"{report['summary'].get('promotion_source_overlap_rows', 0)}/"
        f"{report['summary'].get('promotion_target_overlap_rows', 0)}/"
        f"{report['summary'].get('promotion_novel_rows', 0)}",
        "promotion proposals/followups: "
        f"{report['summary'].get('promotion_proposal_rows', 0)}/"
        f"{report['summary'].get('promotion_followup_rows', 0)}",
        f"combined rows total: {report['summary'].get('combined_network_rows', 0)}",
        f"review rows total: {report['summary'].get('review_rows', 0)}",
        "",
        "[selection]",
        f"kind: {report['selection']['kind']}",
        f"query: {report['selection']['query'] or '(none)'}",
        f"min occurrences: {report['selection']['min_occurrences']}",
        f"min support: {report['selection']['min_support']}",
        f"promotion bucket: {report['selection']['promotion_bucket'] or '(any)'}",
        f"limit per section: {report['selection']['limit']}",
    ]
    for section_name, title in (
        ("existing_word_network_rows", "existing word rows"),
        ("auto_component_rows", "auto component rows"),
        ("promotion_ready_word_network_rows", "promotion-ready word rows"),
        ("promotion_diff_rows", "promotion diff rows"),
        ("promotion_proposal_rows", "promotion proposal rows"),
        ("promotion_followup_rows", "promotion followup rows"),
        ("phrase_network_rows", "phrase rows"),
        ("combined_network_rows", "combined rows"),
        ("review_rows", "review rows"),
    ):
        section = report["sections"].get(section_name)
        if section is None:
            continue
        lines.append("")
        lines.append(
            f"[{title}] matching={section['matching_count']} displayed={section['displayed_count']}"
        )
        if not section["rows"]:
            lines.append("(none)")
            continue
        for row in section["rows"]:
            lines.extend(format_section_row(section_name, row))
    return "\n".join(lines)


def format_section_row(section_name, row):
    if section_name == "review_rows":
        lines = [
            f"{row.get('case_name', '(ad-hoc)')}: "
            f"{row.get('source_normalized', '')} -> {row.get('target_normalized', '')}"
            f" | confidence={row.get('confidence', '')}"
        ]
        if row.get("component_projection_pairs"):
            lines.append(f"  components: {row['component_projection_pairs']}")
        if row.get("reason"):
            lines.append(f"  reason: {row['reason']}")
        return lines
    if section_name == "promotion_diff_rows":
        lines = [
            f"{row.get('status', '')} {row.get('pos_tag', '')}: "
            f"{row.get('source_normalized', '')} -> {row.get('target_normalized', '')}"
            f" | occurrences={row.get('occurrences', '')}"
        ]
        if row.get("existing_targets_for_source"):
            lines.append(
                f"  existing targets for source: {row['existing_targets_for_source']}"
            )
        if row.get("existing_sources_for_target"):
            lines.append(
                f"  existing sources for target: {row['existing_sources_for_target']}"
            )
        if row.get("parent_phrases"):
            lines.append(f"  parent phrases: {row['parent_phrases']}")
        if row.get("case_names"):
            lines.append(f"  cases: {row['case_names']}")
        return lines
    if section_name == "promotion_followup_rows":
        lines = [
            f"{row.get('status', '')} {row.get('pos_tag', '')}: "
            f"{row.get('source_normalized', '')} -> {row.get('target_normalized', '')}"
            f" | occurrences={row.get('occurrences', '')}"
        ]
        if row.get("existing_targets_for_source"):
            lines.append(
                f"  existing targets for source: {row['existing_targets_for_source']}"
            )
        if row.get("existing_sources_for_target"):
            lines.append(
                f"  existing sources for target: {row['existing_sources_for_target']}"
            )
        if row.get("parent_phrases"):
            lines.append(f"  parent phrases: {row['parent_phrases']}")
        if row.get("case_names"):
            lines.append(f"  cases: {row['case_names']}")
        return lines
    lines = [
        f"{row.get('candidate_kind', section_name)} {row.get('pos_tag', '')}: "
        f"{row.get('source_normalized', '')} -> {row.get('target_normalized', '')}"
        f" | occurrences={row.get('occurrences', '')}"
    ]
    if row.get("average_confidence") not in ("", None):
        lines[0] += f" | avg_conf={row['average_confidence']}"
    if row.get("promotion_bucket"):
        lines[0] += f" | promotion={row['promotion_bucket']}"
    support = row.get("support", row.get("case_count"))
    if support not in ("", None):
        lines[0] += f" | support={support}"
    if row.get("source_surfaces") or row.get("target_surfaces"):
        lines.append(
            f"  surfaces: {row.get('source_surfaces', '')} => "
            f"{row.get('target_surfaces', '')}"
        )
    if row.get("parent_phrases"):
        lines.append(f"  parent phrases: {row['parent_phrases']}")
    if row.get("case_names"):
        lines.append(f"  cases: {row['case_names']}")
    notes = row.get("notes", row.get("reasons", ""))
    if notes:
        lines.append(f"  notes: {notes}")
    return lines


def sort_bucket_values(values):
    return sorted(
        values,
        key=lambda item: (
            item.get("candidate_kind", ""),
            -item.get("occurrences", 0),
            item.get("pos_tag", ""),
            item.get("source_normalized", ""),
            item.get("target_normalized", ""),
        ),
    )


def add_pipe_separated(bucket, value):
    if not value:
        return
    for part in str(value).split(" | "):
        part = part.strip()
        if part:
            bucket.add(part)


def compute_average_confidence(bucket):
    if bucket["confidence_occurrences"] == 0:
        return ""
    return bucket["confidence_weighted_sum"] / bucket["confidence_occurrences"]


def classify_auto_component_promotion_bucket(bucket):
    average_confidence = compute_average_confidence(bucket)
    reasons = bucket.get("reasons", set())
    occurrences = bucket.get("occurrences", 0)
    case_support = len(bucket.get("case_names", ()))
    if occurrences >= 2 or case_support >= 2:
        return "ready"
    if average_confidence not in ("", None) and average_confidence >= 0.98:
        return "ready"
    if "reverse_of_genitive_compound_projection" in reasons:
        return "candidate"
    return "candidate"


def select_rows_by_promotion_bucket(rows, promotion_bucket):
    return [
        row
        for row in rows
        if row.get("promotion_bucket", "") == promotion_bucket
    ]


def build_search_blob(row):
    return " ".join(str(value).lower() for value in row.values() if value not in ("", None))


def int_or_zero(value):
    if value in ("", None):
        return 0
    return int(value)


def write_aggregated_tables(output_dir, aggregated):
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "summary.json").write_text(
        json.dumps(aggregated["summary"], indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    )
    write_csv_rows(path / "phrase-network-relations.csv", aggregated["phrase_network_rows"])
    write_csv_rows(
        path / "auto-component-word-relations.csv",
        aggregated["auto_component_rows"],
    )
    write_csv_rows(
        path / "ready-auto-component-word-relations.csv",
        aggregated["ready_auto_component_rows"],
    )
    write_csv_rows(
        path / "candidate-auto-component-word-relations.csv",
        aggregated["candidate_auto_component_rows"],
    )
    write_csv_rows(
        path / "existing-word-network.csv",
        aggregated["existing_word_network_rows"],
    )
    write_csv_rows(
        path / "promotion-ready-word-network.csv",
        aggregated["promotion_ready_word_network_rows"],
    )
    write_csv_rows(
        path / "promotion-ready-diff.csv",
        aggregated["promotion_diff_rows"],
    )
    write_csv_rows(
        path / "promotion-ready-proposals.csv",
        aggregated["promotion_proposal_rows"],
    )
    write_csv_rows(
        path / "promotion-followup.csv",
        aggregated["promotion_followup_rows"],
    )
    write_csv_rows(
        path / "lexical-network-staging.csv",
        aggregated["combined_network_rows"],
    )
    write_csv_rows(path / "review-queue.csv", aggregated["review_rows"])


def load_csv_rows(path):
    csv_path = Path(path)
    if not csv_path.exists():
        return []
    text = csv_path.read_text()
    if not text.strip():
        return []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path, rows):
    if not rows:
        path.write_text("")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
