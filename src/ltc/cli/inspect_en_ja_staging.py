"""Inspect en_ja staging candidates without opening the CSV files directly."""

from __future__ import annotations

import argparse
import json
import sys

from ltc.staging.en_ja import (
    format_inspection_text,
    inspect_staging_snapshot,
    load_staging_snapshot,
)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description=(
            "Inspect en_ja phrase/component staging candidates from either an "
            "extracted bundle directory or an aggregated staging directory."
        )
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help=(
            "Either an extract_en_ja_observations --output-dir directory "
            "(bundle.json) or an aggregate_en_ja_staging output directory "
            "(summary.json + CSV files)."
        ),
    )
    parser.add_argument(
        "--kind",
        choices=(
            "all",
            "existing",
            "auto",
            "promotion",
            "promotion-diff",
            "promotion-proposal",
            "promotion-followup",
            "phrase",
            "combined",
            "review",
        ),
        default="all",
        help="Which staging section to inspect.",
    )
    parser.add_argument(
        "--query",
        help="Optional case-insensitive text filter across source/target/cases/reasons.",
    )
    parser.add_argument(
        "--min-occurrences",
        type=int,
        default=1,
        help="Minimum occurrence count for non-review rows.",
    )
    parser.add_argument(
        "--min-support",
        type=int,
        default=1,
        help="Minimum support/case count for non-review rows.",
    )
    parser.add_argument(
        "--promotion-bucket",
        choices=("ready", "candidate"),
        help="Optional filter for staging promotion strength.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum rows displayed per section.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser.parse_args(argv[1:])


def main(argv=None):
    argv = sys.argv if argv is None else argv
    args = parse_args(argv)
    snapshot = load_staging_snapshot(args.input_dir)
    report = inspect_staging_snapshot(
        snapshot,
        kind=args.kind,
        query=args.query,
        min_occurrences=args.min_occurrences,
        min_support=args.min_support,
        promotion_bucket=args.promotion_bucket,
        limit=args.limit,
    )
    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(format_inspection_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
