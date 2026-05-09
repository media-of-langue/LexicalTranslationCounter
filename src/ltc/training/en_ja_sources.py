"""Source-specific converters for public en_ja corpora."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from itertools import zip_longest
from pathlib import Path
from typing import Iterable, Iterator

from ltc.text import normalize_english_text
from ltc.training.en_ja_data import normalize_sentence


ASPEC_SEPARATOR = " ||| "


@dataclass(frozen=True)
class ConvertedSourceSummary:
    source_name: str
    output_path: str
    rows_written: int

    def config_fragment(self):
        return {
            "name": self.source_name,
            "path": self.output_path,
            "format": "paired_tsv",
        }

    def as_dict(self):
        payload = asdict(self)
        payload["config_fragment"] = self.config_fragment()
        return payload


def ensure_parent_dir(path):
    Path(path).resolve().parent.mkdir(parents=True, exist_ok=True)


def normalize_pair(source_text, target_text, unicode_normalization="NFKC"):
    return (
        normalize_sentence(
            normalize_english_text(source_text),
            unicode_normalization=unicode_normalization,
        ),
        normalize_sentence(target_text, unicode_normalization=unicode_normalization),
    )


def write_pairs_as_tsv(output_path, pairs, unicode_normalization="NFKC"):
    output_path = Path(output_path).resolve()
    ensure_parent_dir(output_path)
    count = 0
    with output_path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        for source_text, target_text in pairs:
            source_text, target_text = normalize_pair(
                source_text,
                target_text,
                unicode_normalization=unicode_normalization,
            )
            if not source_text and not target_text:
                continue
            writer.writerow((source_text, target_text))
            count += 1
    return count


def build_summary(source_name, output_path, rows_written):
    return ConvertedSourceSummary(
        source_name=source_name,
        output_path=str(Path(output_path).resolve()),
        rows_written=rows_written,
    )


def iter_parallel_text_pairs(source_name, source_file, target_file):
    source_path = Path(source_file).resolve()
    target_path = Path(target_file).resolve()
    sentinel = object()
    with source_path.open() as source_handle, target_path.open() as target_handle:
        for line_number, pair in enumerate(
            zip_longest(source_handle, target_handle, fillvalue=sentinel),
            start=1,
        ):
            source_text, target_text = pair
            if source_text is sentinel or target_text is sentinel:
                raise RuntimeError(
                    f"{source_name} source/target files have different line counts near "
                    f"line {line_number}: {source_path} vs {target_path}"
                )
            source_text = source_text.rstrip("\n")
            target_text = target_text.rstrip("\n")
            if not source_text and not target_text:
                continue
            yield source_text, target_text


def convert_parallel_text_files(source_name, source_file, target_file, output_path):
    rows_written = write_pairs_as_tsv(
        output_path,
        iter_parallel_text_pairs(source_name, source_file, target_file),
    )
    return build_summary(source_name, output_path, rows_written)


def iter_paired_tsv_rows(
    input_path,
    source_column=0,
    target_column=1,
    delimiter="\t",
    skip_header=False,
):
    with Path(input_path).resolve().open(newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        for index, row in enumerate(reader):
            if skip_header and index == 0:
                continue
            if not row:
                continue
            if len(row) <= max(source_column, target_column):
                continue
            yield row[source_column], row[target_column]


def convert_paired_tsv(
    source_name,
    input_path,
    output_path,
    source_column=0,
    target_column=1,
    delimiter="\t",
    skip_header=False,
):
    rows_written = write_pairs_as_tsv(
        output_path,
        iter_paired_tsv_rows(
            input_path,
            source_column=source_column,
            target_column=target_column,
            delimiter=delimiter,
            skip_header=skip_header,
        ),
    )
    return build_summary(source_name, output_path, rows_written)


def infer_aspec_split_kind(file_name):
    lowered = file_name.lower()
    if lowered.startswith("train"):
        return "train"
    if lowered.startswith("dev") or lowered.startswith("test"):
        return "dev_or_test"
    raise ValueError(
        "ASPEC-JE file names should look like train1.txt, train-1.txt, dev.txt, "
        f"or test.txt (got {file_name!r})"
    )


def extract_aspec_pair(line, split_kind):
    fields = line.rstrip("\n").split(ASPEC_SEPARATOR)
    if split_kind == "train":
        if len(fields) < 5:
            raise RuntimeError(
                "ASPEC-JE train lines must have at least 5 fields separated by "
                f"{ASPEC_SEPARATOR!r}: {line[:120]!r}"
            )
        ja_text = fields[3]
        en_text = fields[4]
    else:
        if len(fields) < 4:
            raise RuntimeError(
                "ASPEC-JE dev/test lines must have at least 4 fields separated by "
                f"{ASPEC_SEPARATOR!r}: {line[:120]!r}"
            )
        ja_text = fields[2]
        en_text = fields[3]
    return en_text, ja_text


def iter_aspec_pairs(input_paths: Iterable[str]) -> Iterator[tuple[str, str]]:
    for input_path in input_paths:
        resolved = Path(input_path).resolve()
        split_kind = infer_aspec_split_kind(resolved.name)
        with resolved.open() as handle:
            for line in handle:
                if not line.strip():
                    continue
                yield extract_aspec_pair(line, split_kind)


def convert_aspec_je(input_paths, output_path):
    rows_written = write_pairs_as_tsv(output_path, iter_aspec_pairs(input_paths))
    return build_summary("aspec_je", output_path, rows_written)


def resolve_aspec_input_paths(input_paths=None, input_dir=None):
    if input_paths:
        return [str(Path(path).resolve()) for path in input_paths]
    if input_dir:
        input_dir = Path(input_dir).resolve()
        candidates = []
        for pattern in ("train*.txt", "dev*.txt", "test*.txt"):
            candidates.extend(sorted(str(path) for path in input_dir.glob(pattern)))
        if not candidates:
            raise RuntimeError(f"No ASPEC-JE files found under {input_dir}")
        return candidates
    raise RuntimeError("Provide either input_paths or input_dir for ASPEC-JE conversion.")
