"""CLI for small curated en_ja quality checks."""

from __future__ import annotations

import argparse
import json
import sys
import warnings

from ltc.evaluation.en_ja_quality import default_cases_path, run_quality_suite


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Run small curated quality checks for the en_ja alignment path."
    )
    parser.add_argument(
        "--cases",
        default=str(default_cases_path()),
        help="Path to the quality case JSON file.",
    )
    parser.add_argument(
        "--case",
        action="append",
        help="Only run selected case name(s). Can be passed multiple times.",
    )
    parser.add_argument(
        "--suite",
        choices=("core", "extended"),
        default="core",
        help="Run the fast core suite or the broader extended suite.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit with status 1 when any case fails.",
    )
    return parser.parse_args(argv[1:])


def format_text(payload):
    lines = []
    runtime = payload["runtime"]
    lines.append("[runtime]")
    lines.append(runtime["note"])
    lines.append(f"suite: {payload['suite']}")
    lines.append("")
    for result in payload["cases"]:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"[{status}] {result.name} ({result.tier})")
        if result.notes:
            lines.append(f"note: {result.notes}")
        actual_pairs = ", ".join(
            f"{pair.pos}:{pair.src}->{pair.tgt}" for pair in result.actual_pairs
        )
        lines.append(f"actual: {actual_pairs or '(none)'}")
        if result.tier == "core":
            if result.actual_alignments:
                lines.append("alignment:")
                for alignment in result.actual_alignments:
                    score_bits = []
                    if alignment.best_alignment_score is not None:
                        score_bits.append(f"best={alignment.best_alignment_score:.4f}")
                    if alignment.average_alignment_score is not None:
                        score_bits.append(f"avg={alignment.average_alignment_score:.4f}")
                    if alignment.alignment_evidence_count is not None:
                        score_bits.append(
                            f"count={alignment.alignment_evidence_count}"
                        )
                    score_suffix = (
                        " [" + " ".join(score_bits) + "]" if score_bits else ""
                    )
                    lines.append(
                        "  "
                        f"{alignment.pos}: {alignment.src_surface} -> {alignment.tgt_surface}"
                        f" | normalized: {alignment.src_normalized} -> {alignment.tgt_normalized}"
                        f"{score_suffix}"
                    )
            else:
                lines.append("alignment: (none)")
        if result.missing_pairs:
            missing_pairs = ", ".join(
                f"{pair.pos}:{pair.src}->{pair.tgt}" for pair in result.missing_pairs
            )
            lines.append(f"missing: {missing_pairs}")
        if result.forbidden_hits:
            forbidden_pairs = ", ".join(
                f"{pair.pos}:{pair.src}->{pair.tgt}"
                for pair in result.forbidden_hits
            )
            lines.append(f"forbidden: {forbidden_pairs}")
        if result.unexpected_pairs:
            unexpected_pairs = ", ".join(
                f"{pair.pos}:{pair.src}->{pair.tgt}"
                for pair in result.unexpected_pairs
            )
            lines.append(f"unexpected: {unexpected_pairs}")
        lines.append("")
    lines.append(
        f"summary: {payload['passed']} passed, {payload['failed']} failed"
    )
    return "\n".join(lines)


def format_json(payload):
    serializable = {
        "runtime": payload["runtime"],
        "cases": [result.as_dict() for result in payload["cases"]],
        "passed": payload["passed"],
        "failed": payload["failed"],
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
        payload = run_quality_suite(
            path=args.cases,
            selected_case_names=tuple(args.case) if args.case else None,
            suite=args.suite,
        )
    if args.format == "json":
        print(format_json(payload))
    else:
        print(format_text(payload))

    if args.fail_on_error and payload["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    raise SystemExit(main())
