"""Prepare source-aware en_ja fine-tuning data from public parallel corpora."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path


WHITESPACE_RE = re.compile(r"\s+")
PAIR_SEPARATOR = "\u241f"


@dataclass(frozen=True)
class SourceSpec:
    name: str
    path: str
    format: str = "paired_tsv"
    source_column: int = 0
    target_column: int = 1
    delimiter: str = "\t"
    skip_header: bool = False
    comment_prefix: str | None = None
    max_records: int | None = None
    jsonl_source_key: str = "source"
    jsonl_target_key: str = "target"


@dataclass(frozen=True)
class FilterConfig:
    min_source_chars: int = 1
    min_target_chars: int = 1
    max_source_chars: int | None = 400
    max_target_chars: int | None = 400
    max_length_ratio: float = 4.0
    unicode_normalization: str = "NFKC"


@dataclass(frozen=True)
class SplitConfig:
    train: float = 0.98
    dev: float = 0.01
    test: float = 0.01

    def validated(self):
        total = self.train + self.dev + self.test
        if not 0.999 <= total <= 1.001:
            raise ValueError(
                "Split ratios must sum to 1.0 "
                f"(got train={self.train}, dev={self.dev}, test={self.test})"
            )
        return self


@dataclass(frozen=True)
class TrainingConfig:
    name: str
    seed: str
    sources: tuple[SourceSpec, ...]
    filters: FilterConfig
    splits: SplitConfig


@dataclass(frozen=True)
class TrainingExample:
    source_name: str
    source_text: str
    target_text: str
    split: str
    fingerprint: str

    def as_manifest_row(self):
        return (
            self.source_name,
            self.split,
            self.fingerprint,
            self.source_text,
            self.target_text,
        )


def decode_delimiter(value):
    return value.encode("utf-8").decode("unicode_escape")


def load_training_config(path):
    config_path = Path(path).resolve()
    payload = json.loads(config_path.read_text())
    sources = []
    for item in payload["sources"]:
        item = dict(item)
        source_path = Path(item["path"])
        if not source_path.is_absolute():
            item["path"] = str((config_path.parent / source_path).resolve())
        if "delimiter" in item:
            item["delimiter"] = decode_delimiter(item["delimiter"])
        sources.append(SourceSpec(**item))
    return TrainingConfig(
        name=payload["name"],
        seed=payload.get("seed", payload["name"]),
        sources=tuple(sources),
        filters=FilterConfig(**payload.get("filters", {})),
        splits=SplitConfig(**payload.get("splits", {})).validated(),
    )


def normalize_sentence(text, unicode_normalization="NFKC"):
    normalized = unicodedata.normalize(unicode_normalization, text)
    return WHITESPACE_RE.sub(" ", normalized).strip()


def build_pair_fingerprint(source_text, target_text):
    digest = hashlib.sha256(
        f"{source_text}{PAIR_SEPARATOR}{target_text}".encode("utf-8")
    ).hexdigest()
    return digest


def hashed_split(source_text, target_text, splits, seed):
    digest = hashlib.sha256(
        f"{seed}{PAIR_SEPARATOR}{source_text}{PAIR_SEPARATOR}{target_text}".encode(
            "utf-8"
        )
    ).hexdigest()
    score = int(digest[:12], 16) / float(16**12)
    if score < splits.train:
        return "train"
    if score < splits.train + splits.dev:
        return "dev"
    return "test"


def passes_length_filters(source_text, target_text, filters):
    if len(source_text) < filters.min_source_chars:
        return False
    if len(target_text) < filters.min_target_chars:
        return False
    if filters.max_source_chars is not None and len(source_text) > filters.max_source_chars:
        return False
    if filters.max_target_chars is not None and len(target_text) > filters.max_target_chars:
        return False
    shorter = min(len(source_text), len(target_text))
    longer = max(len(source_text), len(target_text))
    if shorter == 0:
        return False
    return (longer / shorter) <= filters.max_length_ratio


def iter_source_pairs(spec):
    source_path = Path(spec.path)
    if spec.format == "paired_tsv":
        with source_path.open(newline="") as handle:
            reader = csv.reader(handle, delimiter=spec.delimiter)
            yielded = 0
            for index, row in enumerate(reader):
                if spec.skip_header and index == 0:
                    continue
                if not row:
                    continue
                if spec.comment_prefix and row[0].startswith(spec.comment_prefix):
                    continue
                if len(row) <= max(spec.source_column, spec.target_column):
                    continue
                yield row[spec.source_column], row[spec.target_column]
                yielded += 1
                if spec.max_records is not None and yielded >= spec.max_records:
                    break
        return

    if spec.format == "awesome_plaintext":
        with source_path.open() as handle:
            yielded = 0
            for line in handle:
                if spec.comment_prefix and line.startswith(spec.comment_prefix):
                    continue
                if "|||" not in line:
                    continue
                left, right = line.split("|||", 1)
                yield left.strip(), right.strip()
                yielded += 1
                if spec.max_records is not None and yielded >= spec.max_records:
                    break
        return

    if spec.format == "jsonl":
        with source_path.open() as handle:
            yielded = 0
            for line in handle:
                if not line.strip():
                    continue
                item = json.loads(line)
                yield item[spec.jsonl_source_key], item[spec.jsonl_target_key]
                yielded += 1
                if spec.max_records is not None and yielded >= spec.max_records:
                    break
        return

    raise ValueError(f"Unsupported source format: {spec.format}")


def prepare_training_examples(config):
    seen_pairs = set()
    kept_examples = []
    source_stats = {}
    drop_stats = {
        "empty": 0,
        "identical": 0,
        "length_filter": 0,
        "duplicate_pair": 0,
    }

    for spec in config.sources:
        source_stats[spec.name] = {"raw": 0, "kept": 0}
        for source_text_raw, target_text_raw in iter_source_pairs(spec):
            source_stats[spec.name]["raw"] += 1
            source_text = normalize_sentence(
                source_text_raw,
                unicode_normalization=config.filters.unicode_normalization,
            )
            target_text = normalize_sentence(
                target_text_raw,
                unicode_normalization=config.filters.unicode_normalization,
            )

            if not source_text or not target_text:
                drop_stats["empty"] += 1
                continue
            if source_text == target_text:
                drop_stats["identical"] += 1
                continue
            if not passes_length_filters(source_text, target_text, config.filters):
                drop_stats["length_filter"] += 1
                continue

            fingerprint = build_pair_fingerprint(source_text, target_text)
            if fingerprint in seen_pairs:
                drop_stats["duplicate_pair"] += 1
                continue
            seen_pairs.add(fingerprint)

            split = hashed_split(
                source_text,
                target_text,
                splits=config.splits,
                seed=config.seed,
            )
            kept_examples.append(
                TrainingExample(
                    source_name=spec.name,
                    source_text=source_text,
                    target_text=target_text,
                    split=split,
                    fingerprint=fingerprint,
                )
            )
            source_stats[spec.name]["kept"] += 1

    return {
        "examples": tuple(kept_examples),
        "source_stats": source_stats,
        "drop_stats": drop_stats,
    }


def summarize_examples(config, prepared):
    split_counts = {"train": 0, "dev": 0, "test": 0}
    for example in prepared["examples"]:
        split_counts[example.split] += 1
    return {
        "name": config.name,
        "seed": config.seed,
        "filters": asdict(config.filters),
        "splits": asdict(config.splits),
        "source_stats": prepared["source_stats"],
        "drop_stats": prepared["drop_stats"],
        "split_counts": split_counts,
        "total_examples": len(prepared["examples"]),
    }


def write_training_outputs(output_dir, config, prepared):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    manifest_path = output_path / "manifest.tsv"
    with manifest_path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(
            ("source_name", "split", "fingerprint", "source_text", "target_text")
        )
        for example in prepared["examples"]:
            writer.writerow(example.as_manifest_row())

    split_handles = {}
    try:
        for split in ("train", "dev", "test"):
            split_handles[split] = (output_path / f"awesome_{split}.txt").open("w")
        for example in prepared["examples"]:
            split_handles[example.split].write(
                f"{example.source_text} ||| {example.target_text}\n"
            )
    finally:
        for handle in split_handles.values():
            handle.close()

    summary = summarize_examples(config, prepared)
    (output_path / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    return {
        "manifest_path": str(manifest_path),
        "summary_path": str((output_path / "summary.json").resolve()),
        "train_path": str((output_path / "awesome_train.txt").resolve()),
        "dev_path": str((output_path / "awesome_dev.txt").resolve()),
        "test_path": str((output_path / "awesome_test.txt").resolve()),
        "summary": summary,
    }
