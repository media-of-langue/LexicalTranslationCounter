"""Show Awesome Align model registry and resolution status for one pair."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ltc.backends.alignment.awesome_utils import (
    canonical_awesome_model_registry_dir_from_root,
    check_awesome_model_runtime,
    default_alignment_module_path,
    default_local_dir_name_for_pair,
    inspect_awesome_model_spec,
    normalize_pair_name,
    resolve_awesome_model_selection,
)


ROOT = Path(__file__).resolve().parents[3]


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description=(
            "Show the current Awesome Align model resolution state for one "
            "language pair."
        )
    )
    parser.add_argument(
        "--pair",
        required=True,
        help="Language pair, for example en-ja or de-en.",
    )
    parser.add_argument(
        "--local-dir-name",
        help="Legacy src/model directory name override for this pair.",
    )
    parser.add_argument(
        "--root",
        default=str(ROOT),
        help="Repository root. Defaults to the current repository.",
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
        help="Exit with status 1 if the runtime check fails.",
    )
    parser.add_argument(
        "--require-production",
        action="store_true",
        help="Exit with status 1 if the resolved selection is not production-ready.",
    )
    return parser.parse_args(argv[1:])


def resolve_local_dir_name(pair_name, explicit_local_dir_name=None):
    if explicit_local_dir_name:
        return explicit_local_dir_name
    local_dir_name = default_local_dir_name_for_pair(pair_name)
    if local_dir_name:
        return local_dir_name
    raise RuntimeError(
        f"No default legacy Awesome model directory is known for {pair_name!r}. "
        "Pass --local-dir-name explicitly."
    )


def runtime_check_payload(model_spec, pair_name):
    backend_name = f"alignment.{normalize_pair_name(pair_name, separator='_')}"
    try:
        check_awesome_model_runtime(model_spec, backend_name=backend_name)
    except Exception as exc:  # pragma: no cover - exercised in tests via helper
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
    return {"ok": True, "error_type": None, "error_message": None}


def build_status(root, pair_name, local_dir_name=None):
    root = Path(root).resolve()
    pair_underscore = normalize_pair_name(pair_name, separator="_")
    pair_hyphen = normalize_pair_name(pair_name, separator="-")
    local_dir_name = resolve_local_dir_name(pair_underscore, local_dir_name)
    registry_dir = canonical_awesome_model_registry_dir_from_root(root, pair_underscore)
    alignment_file = default_alignment_module_path(root, pair_underscore)
    selection = resolve_awesome_model_selection(
        alignment_file,
        local_dir_name,
        pair_name=pair_underscore,
    )
    model_inspection = inspect_awesome_model_spec(selection.model_spec)
    return {
        "pair": pair_hyphen,
        "legacy_local_dir_name": local_dir_name,
        "registry_dir": str(registry_dir.resolve()),
        "selection": {
            "model_spec": selection.model_spec,
            "resolution_source": selection.resolution_source,
            "profile": selection.profile,
            "production_ready": selection.production_ready,
            "fallback_model_name": selection.fallback_model_name,
            "registry_dir": selection.registry_dir,
            "metadata": selection.metadata,
            "note": selection.note,
        },
        "model_spec_inspection": model_inspection,
        "runtime_check": runtime_check_payload(selection.model_spec, pair_hyphen),
    }


def format_text(payload):
    selection = payload["selection"]
    inspection = payload["model_spec_inspection"]
    runtime_check = payload["runtime_check"]
    lines = [
        f"Pair: {payload['pair']}",
        f"Registry dir: {payload['registry_dir']}",
        f"Legacy local dir name: {payload['legacy_local_dir_name']}",
        f"Resolved model spec: {selection['model_spec']}",
        f"Resolution source: {selection['resolution_source']}",
        f"Profile: {selection['profile']}",
        f"Production ready: {selection['production_ready']}",
        f"Note: {selection['note']}",
        f"Model spec kind: {inspection['kind']}",
    ]
    if inspection["path"]:
        lines.append(f"Model path: {inspection['path']}")
    if inspection["missing_files"]:
        lines.append(
            "Missing model files: "
            + ", ".join(Path(path).name for path in inspection["missing_files"])
        )
    if inspection["kind"] == "model_name":
        lines.append(f"Cached locally: {inspection['cached_locally']}")
    if selection["metadata"]:
        lines.append("Metadata:")
        for key in sorted(selection["metadata"]):
            lines.append(f"  {key}: {selection['metadata'][key]}")
    lines.append(
        "Runtime check: OK"
        if runtime_check["ok"]
        else (
            f"Runtime check: NG ({runtime_check['error_type']}: "
            f"{runtime_check['error_message']})"
        )
    )
    return "\n".join(lines)


def main(argv=None):
    argv = sys.argv if argv is None else argv
    args = parse_args(argv)
    payload = build_status(
        args.root,
        args.pair,
        local_dir_name=args.local_dir_name,
    )
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(format_text(payload))

    if args.require_production and not payload["selection"]["production_ready"]:
        raise SystemExit(1)
    if args.fail_on_error and not payload["runtime_check"]["ok"]:
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
