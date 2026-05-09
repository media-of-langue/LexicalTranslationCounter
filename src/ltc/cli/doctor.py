"""Diagnostic CLI for checking backend availability."""

from __future__ import annotations

import argparse
import json
import sys

from ltc.diagnostics import (
    MODULE_GROUPS,
    count_failures,
    count_successes,
    run_module_diagnostics,
)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Check LTC backend imports and report missing runtime dependencies."
    )
    parser.add_argument(
        "--group",
        action="append",
        choices=sorted(MODULE_GROUPS.keys()),
        help="Only check selected module group(s). Can be passed multiple times.",
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
        help="Exit with status 1 when any diagnostic check fails.",
    )
    return parser.parse_args(argv[1:])


def format_text(results):
    lines = []
    for group, group_results in results.items():
        lines.append(f"[{group}]")
        for result in group_results:
            if result.ok:
                line = f"OK  {result.name}"
                if result.note:
                    line += f" ({result.note})"
                lines.append(line)
            else:
                lines.append(
                    f"NG  {result.name}: {result.error_type}: {result.error_message}"
                )
        lines.append("")

    ok_count = count_successes(results)
    ng_count = count_failures(results)
    lines.append(f"summary: {ok_count} ok, {ng_count} failed")
    return "\n".join(lines)


def format_json(results):
    payload = {
        "summary": {
            "ok": count_successes(results),
            "failed": count_failures(results),
        },
        "groups": {
            group: [result.as_dict() for result in group_results]
            for group, group_results in results.items()
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def main(argv=None):
    argv = sys.argv if argv is None else argv
    args = parse_args(argv)
    groups = tuple(args.group) if args.group else None
    results = run_module_diagnostics(groups=groups)

    if args.format == "json":
        print(format_json(results))
    else:
        print(format_text(results))

    if args.fail_on_error and count_failures(results):
        raise SystemExit(1)


if __name__ == "__main__":
    raise SystemExit(main())
