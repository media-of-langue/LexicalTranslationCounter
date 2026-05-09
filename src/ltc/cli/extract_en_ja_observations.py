"""Extract phrase-aware en_ja observation artifacts for review."""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

from ltc.evaluation.en_ja_quality import default_cases_path
from ltc.inspection.en_ja import resolve_inspection_request
from ltc.observation_exports.en_ja import (
    build_bundle_for_quality_suite,
    build_bundle_for_request,
    write_bundle_directory,
)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description=(
            "Extract en_ja word/phrase observations and lexicalization review "
            "artifacts without changing the legacy count output."
        )
    )
    parser.add_argument("--source", help="English source sentence.")
    parser.add_argument("--target", help="Japanese target sentence.")
    parser.add_argument(
        "--case",
        help="Name of a curated en_ja quality case to extract.",
    )
    parser.add_argument(
        "--cases",
        default=str(default_cases_path()),
        help="Path to the en_ja quality case JSON file.",
    )
    parser.add_argument(
        "--suite",
        choices=("core", "extended"),
        default="core",
        help="Curated suite to extract when --case is not provided.",
    )
    parser.add_argument(
        "--select-case",
        action="append",
        default=[],
        help="Restrict suite extraction to these case names. Repeatable.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json", "jsonl"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--output",
        help="Optional output path. When omitted, the selected format is written to stdout.",
    )
    parser.add_argument(
        "--output-dir",
        help=(
            "Optional directory for writing bundle.json, documents.jsonl, "
            "auto-component-word-candidates.jsonl, phrase-network-candidates.jsonl, "
            "and review-queue.jsonl."
        ),
    )
    return parser.parse_args(argv[1:])


def format_text(bundle):
    summary = bundle["summary"]
    lines = []
    lines.append("[summary]")
    lines.append(f"documents: {summary['documents']}")
    lines.append(f"word observations: {summary['word_observations']}")
    lines.append(f"phrase observations: {summary['phrase_observations']}")
    lines.append(f"component projections: {summary['component_projections']}")
    lines.append("lexicalization decisions:")
    if summary["lexicalization_decisions"]:
        for action, count in sorted(summary["lexicalization_decisions"].items()):
            lines.append(f"  {action}: {count}")
    else:
        lines.append("  (none)")
    candidate_tables = bundle["candidate_tables"]
    staging_tables = bundle["staging_tables"]
    lines.append("")
    lines.append("[candidate tables]")
    lines.append(
        "phrase network candidates: "
        f"{len(candidate_tables['phrase_network_candidates'])}"
    )
    lines.append(
        "auto component word candidates: "
        f"{len(candidate_tables['auto_component_word_candidates'])}"
    )
    lines.append(f"review queue: {len(candidate_tables['review_queue'])}")
    lines.append("")
    lines.append("[staging tables]")
    lines.append(
        "phrase network staging rows: "
        f"{len(staging_tables['phrase_network_staging'])}"
    )
    lines.append(
        "auto component word staging rows: "
        f"{len(staging_tables['auto_component_word_staging'])}"
    )
    lines.append(
        "review queue staging rows: "
        f"{len(staging_tables['review_queue_staging'])}"
    )
    lines.append("")
    lines.append("[documents]")
    for document in bundle["documents"]:
        request = document["request"]
        lines.append(
            f"{request.get('name') or '(ad-hoc)'}: "
            f"words={len(document['word_observations'])}, "
            f"phrases={len(document['phrase_observations'])}, "
            f"decisions={len(document['lexicalization_decisions'])}"
        )
        for decision in document["lexicalization_decisions"]:
            lines.append(
                "  "
                f"{decision['recommended_action']}: "
                f"{decision['source_normalized']} -> {decision['target_normalized']}"
            )
    if candidate_tables["auto_component_word_candidates"]:
        lines.append("")
        lines.append("[auto component word candidates]")
        for row in candidate_tables["auto_component_word_candidates"]:
            lines.append(
                f"{row['pos_tag']}: {row['source_normalized']} -> {row['target_normalized']}"
                f" | occurrences={row['occurrences']}"
            )
    if candidate_tables["review_queue"]:
        lines.append("")
        lines.append("[review queue]")
        for row in candidate_tables["review_queue"]:
            lines.append(
                f"{row['case_name'] or '(ad-hoc)'}: "
                f"{row['source_normalized']} -> {row['target_normalized']}"
            )
    if staging_tables["phrase_network_staging"]:
        lines.append("")
        lines.append("[phrase network staging]")
        for row in staging_tables["phrase_network_staging"]:
            lines.append(
                f"{row['pos_tag']}: {row['source_normalized']} -> {row['target_normalized']}"
                f" | occurrences={row['occurrences']}"
            )
    return "\n".join(lines)


def format_json(bundle):
    return json.dumps(bundle, indent=2, ensure_ascii=False, sort_keys=True)


def format_jsonl(bundle):
    return "\n".join(
        json.dumps(document, ensure_ascii=False, sort_keys=True)
        for document in bundle["documents"]
    )


def build_bundle(args):
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="alignment.en_ja is using the fallback smoke/dev model.*",
            category=RuntimeWarning,
        )
        if args.case or (args.source and args.target):
            request = resolve_inspection_request(
                source=args.source,
                target=args.target,
                case_name=args.case,
                cases_path=args.cases,
            )
            return build_bundle_for_request(request)
        return build_bundle_for_quality_suite(
            path=args.cases,
            selected_case_names=args.select_case,
            suite=args.suite,
        )


def select_formatter(output_format):
    if output_format == "json":
        return format_json
    if output_format == "jsonl":
        return format_jsonl
    return format_text


def write_output(text, output_path):
    path = Path(output_path)
    path.write_text(text + ("" if text.endswith("\n") or not text else "\n"))


def main(argv=None):
    argv = sys.argv if argv is None else argv
    args = parse_args(argv)
    bundle = build_bundle(args)
    formatter = select_formatter(args.format)
    rendered = formatter(bundle)
    if args.output_dir:
        write_bundle_directory(bundle, args.output_dir)
    if args.output:
        write_output(rendered, args.output)
        print(format_text(bundle))
        return 0
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
