#!/usr/bin/env python3
"""Build a small de-en LTC input package from local corpus artifacts.

The package contains raw LTC input files so it can be extracted into a checkout
and used with count_function.py. Existing LTC output relations are used only to
choose corpus rows that should produce a non-trivial graph.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import json
import random
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


POSES = ("noun", "verb", "adj", "adverb")
DEFAULT_QUOTAS = {"noun": 2500, "verb": 1500, "adj": 750, "adverb": 250}
ID_RE = re.compile(r"\d+")


@dataclass(frozen=True)
class EdgeSample:
    pos: str
    rid: int
    id_la: int
    id_lb: int
    count: int
    corpus_ids: tuple[int, ...]
    priority: int


def media_root() -> Path:
    return Path(__file__).resolve().parents[2]


def parse_quotas(raw: str) -> dict[str, int]:
    if raw == "default":
        return dict(DEFAULT_QUOTAS)
    quotas: dict[str, int] = {}
    for part in raw.split(","):
        key, value = part.split("=", 1)
        key = key.strip()
        if key not in POSES:
            raise ValueError(f"unknown POS in quota: {key!r}")
        quotas[key] = int(value)
    for pos in POSES:
        quotas.setdefault(pos, 0)
    return quotas


def stable_int(*parts: object) -> int:
    raw = "|".join(str(p) for p in parts).encode("utf-8")
    return int.from_bytes(hashlib.blake2b(raw, digest_size=8).digest(), "big")


def parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def sample_example_ids(raw: str, cap: int, seed: int, edge_key: str) -> tuple[int, ...]:
    ids = sorted({int(match.group(0)) for match in ID_RE.finditer(raw)})
    if len(ids) > cap:
        rng = random.Random(stable_int(seed, edge_key))
        ids = sorted(rng.sample(ids, cap))
    return tuple(ids)


def maybe_keep_edge(
    heap: list[tuple[int, int, EdgeSample]],
    quota: int,
    edge: EdgeSample,
) -> None:
    if quota <= 0:
        return
    item = (-edge.priority, edge.rid, edge)
    if len(heap) < quota:
        heapq.heappush(heap, item)
    elif item > heap[0]:
        heapq.heapreplace(heap, item)


def select_edges(
    ltc_output_dir: Path,
    quotas: dict[str, int],
    min_count: int,
    max_count: int,
    ids_per_relation: int,
    seed: int,
) -> dict[str, list[EdgeSample]]:
    selected: dict[str, list[EdgeSample]] = {}
    for pos in POSES:
        rel_path = ltc_output_dir / f"relations_de_en_{pos}.csv"
        if not rel_path.exists():
            raise FileNotFoundError(f"relations file not found: {rel_path}")

        heap: list[tuple[int, int, EdgeSample]] = []
        with rel_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 7:
                    continue
                count = int(row[3])
                if count < min_count or count > max_count:
                    continue
                if parse_bool(row[6]):
                    continue
                rid = int(row[0])
                id_la = int(row[1])
                id_lb = int(row[2])
                priority = stable_int(seed, pos, rid, id_la, id_lb, count)
                edge_key = f"{pos}:{rid}:{id_la}:{id_lb}:{count}"
                corpus_ids = sample_example_ids(
                    row[4], ids_per_relation, seed=seed, edge_key=edge_key
                )
                if not corpus_ids:
                    continue
                maybe_keep_edge(
                    heap,
                    quotas[pos],
                    EdgeSample(
                        pos=pos,
                        rid=rid,
                        id_la=id_la,
                        id_lb=id_lb,
                        count=count,
                        corpus_ids=corpus_ids,
                        priority=priority,
                    ),
                )
        selected[pos] = [item[2] for item in sorted(heap, reverse=True)]
    return selected


def choose_corpus_ids(
    selected: dict[str, list[EdgeSample]],
    rows_target: int,
    seed: int,
) -> tuple[set[int], Counter[int]]:
    edge_first_ids: set[int] = set()
    counts: Counter[int] = Counter()
    for edges in selected.values():
        for edge in edges:
            edge_first_ids.add(edge.corpus_ids[0])
            counts.update(edge.corpus_ids)

    if len(counts) <= rows_target:
        return set(counts), counts

    remaining_slots = max(0, rows_target - len(edge_first_ids))
    optional_ids = [cid for cid in counts if cid not in edge_first_ids]
    optional_ids.sort(
        key=lambda cid: (-counts[cid], stable_int(seed, "corpus-row", cid))
    )
    chosen = set(edge_first_ids)
    chosen.update(optional_ids[:remaining_slots])
    return chosen, counts


def copy_wordlists(wordlist_dir: Path, input_out_dir: Path) -> list[str]:
    copied: list[str] = []
    for lang in ("de", "en"):
        for pos in POSES:
            src = wordlist_dir / f"wordlist_{lang}_{pos}.csv"
            if not src.exists():
                raise FileNotFoundError(f"wordlist not found: {src}")
            dst = input_out_dir / src.name
            shutil.copy2(src, dst)
            copied.append(src.name)
    return copied


def write_sample_corpus(
    source_corpus: Path,
    out_path: Path,
    corpus_ids: set[int],
) -> int:
    written = 0
    with source_corpus.open("r", encoding="utf-8", errors="replace", newline="") as src:
        reader = csv.reader(src)
        with out_path.open("w", encoding="utf-8", newline="") as dst:
            writer = csv.writer(dst)
            for row in reader:
                if row and int(row[0]) in corpus_ids:
                    writer.writerow(row)
                    written += 1
    return written


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_license(path: Path) -> None:
    path.write_text(
        """# Data License Notes

