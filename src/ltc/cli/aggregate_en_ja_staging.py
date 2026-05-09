"""Aggregate extracted en_ja observation bundles into separate staging relations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ltc.staging.en_ja import (
    aggregate_bundle_payloads,
    load_bundle_payload,
    write_aggregated_tables,
)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate one or more en_ja observation bundles into separate "
            "phrase/component staging relation tables."
        )
    )
    parser.add_argument(
        "--bundle",
        action="append",
        default=[],
        help="Path to a bundle.json file produced by extract_en_ja_observations. Repeatable.",
    )
    parser.add_argument(
        "--input-dir",
        action="append",
        default=[],
        help=(
            "Directory produced by extract_en_ja_observations --output-dir. "
            "bundle.json will be loaded from each directory. Repeatable."
        ),
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where aggregated staging CSV/JSON files will be written.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Summary format printed to stdout.",
    )
    return parser.parse_args(argv[1:])


def resolve_bundle_paths(args):
    paths = [Path(path) for path in args.bundle]
    paths.extend(Path(path) / "bundle.json" for path in args.input_dir)
    if not paths:
        raise ValueError("provide at least one --bundle or --input-dir")
    return paths


def format_text(aggregated, output_dir):
    summary = aggregated["summary"]
    lines = [
        "[summary]",
        f"bundles: {summary['bundles']}",
        f"phrase network rows: {summary['phrase_network_rows']}",
        f"auto component rows: {summary['auto_component_rows']}",
        f"ready auto component rows: {summary['ready_auto_component_rows']}",
        f"candidate auto component rows: {summary['candidate_auto_component_rows']}",
        f"existing word rows: {summary['existing_word_network_rows']}",
        "promotion-ready word network rows: "
        f"{summary['promotion_ready_word_network_rows']}",
        "promotion diff exact/source/target/novel: "
        f"{summary['promotion_exact_match_rows']}/"
        f"{summary['promotion_source_overlap_rows']}/"
        f"{summary['promotion_target_overlap_rows']}/"
        f"{summary['promotion_novel_rows']}",
        "promotion proposals/followups: "
        f"{summary['promotion_proposal_rows']}/"
        f"{summary['promotion_followup_rows']}",
        f"combined network rows: {summary['combined_network_rows']}",
        f"review rows: {summary['review_rows']}",
        "",
        "[output]",
        str(output_dir),
    ]
    if aggregated["promotion_ready_word_network_rows"]:
        lines.append("")
        lines.append("[promotion-ready word network rows]")
        for row in aggregated["promotion_ready_word_network_rows"]:
            lines.append(
                f"{row['pos_tag']}: {row['source_normalized']} -> {row['target_normalized']}"
                f" | occurrences={row['occurrences']}"
            )
    if aggregated["promotion_diff_rows"]:
        lines.append("")
        lines.append("[promotion diff rows]")
        for row in aggregated["promotion_diff_rows"]:
            lines.append(
                f"{row['status']}: {row['source_normalized']} -> {row['target_normalized']}"
            )
    if aggregated["promotion_proposal_rows"]:
        lines.append("")
        lines.append("[promotion proposal rows]")
        for row in aggregated["promotion_proposal_rows"]:
            lines.append(
                f"{row['pos_tag']}: {row['source_normalized']} -> {row['target_normalized']}"
                f" | occurrences={row['occurrences']}"
            )
    if aggregated["promotion_followup_rows"]:
        lines.append("")
        lines.append("[promotion followup rows]")
        for row in aggregated["promotion_followup_rows"]:
            lines.append(
                f"{row['status']}: {row['source_normalized']} -> {row['target_normalized']}"
            )
    if aggregated["ready_auto_component_rows"]:
        lines.append("")
        lines.append("[ready auto component rows]")
        for row in aggregated["ready_auto_component_rows"]:
            lines.append(
                f"{row['pos_tag']}: {row['source_normalized']} -> {row['target_normalized']}"
                f" | occurrences={row['occurrences']}"
            )
    if aggregated["candidate_auto_component_rows"]:
        lines.append("")
        lines.append("[candidate auto component rows]")
        for row in aggregated["candidate_auto_component_rows"]:
            lines.append(
                f"{row['pos_tag']}: {row['source_normalized']} -> {row['target_normalized']}"
                f" | occurrences={row['occurrences']}"
            )
    if aggregated["review_rows"]:
        lines.append("")
        lines.append("[review rows]")
        for row in aggregated["review_rows"]:
            lines.append(
                f"{row['case_name']}: {row['source_normalized']} -> {row['target_normalized']}"
            )
    return "\n".join(lines)


def format_json(aggregated):
    return json.dumps(aggregated, indent=2, ensure_ascii=False, sort_keys=True)


def main(argv=None):
    argv = sys.argv if argv is None else argv
    args = parse_args(argv)
    bundle_paths = resolve_bundle_paths(args)
    bundle_payloads = [load_bundle_payload(path) for path in bundle_paths]
    aggregated = aggregate_bundle_payloads(bundle_payloads)
    write_aggregated_tables(args.output_dir, aggregated)
    if args.format == "json":
        print(format_json(aggregated))
    else:
        print(format_text(aggregated, args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
