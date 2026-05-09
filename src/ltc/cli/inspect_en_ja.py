"""Inspect one en_ja sentence pair with intermediate alignment details."""

from __future__ import annotations

import argparse
import json
import sys
import warnings

from ltc.evaluation.en_ja_quality import default_cases_path
from ltc.inspection.en_ja import inspect_request, resolve_inspection_request


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Inspect one en_ja sentence pair with intermediate alignment details."
    )
    parser.add_argument("--source", help="English source sentence.")
    parser.add_argument("--target", help="Japanese target sentence.")
    parser.add_argument(
        "--case",
        help="Name of a curated en_ja quality case to inspect.",
    )
    parser.add_argument(
        "--cases",
        default=str(default_cases_path()),
        help="Path to the en_ja quality case JSON file.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser.parse_args(argv[1:])


def format_token_line(token):
    pos_text = token["pos_tag"] or "-"
    return f"{token['index']:>2}: {token['text']} [{pos_text}]"


def format_text(payload):
    lines = []
    request = payload["request"]
    runtime = payload["runtime"]
    lines.append("[runtime]")
    lines.append(runtime["note"])
    lines.append("")
    if request["name"]:
        lines.append("[case]")
        lines.append(request["name"])
        if request["notes"]:
            lines.append(f"note: {request['notes']}")
        lines.append("")
    lines.append("[source]")
    lines.append(request["source"])
    for token in payload["source"]["tokens"]:
        lines.append(format_token_line(token))
    lines.append("")
    lines.append("[target]")
    lines.append(request["target"])
    for token in payload["target"]["tokens"]:
        lines.append(format_token_line(token))
    lines.append("")
    lines.append("[ignored indices]")
    lines.append(
        "source: "
        + (", ".join(str(index) for index in payload["ignored_source_indices"]) or "(none)")
    )
    lines.append(
        "target: "
        + (", ".join(str(index) for index in payload["ignored_target_indices"]) or "(none)")
    )
    lines.append("")
    lines.append("[merged groups]")
    if not payload["merged_groups"]:
        lines.append("(none)")
    for index, group in enumerate(payload["merged_groups"]):
        src_tokens = " ".join(group["source_tokens"]) or "(none)"
        tgt_tokens = "".join(group["target_tokens"]) or "(none)"
        src_flags = ",".join(group["source_pos_tags"]) or "-"
        tgt_flags = ",".join(group["target_pos_tags"]) or "-"
        ignored = []
        if group["ignored_by_source_rule"]:
            ignored.append("source-rule")
        if group["ignored_by_target_rule"]:
            ignored.append("target-rule")
        ignored_text = f" ignored={'+'.join(ignored)}" if ignored else ""
        lines.append(
            f"{index}: src{group['source_indices']} {src_tokens} [{src_flags}]"
            f" -> tgt{group['target_indices']} {tgt_tokens} [{tgt_flags}]{ignored_text}"
        )
    lines.append("")
    lines.append("[postprocessed groups]")
    if not payload["postprocessed_groups"]:
        lines.append("(none)")
    for index, group in enumerate(payload["postprocessed_groups"]):
        src_tokens = " ".join(group["source_tokens"]) or "(none)"
        tgt_tokens = "".join(group["target_tokens"]) or "(none)"
        score_bits = []
        if group.get("best_alignment_score") is not None:
            score_bits.append(f"best={group['best_alignment_score']:.4f}")
        if group.get("average_alignment_score") is not None:
            score_bits.append(f"avg={group['average_alignment_score']:.4f}")
        score_text = f" [{' '.join(score_bits)}]" if score_bits else ""
        lines.append(
            f"{index}: src {src_tokens} ({'/'.join(group['source_pos_tags'])})"
            f" -> tgt {tgt_tokens} ({'/'.join(group['target_pos_tags'])}){score_text}"
        )
    lines.append("")
    lines.append("[source target candidates]")
    if not payload["source_target_candidates"]:
        lines.append("(none)")
    for source_item in payload["source_target_candidates"]:
        candidates_text = ", ".join(
            (
                f"{candidate['target_index']}:{candidate['target_token']}"
                f" [{candidate['target_pos_tag'] or '-'}]"
                f" {candidate['score']:.4f}"
            )
            for candidate in source_item["candidates"]
        )
        lines.append(
            f"{source_item['source_index']}: {source_item['source_token']}"
            f" [{source_item['source_pos_tag']}] -> {candidates_text or '(none)'}"
        )
    lines.append("")
    lines.append("[final pairs]")
    if not payload["final_pairs"]:
        lines.append("(none)")
    for pair in payload["final_pairs"]:
        score_bits = []
        if pair.get("best_alignment_score") is not None:
            score_bits.append(f"best={pair['best_alignment_score']:.4f}")
        if pair.get("average_alignment_score") is not None:
            score_bits.append(f"avg={pair['average_alignment_score']:.4f}")
        score_text = f" [{' '.join(score_bits)}]" if score_bits else ""
        lines.append(
            f"{pair['pos_tag']}: {pair['source_surface']} -> {pair['target_surface']}"
            f" | normalized: {pair['source_normalized']} -> {pair['target_normalized']}"
            f"{score_text}"
        )
    lines.append("")
    lines.append("[word observations]")
    if not payload.get("word_observations"):
        lines.append("(none)")
    for observation in payload.get("word_observations", []):
        lines.append(
            f"{observation['pos_tag']}: {observation['source_surface']} -> {observation['target_surface']}"
            f" | normalized: {observation['source_normalized']} -> {observation['target_normalized']}"
            f" | action: {observation['lexicalization_action']}"
        )
    lines.append("")
    lines.append("[phrase observations]")
    if not payload.get("phrase_observations"):
        lines.append("(none)")
    for index, observation in enumerate(payload.get("phrase_observations", [])):
        lines.append(
            f"{index}: {observation['source_surface']} -> {observation['target_surface']}"
            f" | normalized: {observation['source_normalized']} -> {observation['target_normalized']}"
            f" | action: {observation['lexicalization_action']}"
        )
        if observation.get("lexicalization_reason"):
            lines.append(f"   reason: {observation['lexicalization_reason']}")
        for projection in observation.get("component_projections", []):
            confidence = projection.get("confidence")
            confidence_text = (
                f" confidence={confidence:.4f}" if confidence is not None else ""
            )
            lines.append(
                "   projection: "
                f"{projection['source_surface']} -> {projection['target_surface']}"
                f" | normalized: {projection['source_normalized']} -> {projection['target_normalized']}"
                f" | status: {projection['promotion_status']}"
                f" | reason: {projection['reason']}{confidence_text}"
            )
    lines.append("")
    lines.append("[lexicalization decisions]")
    if not payload.get("lexicalization_decisions"):
        lines.append("(none)")
    for decision in payload.get("lexicalization_decisions", []):
        confidence = decision.get("confidence")
        confidence_text = f" confidence={confidence:.4f}" if confidence is not None else ""
        lines.append(
            f"{decision['recommended_action']}: "
            f"{decision['source_surface']} -> {decision['target_surface']}"
            f" | normalized: {decision['source_normalized']} -> {decision['target_normalized']}"
            f" | evidence={decision['observation_unit_level']}{confidence_text}"
        )
        if decision.get("reason"):
            lines.append(f"   reason: {decision['reason']}")
    return "\n".join(lines)


def format_json(payload):
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)


def main(argv=None):
    argv = sys.argv if argv is None else argv
    args = parse_args(argv)
    request = resolve_inspection_request(
        source=args.source,
        target=args.target,
        case_name=args.case,
        cases_path=args.cases,
    )
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="alignment.en_ja is using the fallback smoke/dev model.*",
            category=RuntimeWarning,
        )
        payload = inspect_request(request)

    if args.format == "json":
        print(format_json(payload))
    else:
        print(format_text(payload))


if __name__ == "__main__":
    raise SystemExit(main())
