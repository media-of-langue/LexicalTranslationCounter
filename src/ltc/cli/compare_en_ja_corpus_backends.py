"""Compare en_ja tracked-corpus outputs across two Japanese text backends."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT / "src"


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Compare en_ja tracked-corpus outputs across two Japanese text backends."
    )
    parser.add_argument(
        "--input",
        default=str(ROOT / "src" / "test" / "data" / "corpus_en_ja.csv"),
        help="Path to a corpus_en_ja.csv-style file.",
    )
    parser.add_argument(
        "--left-backend",
        default="jumanpp",
        help="Japanese text backend for the left-hand run.",
    )
    parser.add_argument(
        "--right-backend",
        default="sudachi_a",
        help="Japanese text backend for the right-hand run.",
    )
    parser.add_argument(
        "--left-label",
        default="jumanpp",
        help="Display label for the left-hand run.",
    )
    parser.add_argument(
        "--right-label",
        default="sudachi_a",
        help="Display label for the right-hand run.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help=(
            "Rows to compare. For head selection this means the first N rows; "
            "for random/stratified it becomes the sample size."
        ),
    )
    parser.add_argument(
        "--row-id",
        action="append",
        help="Only compare selected corpus id(s). Can be passed multiple times.",
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
        "--only-different",
        action="store_true",
        help="Only print rows whose normalized final pairs differ.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser.parse_args(argv[1:])


def build_subprocess_env(backend_name):
    env = os.environ.copy()
    env["ROOT"] = str(ROOT)
    existing_pythonpath = env.get("PYTHONPATH")
    src_text = str(SRC_DIR)
    if existing_pythonpath:
        if src_text not in existing_pythonpath.split(os.pathsep):
            env["PYTHONPATH"] = os.pathsep.join([src_text, existing_pythonpath])
    else:
        env["PYTHONPATH"] = src_text
    env["LTC_JA_TEXT_BACKEND"] = backend_name
    return env


def build_audit_command(args):
    command = [
        sys.executable,
        "-m",
        "ltc.cli.audit_en_ja_corpus",
        "--input",
        args.input,
        "--format",
        "json",
    ]
    if args.limit is not None:
        command.extend(["--limit", str(args.limit)])
    if args.selection != "head" or args.limit is not None:
        command.extend(["--selection", args.selection, "--seed", str(args.seed)])
    for row_id in args.row_id or []:
        command.extend(["--row-id", row_id])
    return command


def run_audit(command, backend_name):
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=build_subprocess_env(backend_name),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        details = stderr or stdout or f"audit subprocess exited with {result.returncode}"
        raise RuntimeError(details)
    return parse_json_payload(result.stdout)


def parse_json_payload(raw_text):
    text = raw_text.strip()
    if not text:
        raise ValueError("audit subprocess returned empty stdout")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


def build_row_map(payload):
    return {row["corpus_id"]: row for row in payload["rows"]}


def normalized_pair_tuples(row):
    return sorted((pair["pos"], pair["src"], pair["tgt"]) for pair in row["actual_pairs"])


def compare_rows(left_row, right_row):
    left_pairs = normalized_pair_tuples(left_row)
    right_pairs = normalized_pair_tuples(right_row)
    left_set = set(left_pairs)
    right_set = set(right_pairs)
    return {
        "corpus_id": left_row["corpus_id"],
        "source": left_row["source"],
        "target": left_row["target"],
        "left_pairs": left_pairs,
        "right_pairs": right_pairs,
        "only_left_pairs": sorted(left_set - right_set),
        "only_right_pairs": sorted(right_set - left_set),
        "same": left_pairs == right_pairs,
    }


def build_payload(args, left_payload, right_payload):
    left_rows = build_row_map(left_payload)
    right_rows = build_row_map(right_payload)
    shared_ids = sorted(set(left_rows) & set(right_rows), key=lambda value: int(value))
    compared_rows = [compare_rows(left_rows[row_id], right_rows[row_id]) for row_id in shared_ids]
    same_rows = sum(1 for row in compared_rows if row["same"])
    different_rows = len(compared_rows) - same_rows
    rows_with_only_left_pairs = sum(1 for row in compared_rows if row["only_left_pairs"])
    rows_with_only_right_pairs = sum(1 for row in compared_rows if row["only_right_pairs"])
    total_only_left_pairs = sum(len(row["only_left_pairs"]) for row in compared_rows)
    total_only_right_pairs = sum(len(row["only_right_pairs"]) for row in compared_rows)
    return {
        "left": {
            "label": args.left_label,
            "backend": args.left_backend,
            "runtime": left_payload["runtime"],
        },
        "right": {
            "label": args.right_label,
            "backend": args.right_backend,
            "runtime": right_payload["runtime"],
        },
        "selection": left_payload.get(
            "selection",
            {
                "strategy": getattr(args, "selection", "head"),
                "seed": getattr(args, "seed", 13),
                "limit": getattr(args, "limit", None),
            },
        ),
        "summary": {
            "rows_compared": len(compared_rows),
            "same_rows": same_rows,
            "different_rows": different_rows,
            "rows_with_only_left_pairs": rows_with_only_left_pairs,
            "rows_with_only_right_pairs": rows_with_only_right_pairs,
            "total_only_left_pairs": total_only_left_pairs,
            "total_only_right_pairs": total_only_right_pairs,
        },
        "rows": compared_rows,
    }


def format_pair_list(pairs):
    return ", ".join(f"{pos}:{src}->{tgt}" for pos, src, tgt in pairs) or "(none)"


def format_text(payload, only_different=False):
    selection = payload.get("selection", {})
    lines = [
        "[left]",
        payload["left"]["runtime"]["note"],
        f"label: {payload['left']['label']}",
        f"backend: {payload['left']['backend']}",
        "",
        "[right]",
        payload["right"]["runtime"]["note"],
        f"label: {payload['right']['label']}",
        f"backend: {payload['right']['backend']}",
        "",
        "[summary]",
        (
            f"selection: {selection.get('strategy', 'head')}"
            + (
                f" (seed={selection.get('seed')}, rows={len(selection.get('row_ids', []))})"
                if selection
                else ""
            )
        ),
        f"rows compared: {payload['summary']['rows_compared']}",
        f"same rows: {payload['summary']['same_rows']}",
        f"different rows: {payload['summary']['different_rows']}",
        f"rows with only {payload['left']['label']} pairs: {payload['summary']['rows_with_only_left_pairs']}",
        f"rows with only {payload['right']['label']} pairs: {payload['summary']['rows_with_only_right_pairs']}",
        f"total only {payload['left']['label']} pairs: {payload['summary']['total_only_left_pairs']}",
        f"total only {payload['right']['label']} pairs: {payload['summary']['total_only_right_pairs']}",
        "",
    ]
    rows = payload["rows"]
    if only_different:
        rows = [row for row in rows if not row["same"]]
    for row in rows:
        lines.append(f"[row {row['corpus_id']}]")
        lines.append(f"source: {row['source']}")
        lines.append(f"target: {row['target']}")
        lines.append(
            f"{payload['left']['label']}: {format_pair_list(row['left_pairs'])}"
        )
        lines.append(
            f"{payload['right']['label']}: {format_pair_list(row['right_pairs'])}"
        )
        if not row["same"]:
            lines.append(
                f"only {payload['left']['label']}: {format_pair_list(row['only_left_pairs'])}"
            )
            lines.append(
                f"only {payload['right']['label']}: {format_pair_list(row['only_right_pairs'])}"
            )
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    argv = sys.argv if argv is None else argv
    args = parse_args(argv)
    command = build_audit_command(args)
    left_payload = run_audit(command, args.left_backend)
    right_payload = run_audit(command, args.right_backend)
    payload = build_payload(args, left_payload, right_payload)
    if args.format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(format_text(payload, only_different=args.only_different))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
