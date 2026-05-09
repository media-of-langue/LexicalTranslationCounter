"""Convert raw public en_ja corpus files into a canonical local TSV."""

from __future__ import annotations

import argparse
import json
import sys

from ltc.training.en_ja_sources import (
    convert_aspec_je,
    convert_paired_tsv,
    convert_parallel_text_files,
    resolve_aspec_input_paths,
)


def parse_args(argv):
    output_parent = argparse.ArgumentParser(add_help=False)
    output_parent.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    parser = argparse.ArgumentParser(
        description=(
            "Convert raw public en_ja corpus files into a canonical local TSV "
            "that can be referenced from the fine-tuning data-prep config."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parallel_parser = subparsers.add_parser(
        "parallel-files",
        parents=[output_parent],
        help="Convert two plain-text files with aligned line-by-line sentences.",
    )
    parallel_parser.add_argument(
        "--source-name",
        default="parallel_text",
        help="Logical source name used in downstream manifests.",
    )
    parallel_parser.add_argument(
        "--source-file",
        required=True,
        help="English text file, one sentence per line.",
    )
    parallel_parser.add_argument(
        "--target-file",
        required=True,
        help="Japanese text file, one sentence per line.",
    )
    parallel_parser.add_argument(
        "--output-path",
        required=True,
        help="Where to write the canonical TSV output.",
    )

    tsv_parser = subparsers.add_parser(
        "paired-tsv",
        parents=[output_parent],
        help="Convert a local paired TSV or CSV into the canonical local TSV.",
    )
    tsv_parser.add_argument(
        "--source-name",
        required=True,
        help="Logical source name used in downstream manifests.",
    )
    tsv_parser.add_argument(
        "--input-path",
        required=True,
        help="Input file containing both English and Japanese columns.",
    )
    tsv_parser.add_argument(
        "--output-path",
        required=True,
        help="Where to write the canonical TSV output.",
    )
    tsv_parser.add_argument(
        "--source-column",
        type=int,
        default=0,
        help="Zero-based column index for English text.",
    )
    tsv_parser.add_argument(
        "--target-column",
        type=int,
        default=1,
        help="Zero-based column index for Japanese text.",
    )
    tsv_parser.add_argument(
        "--delimiter",
        default="\\t",
        help="Delimiter for the input file. Use \\t for tab.",
    )
    tsv_parser.add_argument(
        "--skip-header",
        action="store_true",
        help="Skip the first row of the input file.",
    )

    aspec_parser = subparsers.add_parser(
        "aspec-je",
        parents=[output_parent],
        help="Convert raw ASPEC-JE train/dev/test files into the canonical TSV.",
    )
    aspec_parser.add_argument(
        "--input-dir",
        help="Directory containing ASPEC-JE train/dev/test .txt files.",
    )
    aspec_parser.add_argument(
        "--input-path",
        action="append",
        help="Explicit ASPEC-JE file path. Can be passed multiple times.",
    )
    aspec_parser.add_argument(
        "--output-path",
        required=True,
        help="Where to write the canonical TSV output.",
    )

    return parser.parse_args(argv[1:])


def decode_delimiter(value):
    return value.encode("utf-8").decode("unicode_escape")


def run_conversion(args):
    if args.command == "parallel-files":
        return convert_parallel_text_files(
            source_name=args.source_name,
            source_file=args.source_file,
            target_file=args.target_file,
            output_path=args.output_path,
        )

    if args.command == "paired-tsv":
        return convert_paired_tsv(
            source_name=args.source_name,
            input_path=args.input_path,
            output_path=args.output_path,
            source_column=args.source_column,
            target_column=args.target_column,
            delimiter=decode_delimiter(args.delimiter),
            skip_header=args.skip_header,
        )

    if args.command == "aspec-je":
        return convert_aspec_je(
            input_paths=resolve_aspec_input_paths(
                input_paths=args.input_path,
                input_dir=args.input_dir,
            ),
            output_path=args.output_path,
        )

    raise RuntimeError(f"Unsupported command: {args.command}")


def format_text(summary):
    config_json = json.dumps(
        summary.config_fragment(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    lines = [
        f"Converted source: {summary.source_name}",
        f"Rows written: {summary.rows_written}",
        f"Output TSV: {summary.output_path}",
        "",
        "Config fragment:",
        config_json,
        "",
        "Next step:",
        "  Add the fragment to your en_ja public-sources config and run:",
        "  PYTHONPATH=src python3 -m ltc.cli.prepare_en_ja_finetune_data "
        "--config /path/to/public_sources.json --output-dir /path/to/output",
    ]
    return "\n".join(lines)


def main(argv=None):
    argv = sys.argv if argv is None else argv
    args = parse_args(argv)
    summary = run_conversion(args)
    if args.format == "json":
        print(json.dumps(summary.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(format_text(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
