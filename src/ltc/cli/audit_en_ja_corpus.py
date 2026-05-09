"""Audit a few tracked corpus rows through the en_ja alignment path."""

from __future__ import annotations

import argparse
import json
import sys
import warnings

from ltc.evaluation.en_ja_corpus_audit import default_corpus_path, run_corpus_audit


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Run the en_ja alignment path on tracked corpus rows."
    )
    parser.add_argument(
        "--input",
        default=str(default_corpus_path()),
        help="Path to a corpus_en_ja.csv-style file.",
    )
    parser.add_argument(
        "--row-id",
        action="append",
        help="Only run selected corpus id(s). Can be passed multiple times.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help=(
            "Rows to audit. For head selection this means the first N rows; "
            "for random/stratified it becomes the sample size."
        ),
    )
    parser.add_argument(
        "--selection",
        choices=("head", "random", "stratified"),
        default="head",
        help="How to choose rows when --limit is set.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=13,
        help="Random seed for random/stratified row selection.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser.parse_args(argv[1:])


def format_text(payload):
    selection = payload.get("selection", {})
    lines = [
        "[runtime]",
        payload["runtime"]["note"],
        f"selection: {selection.get('strategy', 'head')}"
        + (
            f" (seed={selection.get('seed')}, rows={len(selection.get('row_ids', []))})"
            if selection
            else ""
        ),
        "",
    ]
    for result in payload["rows"]:
        lines.append(f"[row {result.corpus_id}]")
        lines.append(f"source: {result.source}")
        lines.append(f"target: {result.target}")
        actual_pairs = ", ".join(
            f"{pair.pos}:{pair.src}->{pair.tgt}" for pair in result.actual_pairs
        )
        lines.append(f"actual: {actual_pairs or '(none)'}")
        lines.append("")
    lines.append(f"summary: {len(payload['rows'])} rows")
    return "\n".join(lines)


def format_json(payload):
    serializable = {
        "runtime": payload["runtime"],
        "selection": payload.get("selection", {}),
        "rows": [result.as_dict() for result in payload["rows"]],
    }
    return json.dumps(serializable, indent=2, ensure_ascii=False, sort_keys=True)


def main(argv=None):
    argv = sys.argv if argv is None else argv
    args = parse_args(argv)
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="alignment.en_ja is using the fallback smoke/dev model.*",
            category=RuntimeWarning,
        )
        payload = run_corpus_audit(
            path=args.input,
            selected_ids=tuple(args.row_id) if args.row_id else None,
            limit=args.limit,
            selection=args.selection,
            seed=args.seed,
        )
    if args.format == "json":
        print(format_json(payload))
    else:
        print(format_text(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
