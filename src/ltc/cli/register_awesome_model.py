"""Register an Awesome Align production model under the repository registry."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from ltc.backends.alignment.awesome_utils import (
    MODEL_INFO_FILENAME,
    MODEL_SPEC_FILENAME,
    canonical_awesome_model_registry_dir_from_root,
    looks_like_explicit_local_path,
    missing_awesome_model_files,
    normalize_pair_name,
    read_registered_model_spec,
)


ROOT = Path(__file__).resolve().parents[3]


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description=(
            "Register an Awesome Align production model in the canonical "
            "repository model registry."
        )
    )
    parser.add_argument(
        "--pair",
        required=True,
        help="Language pair, for example en-ja or de-en.",
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Local model directory or Hugging Face model spec.",
    )
    parser.add_argument(
        "--copy-files",
        action="store_true",
        help=(
            "Copy a local model directory into the canonical registry instead "
            "of writing MODEL_SPEC."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace any existing registry contents for this pair.",
    )
    parser.add_argument(
        "--label",
        help="Short human-friendly label stored in MODEL_INFO.json.",
    )
    parser.add_argument(
        "--notes",
        help="Free-form notes stored in MODEL_INFO.json.",
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
    return parser.parse_args(argv[1:])


def registry_has_contents(registry_dir):
    return registry_dir.is_dir() and any(registry_dir.iterdir())


def reset_registry_dir(registry_dir, force):
    if registry_has_contents(registry_dir):
        if not force:
            raise RuntimeError(
                f"Registry directory already contains files: {registry_dir}. "
                "Re-run with --force to replace it."
            )
        shutil.rmtree(registry_dir)
    registry_dir.mkdir(parents=True, exist_ok=True)


def build_metadata(pair_name, source, registration_mode, label=None, notes=None):
    metadata = {
        "backend": "awesome-align",
        "pair": normalize_pair_name(pair_name, separator="-"),
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "registered_from": source,
        "registration_mode": registration_mode,
    }
    if label:
        metadata["label"] = label
    if notes:
        metadata["notes"] = notes
    return metadata


def write_metadata(registry_dir, metadata):
    metadata_path = Path(registry_dir) / MODEL_INFO_FILENAME
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")


def write_model_spec(registry_dir, model_spec):
    spec_path = Path(registry_dir) / MODEL_SPEC_FILENAME
    spec_path.write_text(model_spec.strip() + "\n")


def register_model(root, pair_name, source, copy_files=False, force=False, label=None, notes=None):
    root = Path(root).resolve()
    registry_dir = canonical_awesome_model_registry_dir_from_root(root, pair_name)
    source = source.strip()
    source_path = Path(source).expanduser()

    if copy_files and not source_path.is_dir():
        raise RuntimeError("--copy-files requires --source to be a local model directory.")

    if not source_path.exists() and looks_like_explicit_local_path(source):
        raise RuntimeError(f"Local model path does not exist: {source_path}")

    if source_path.exists() and not source_path.is_dir():
        raise RuntimeError(
            f"Awesome Align model source must be a directory: {source_path}"
        )

    reset_registry_dir(registry_dir, force=force)

    if source_path.is_dir():
        missing_files = missing_awesome_model_files(source_path)
        if missing_files:
            missing_names = ", ".join(path.name for path in missing_files)
            raise RuntimeError(
                f"Local Awesome Align directory is incomplete: {missing_names}"
            )
        if copy_files:
            shutil.rmtree(registry_dir)
            shutil.copytree(source_path, registry_dir)
            registration_mode = "copied_files"
            resolved_model_spec = str(registry_dir.resolve())
        else:
            write_model_spec(registry_dir, str(source_path.resolve()))
            registration_mode = "spec_reference"
            resolved_model_spec = str(source_path.resolve())
    else:
        if copy_files:
            raise RuntimeError("--copy-files cannot be used with a remote model spec.")
        write_model_spec(registry_dir, source)
        registration_mode = "model_name"
        resolved_model_spec = source

    metadata = build_metadata(
        pair_name,
        source=str(source_path.resolve()) if source_path.exists() else source,
        registration_mode=registration_mode,
        label=label,
        notes=notes,
    )
    write_metadata(registry_dir, metadata)

    registry_payload = read_registered_model_spec(registry_dir)
    if registry_payload is None:
        raise RuntimeError(
            f"Failed to register Awesome Align model under {registry_dir}"
        )

    return {
        "pair": normalize_pair_name(pair_name, separator="-"),
        "registry_dir": str(registry_dir.resolve()),
        "registration_mode": registration_mode,
        "model_spec": resolved_model_spec,
        "resolution_source": registry_payload["resolution_source"],
        "metadata": metadata,
    }


def format_text(payload):
    lines = [
        f"Registered Awesome Align model for {payload['pair']}",
        f"Registry dir: {payload['registry_dir']}",
        f"Mode: {payload['registration_mode']}",
        f"Resolved model spec: {payload['model_spec']}",
        f"Resolution source: {payload['resolution_source']}",
    ]
    label = payload["metadata"].get("label")
    if label:
        lines.append(f"Label: {label}")
    notes = payload["metadata"].get("notes")
    if notes:
        lines.append(f"Notes: {notes}")
    lines.append("")
    lines.append("Next steps:")
    lines.append(
        f"  PYTHONPATH=src python3 -m ltc.cli.awesome_model_status --pair {payload['pair']}"
    )
    return "\n".join(lines)


def main(argv=None):
    argv = sys.argv if argv is None else argv
    args = parse_args(argv)
    payload = register_model(
        args.root,
        args.pair,
        args.source,
        copy_files=args.copy_files,
        force=args.force,
        label=args.label,
        notes=args.notes,
    )
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(format_text(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