This sample is derived from the de-en corpus used by Media of Langue.
Project provenance note: the corpus is treated as ParaCrawl-only, not a mixture
of multiple corpora.

ParaCrawl distributes the packaging of its parallel data under Creative Commons
CC0. ParaCrawl does not own the original source texts from which the corpus was
extracted and maintains a notice-and-takedown policy.

References:
- https://www.paracrawl.eu/
- https://opus.nlpl.eu/legacy/ParaCrawl.php
- https://creativecommons.org/publicdomain/zero/1.0/
""",
        encoding="utf-8",
    )


def write_readme(path: Path, package_name: str) -> None:
    path.write_text(
        f"""# {package_name}

Small de-en sample input package for LexicalTranslationCounter.

To try it from a repository checkout:

```sh
tar -xf {package_name}.tar.zst
cd LexicalTranslationCounter/src
python3 count_function.py 0 de en --input-dir ../../{package_name}/src/data/input --max-rows 1000
```

The package contains raw LTC input files only. Existing full LTC relations were
used to choose rows that should produce a useful small graph.
""",
        encoding="utf-8",
    )


def write_manifest(
    path: Path,
    args: argparse.Namespace,
    selected: dict[str, list[EdgeSample]],
    corpus_rows: int,
    corpus_counts: Counter[int],
    wordlists: list[str],
    elapsed_seconds: float,
) -> None:
    manifest = {
        "name": args.name,
        "language_pair": "de_en",
        "created_by": "scripts/build_sample_corpus.py",
        "created_at_unix": int(time.time()),
        "source_corpus": str(args.source_corpus),
        "source_ltc_output_dir": str(args.ltc_output_dir),
        "source_wordlist_dir": str(args.wordlist_dir),
        "license_assumption": "ParaCrawl-only corpus packaging under CC0",
        "rows_target": args.rows_target,
        "corpus_rows": corpus_rows,
        "unique_candidate_corpus_ids": len(corpus_counts),
        "ids_per_relation": args.ids_per_relation,
        "min_count": args.min_count,
        "max_count": args.max_count,
        "seed": args.seed,
        "selected_edges": {
            pos: {
                "count": len(edges),
                "count_min": min((edge.count for edge in edges), default=0),
                "count_max": max((edge.count for edge in edges), default=0),
            }
            for pos, edges in selected.items()
        },
        "wordlists": wordlists,
        "build_elapsed_seconds": elapsed_seconds,
    }
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def create_archive(package_dir: Path, archive_path: Path) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    tar = subprocess.Popen(
        ["tar", "-cf", "-", "-C", str(package_dir.parent), package_dir.name],
        stdout=subprocess.PIPE,
    )
    try:
        subprocess.run(
            ["zstd", "-1", "-T0", "-q", "-o", str(archive_path)],
            stdin=tar.stdout,
            check=True,
        )
    finally:
        if tar.stdout is not None:
            tar.stdout.close()
    tar.wait()
    if tar.returncode != 0:
        raise RuntimeError(f"tar failed with exit code {tar.returncode}")


def parse_args() -> argparse.Namespace:
    root = media_root()
    default_output = root / "de-en" / "samples" / "ltc-sample-de-en-small"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="ltc-sample-de-en-small")
    parser.add_argument(
        "--source-corpus",
        type=Path,
        default=root / "de-en" / "corpus_de_en.csv.full",
    )
    parser.add_argument(
        "--wordlist-dir",
        type=Path,
        default=root / "de-en" / "input",
    )
    parser.add_argument(
        "--ltc-output-dir",
        type=Path,
        default=root
        / "wisteria-jobs"
        / "ltc_de_en_merged_full_20260419_145201"
        / "data_output",
    )
    parser.add_argument("--out-dir", type=Path, default=default_output)
    parser.add_argument(
        "--archive",
        type=Path,
        default=root / "de-en" / "samples" / "ltc-sample-de-en-small.tar.zst",
    )
    parser.add_argument("--rows-target", type=int, default=100000)
    parser.add_argument("--ids-per-relation", type=int, default=25)
    parser.add_argument("--min-count", type=int, default=20)
    parser.add_argument("--max-count", type=int, default=5000)
    parser.add_argument("--quotas", default="default")
    parser.add_argument("--seed", type=int, default=20260502)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-archive", action="store_true")
    return parser.parse_args()


def main() -> None:
    csv.field_size_limit(sys.maxsize)
    args = parse_args()
    start = time.perf_counter()
    args.source_corpus = args.source_corpus.resolve()
    args.wordlist_dir = args.wordlist_dir.resolve()
    args.ltc_output_dir = args.ltc_output_dir.resolve()
    args.out_dir = args.out_dir.resolve()
    args.archive = args.archive.resolve()

    if args.out_dir.exists():
        if not args.force:
            raise FileExistsError(f"output directory exists: {args.out_dir}")
        shutil.rmtree(args.out_dir)

    input_out_dir = args.out_dir / "src" / "data" / "input"
    input_out_dir.mkdir(parents=True)

    quotas = parse_quotas(args.quotas)
    selected = select_edges(
        args.ltc_output_dir,
        quotas=quotas,
        min_count=args.min_count,
        max_count=args.max_count,
        ids_per_relation=args.ids_per_relation,
        seed=args.seed,
    )
    corpus_ids, corpus_counts = choose_corpus_ids(selected, args.rows_target, args.seed)
    corpus_rows = write_sample_corpus(
        args.source_corpus,
        input_out_dir / "corpus_de_en.csv",
        corpus_ids,
    )
    wordlists = copy_wordlists(args.wordlist_dir, input_out_dir)

    write_license(args.out_dir / "LICENSE-DATA.md")
    write_readme(args.out_dir / "README.md", args.name)
    elapsed = time.perf_counter() - start
    write_manifest(
        args.out_dir / "MANIFEST.json",
        args,
        selected,
        corpus_rows,
        corpus_counts,
        wordlists,
        elapsed,
    )

    if not args.no_archive:
        if args.archive.exists():
            args.archive.unlink()
        create_archive(args.out_dir, args.archive)
        (args.archive.parent / f"{args.archive.name}.sha256").write_text(
            f"{file_sha256(args.archive)}  {args.archive.name}\n",
            encoding="utf-8",
        )

    print(f"package_dir={args.out_dir}")
    print(f"corpus_rows={corpus_rows}")
    print(f"archive={args.archive if not args.no_archive else '<disabled>'}")
    print(f"elapsed_seconds={time.perf_counter() - start:.3f}")


if __name__ == "__main__":
    main()
