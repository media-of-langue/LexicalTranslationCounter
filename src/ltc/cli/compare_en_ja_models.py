"""Compare one en_ja inspection case across two model specs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from ltc.evaluation.en_ja_quality import default_cases_path


ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT / "src"


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Compare one en_ja inspection case across two model specs."
    )
    parser.add_argument("--source", help="English source sentence.")
    parser.add_argument("--target", help="Japanese target sentence.")
    parser.add_argument("--case", help="Name of a curated en_ja quality case.")
    parser.add_argument(
        "--cases",
        default=str(default_cases_path()),
        help="Path to the en_ja quality case JSON file.",
    )
    parser.add_argument(
        "--left-model",
        default="bert-base-multilingual-cased",
        help="Model spec for the left-hand run.",
    )
    parser.add_argument(
        "--right-model",
        default="bert-base-multilingual-cased",
        help="Model spec for the right-hand run.",
    )
    parser.add_argument(
        "--left-label",
        default="left",
        help="Display label for the left-hand run.",
    )
    parser.add_argument(
        "--right-label",
        default="right",
        help="Display label for the right-hand run.",
    )
    parser.add_argument(
        "--left-backend",
        default="awesome",
        choices=("awesome", "simalign"),
        help="Alignment backend for the left-hand run.",
    )
    parser.add_argument(
        "--right-backend",
        default="awesome",
        choices=("awesome", "simalign"),
        help="Alignment backend for the right-hand run.",
    )
    parser.add_argument(
        "--left-simalign-method",
        default="mwmf",
        choices=("inter", "mwmf", "itermax"),
        help="SimAlign method for the left-hand run when backend is simalign.",
    )
    parser.add_argument(
        "--right-simalign-method",
        default="mwmf",
        choices=("inter", "mwmf", "itermax"),
        help="SimAlign method for the right-hand run when backend is simalign.",
    )
    parser.add_argument(
        "--left-simalign-model",
        default="bert",
        help="SimAlign model spec for the left-hand run when backend is simalign.",
    )
    parser.add_argument(
        "--right-simalign-model",
        default="bert",
        help="SimAlign model spec for the right-hand run when backend is simalign.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser.parse_args(argv[1:])


def build_inspect_command(args):
    command = [
        sys.executable,
        "-m",
        "ltc.cli.inspect_en_ja",
        "--format",
        "json",
        "--cases",
        args.cases,
    ]
    if args.case:
        command.extend(["--case", args.case])
    else:
        command.extend(["--source", args.source, "--target", args.target])
    return command


def build_subprocess_env(model_spec, backend, simalign_method, simalign_model):
    env = os.environ.copy()
    env["ROOT"] = str(ROOT)
    existing_pythonpath = env.get("PYTHONPATH")
    src_text = str(SRC_DIR)
    if existing_pythonpath:
        if src_text not in existing_pythonpath.split(os.pathsep):
            env["PYTHONPATH"] = os.pathsep.join([src_text, existing_pythonpath])
    else:
        env["PYTHONPATH"] = src_text
    env["LTC_AWESOME_ALIGN_MODEL_EN_JA"] = model_spec
    env["LTC_EN_JA_ALIGNMENT_BACKEND"] = backend
    env["LTC_EN_JA_SIMALIGN_METHOD"] = simalign_method
    env["LTC_EN_JA_SIMALIGN_MODEL"] = simalign_model
    return env


def run_inspection(command, model_spec, backend, simalign_method, simalign_model):
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=build_subprocess_env(
            model_spec,
            backend=backend,
            simalign_method=simalign_method,
            simalign_model=simalign_model,
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        details = stderr or stdout or f"inspect subprocess exited with {result.returncode}"
        raise RuntimeError(details)
    return json.loads(result.stdout)


def normalized_final_pairs(payload):
    return [
        (
            pair["pos_tag"],
            pair["source_normalized"],
            pair["target_normalized"],
        )
        for pair in payload["final_pairs"]
    ]


def top_candidate_summary(payload):
    items = []
    for entry in payload["source_target_candidates"]:
        if not entry["candidates"]:
            continue
        top_candidate = entry["candidates"][0]
        items.append(
            {
                "source_index": entry["source_index"],
                "source_token": entry["source_token"],
                "source_pos_tag": entry["source_pos_tag"],
                "target_token": top_candidate["target_token"],
                "target_pos_tag": top_candidate["target_pos_tag"],
                "score": top_candidate["score"],
            }
        )
    return items


def compare_candidate_views(left_payload, right_payload):
    left_items = {
        item["source_index"]: item for item in top_candidate_summary(left_payload)
    }
    right_items = {
        item["source_index"]: item for item in top_candidate_summary(right_payload)
    }
    diffs = []
    for source_index in sorted(set(left_items) | set(right_items)):
        left_item = left_items.get(source_index)
        right_item = right_items.get(source_index)
        if left_item is None or right_item is None:
            diffs.append(
                {
                    "source_index": source_index,
                    "source_token": (
                        left_item["source_token"] if left_item else right_item["source_token"]
                    ),
                    "source_pos_tag": (
                        left_item["source_pos_tag"]
                        if left_item
                        else right_item["source_pos_tag"]
                    ),
                    "left": left_item,
                    "right": right_item,
                }
            )
            continue
        if (
            left_item["target_token"] != right_item["target_token"]
            or left_item["target_pos_tag"] != right_item["target_pos_tag"]
            or abs(left_item["score"] - right_item["score"]) >= 1e-6
        ):
            diffs.append(
                {
                    "source_index": source_index,
                    "source_token": left_item["source_token"],
                    "source_pos_tag": left_item["source_pos_tag"],
                    "left": left_item,
                    "right": right_item,
                }
            )
    return diffs


def build_payload(args, left_payload, right_payload):
    left_pairs = normalized_final_pairs(left_payload)
    right_pairs = normalized_final_pairs(right_payload)
    left_set = set(left_pairs)
    right_set = set(right_pairs)
    return {
        "request": left_payload["request"],
        "left": {
            "label": args.left_label,
            "model": (
                args.left_model
                if args.left_backend == "awesome"
                else args.left_simalign_model
            ),
            "backend": args.left_backend,
            "runtime": left_payload["runtime"],
            "final_pairs": left_pairs,
        },
        "right": {
            "label": args.right_label,
            "model": (
                args.right_model
                if args.right_backend == "awesome"
                else args.right_simalign_model
            ),
            "backend": args.right_backend,
            "runtime": right_payload["runtime"],
            "final_pairs": right_pairs,
        },
        "only_left_pairs": sorted(left_set - right_set),
        "only_right_pairs": sorted(right_set - left_set),
        "candidate_differences": compare_candidate_views(left_payload, right_payload),
    }


def format_pair_list(pairs):
    return ", ".join(f"{pos}:{src}->{tgt}" for pos, src, tgt in pairs) or "(none)"


def format_candidate_side(item):
    if item is None:
        return "(missing)"
    pos_text = item["target_pos_tag"] or "-"
    return f"{item['target_token']} [{pos_text}] {item['score']:.4f}"


def format_text(payload):
    lines = []
    request = payload["request"]
    lines.append("[request]")
    if request["name"]:
        lines.append(request["name"])
        if request.get("notes"):
            lines.append(f"note: {request['notes']}")
    lines.append(f"source: {request['source']}")
    lines.append(f"target: {request['target']}")
    lines.append("")

    for side_name in ("left", "right"):
        side = payload[side_name]
        lines.append(f"[{side['label']}]")
        lines.append(side["runtime"]["note"])
        lines.append(f"backend: {side['backend']}")
        lines.append(f"model: {side['model']}")
        lines.append(f"final pairs: {format_pair_list(side['final_pairs'])}")
        lines.append("")

    lines.append("[pair diff]")
    lines.append(f"only {payload['left']['label']}: {format_pair_list(payload['only_left_pairs'])}")
    lines.append(
        f"only {payload['right']['label']}: {format_pair_list(payload['only_right_pairs'])}"
    )
    lines.append("")

    lines.append("[top candidate diff]")
    if not payload["candidate_differences"]:
        lines.append("(none)")
    for item in payload["candidate_differences"]:
        lines.append(
            f"{item['source_index']}: {item['source_token']} [{item['source_pos_tag']}]"
        )
        lines.append(
            f"  {payload['left']['label']}: {format_candidate_side(item['left'])}"
        )
        lines.append(
            f"  {payload['right']['label']}: {format_candidate_side(item['right'])}"
        )
    return "\n".join(lines)


def format_json(payload):
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)


def main(argv=None):
    argv = sys.argv if argv is None else argv
    args = parse_args(argv)
    command = build_inspect_command(args)
    left_payload = run_inspection(
        command,
        args.left_model,
        backend=args.left_backend,
        simalign_method=args.left_simalign_method,
        simalign_model=args.left_simalign_model,
    )
    right_payload = run_inspection(
        command,
        args.right_model,
        backend=args.right_backend,
        simalign_method=args.right_simalign_method,
        simalign_model=args.right_simalign_model,
    )
    payload = build_payload(args, left_payload, right_payload)
    if args.format == "json":
        print(format_json(payload))
    else:
        print(format_text(payload))


if __name__ == "__main__":
    raise SystemExit(main())
