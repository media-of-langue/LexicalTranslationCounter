"""Prepare en_ja fine-tuning data from public corpora."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ltc.training.en_ja_data import (
    load_training_config,
    prepare_training_examples,
    write_training_outputs,
)


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = (
    ROOT / "projects" / "training" / "en_ja" / "public_sources.example.json"
)
DEFAULT_OUTPUT_DIR = ROOT / "src" / "data" / "training" / "en_ja_public_mix"


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description=(
            "Prepare source-aware en_ja fine-tuning data and emit Awesome Align "
            "train/dev/test text files."
        )
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help="Path to the en_ja training-source JSON config.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where manifest and awesome_*.txt files will be written.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser.parse_args(argv[1:])


def format_text(payload):
    summary = payload["summary"]
    lines = [
        f"name: {summary['name']}",
        f"seed: {summary['seed']}",
        f"manifest: {payload['manifest_path']}",
        f"train: {payload['train_path']}",
        f"dev: {payload['dev_path']}",
        f"test: {payload['test_path']}",
        "",
        "[counts]",
        f"total: {summary['total_examples']}",
        f"train: {summary['split_counts']['train']}",
        f"dev: {summary['split_counts']['dev']}",
        f"test: {summary['split_counts']['test']}",
        "",
        "[drops]",
        f"empty: {summary['drop_stats']['empty']}",
        f"identical: {summary['drop_stats']['identical']}",
        f"length_filter: {summary['drop_stats']['length_filter']}",
        f"duplicate_pair: {summary['drop_stats']['duplicate_pair']}",
        "",
        "[sources]",
    ]
    for source_name in sorted(summary["source_stats"]):
        stats = summary["source_stats"][source_name]
        lines.append(f"{source_name}: raw={stats['raw']} kept={stats['kept']}")
    return "\n".join(lines)


def main(argv=None):
    argv = sys.argv if argv is None else argv
    args = parse_args(argv)
    config = load_training_config(args.config)
    prepared = prepare_training_examples(config)
    payload = write_training_outputs(args.output_dir, config, prepared)

    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(format_text(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
