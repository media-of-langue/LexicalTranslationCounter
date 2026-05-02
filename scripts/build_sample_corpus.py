#!/usr/bin/env python3
"""Build a small LTC input package from local corpus artifacts.

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
class PairConfig:
    language_pair: str
    langs: tuple[str, str]
    name: str
    source_corpus: Path
    wordlist_dirs: tuple[Path, ...]
    ltc_output_dir: Path
    relation_prefix: str
    relation_format: str
    out_dir: Path
    archive: Path
    license_profile: str
    source_note: str
    source_image_digest: str | None = None

    @property
    def pair_underscore(self) -> str:
        return "_".join(self.langs)


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


def normalize_pair(raw: str) -> str:
    return raw.strip().lower().replace("_", "-")


def pair_configs() -> dict[str, PairConfig]:
    root = media_root()
    return {
        "de-en": PairConfig(
            language_pair="de-en",
            langs=("de", "en"),
            name="ltc-sample-de-en-small",
            source_corpus=root / "de-en" / "corpus_de_en.csv.full",
            wordlist_dirs=(root / "de-en" / "input",),
            ltc_output_dir=root
            / "wisteria-jobs"
            / "ltc_de_en_merged_full_20260419_145201"
            / "data_output",
            relation_prefix="relations_de_en",
            relation_format="relations",
            out_dir=root / "de-en" / "samples" / "ltc-sample-de-en-small",
            archive=root / "de-en" / "samples" / "ltc-sample-de-en-small.tar.zst",
            license_profile="paracrawl",
            source_note="ParaCrawl-derived de-en corpus used by Media of Langue.",
        ),
        "en-ja": PairConfig(
            language_pair="en-ja",
            langs=("en", "ja"),
            name="ltc-sample-en-ja-small",
            source_corpus=root
            / "ltc-data"
            / "raw"
            / "en_ja_from_docker"
            / "input"
            / "corpus_en_ja.csv",
            wordlist_dirs=(
                root / "LexicalTranslationCounter" / "src" / "data" / "input",
                root / "ltc-data" / "raw" / "en_ja_from_docker" / "input",
            ),
            ltc_output_dir=root / "ltc-data" / "en_ja" / "20240115_default",
            relation_prefix="translations_en_ja",
            relation_format="translations",
            out_dir=root / "ltc-data" / "samples" / "ltc-sample-en-ja-small",
            archive=root
            / "ltc-data"
            / "samples"
            / "ltc-sample-en-ja-small.tar.zst",
            license_profile="jparacrawl",
            source_note=(
                "en-ja corpus copied from mediaoflangue/corpus_en_ja Docker data image."
            ),
            source_image_digest=(
                "mediaoflangue/corpus_en_ja@sha256:"
                "06fb3b85f2072042e1d49ebd113c515dfa4a42fc8424e512128a02f108eb1053"
            ),
        ),
    }


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


def parse_relation_row(
    row: list[str],
    relation_format: str,
) -> tuple[int, int, int, int, str] | None:
    if not row or not row[0].strip().lstrip("+-").isdigit():
        return None
    try:
        if relation_format == "relations":
            if len(row) < 7 or parse_bool(row[6]):
                return None
            return int(row[0]), int(row[1]), int(row[2]), int(row[3]), row[4]
        if relation_format == "translations":
            if len(row) < 5:
                return None
            return int(row[0]), int(row[1]), int(row[2]), int(row[3]), row[4]
    except ValueError:
        return None
    raise ValueError(f"unknown relation format: {relation_format}")


def select_edges(
    config: PairConfig,
    ltc_output_dir: Path,
    quotas: dict[str, int],
    min_count: int,
    max_count: int,
    ids_per_relation: int,
    seed: int,
) -> dict[str, list[EdgeSample]]:
    selected: dict[str, list[EdgeSample]] = {}
    for pos in POSES:
        rel_path = ltc_output_dir / f"{config.relation_prefix}_{pos}.csv"
        if not rel_path.exists():
            raise FileNotFoundError(f"relations file not found: {rel_path}")

        heap: list[tuple[int, int, EdgeSample]] = []
        with rel_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                parsed = parse_relation_row(row, config.relation_format)
                if parsed is None:
                    continue
                rid, id_la, id_lb, count, raw_corpus_ids = parsed
                if count < min_count or count > max_count:
                    continue
                priority = stable_int(seed, pos, rid, id_la, id_lb, count)
                edge_key = f"{pos}:{rid}:{id_la}:{id_lb}:{count}"
                corpus_ids = sample_example_ids(
                    raw_corpus_ids, ids_per_relation, seed=seed, edge_key=edge_key
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


def find_wordlist(wordlist_dirs: tuple[Path, ...], lang: str, pos: str) -> Path:
    name = f"wordlist_{lang}_{pos}.csv"
    for wordlist_dir in wordlist_dirs:
        candidate = wordlist_dir / name
        if candidate.exists():
            return candidate
    searched = ", ".join(str(path) for path in wordlist_dirs)
    raise FileNotFoundError(f"wordlist not found: {name}; searched {searched}")


def copy_wordlists(
    langs: tuple[str, str],
    wordlist_dirs: tuple[Path, ...],
    input_out_dir: Path,
) -> list[dict[str, str]]:
    copied: list[dict[str, str]] = []
    for lang in langs:
        for pos in POSES:
            src = find_wordlist(wordlist_dirs, lang, pos)
            dst = input_out_dir / src.name
            shutil.copy2(src, dst)
            copied.append({"file": src.name, "source": str(src)})
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
                if not row:
                    continue
                try:
                    row_id = int(row[0])
                except ValueError:
                    continue
                if row_id in corpus_ids:
                    writer.writerow(row)
                    written += 1
    return written


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_license(path: Path, config: PairConfig) -> None:
    if config.license_profile == "paracrawl":
        text = """# Data License Notes

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
"""
    elif config.license_profile == "jparacrawl":
        text = """# Data License Notes

This sample is derived from the en-ja corpus used by Media of Langue.
Project provenance note: the corpus is treated as JParaCrawl-based.

JParaCrawl is distributed by NTT Communication Science Laboratories. Its terms
allow use, replication, distribution, and modification for research purposes.
Commercial use is excluded from that grant and requires separate contact with
NTT. This data package is separate from the LexicalTranslationCounter software
license.

References:
- https://www.kecl.ntt.co.jp/icl/lirg/jparacrawl/
"""
    else:
        raise ValueError(f"unknown license profile: {config.license_profile}")
    path.write_text(text, encoding="utf-8")


def write_readme(path: Path, config: PairConfig, package_name: str) -> None:
    la1, la2 = config.langs
    path.write_text(
        f"""# {package_name}

Small {config.language_pair} sample input package for LexicalTranslationCounter.

To try it from a repository checkout:

```sh
tar -xf {package_name}.tar.zst
cd LexicalTranslationCounter/src
python3 count_function.py 0 {la1} {la2} --input-dir ../../{package_name}/src/data/input --max-rows 1000
```

The package contains raw LTC input files only. Existing full LTC relations were
used to choose rows that should produce a useful small graph.
""",
        encoding="utf-8",
    )


def write_manifest(
    path: Path,
    args: argparse.Namespace,
    config: PairConfig,
    selected: dict[str, list[EdgeSample]],
    corpus_rows: int,
    corpus_counts: Counter[int],
    wordlists: list[dict[str, str]],
    elapsed_seconds: float,
) -> None:
    manifest = {
        "name": args.name,
        "language_pair": config.pair_underscore,
        "created_by": "scripts/build_sample_corpus.py",
        "created_at_unix": int(time.time()),
        "source_corpus": str(args.source_corpus),
        "source_ltc_output_dir": str(args.ltc_output_dir),
        "source_note": config.source_note,
        "source_image_digest": config.source_image_digest,
        "source_wordlist_dirs": [str(path) for path in args.wordlist_dirs],
        "relation_prefix": config.relation_prefix,
        "relation_format": config.relation_format,
        "license_profile": config.license_profile,
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--language-pair",
        default="de-en",
        choices=sorted(pair_configs()),
        help="Language pair to package.",
    )
    parser.add_argument("--name", default=None)
    parser.add_argument("--source-corpus", type=Path, default=None)
    parser.add_argument(
        "--wordlist-dir",
        type=Path,
        action="append",
        default=None,
        help="Directory containing wordlist_{lang}_{pos}.csv. Can be repeated.",
    )
    parser.add_argument("--ltc-output-dir", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--archive", type=Path, default=None)
    parser.add_argument("--rows-target", type=int, default=100000)
    parser.add_argument("--ids-per-relation", type=int, default=25)
    parser.add_argument("--min-count", type=int, default=20)
    parser.add_argument("--max-count", type=int, default=5000)
    parser.add_argument("--quotas", default="default")
    parser.add_argument("--seed", type=int, default=20260502)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-archive", action="store_true")
    args = parser.parse_args()

    config = pair_configs()[normalize_pair(args.language_pair)]
    args.language_pair = config.language_pair
    args.name = args.name or config.name
    args.source_corpus = (args.source_corpus or config.source_corpus).resolve()
    wordlist_dirs = args.wordlist_dir or list(config.wordlist_dirs)
    args.wordlist_dirs = tuple(path.resolve() for path in wordlist_dirs)
    args.ltc_output_dir = (args.ltc_output_dir or config.ltc_output_dir).resolve()
    args.out_dir = (args.out_dir or config.out_dir).resolve()
    args.archive = (args.archive or config.archive).resolve()
    args.config = config
    return args


def main() -> None:
    csv.field_size_limit(sys.maxsize)
    args = parse_args()
    config: PairConfig = args.config
    start = time.perf_counter()

    if args.out_dir.exists():
        if not args.force:
            raise FileExistsError(f"output directory exists: {args.out_dir}")
        shutil.rmtree(args.out_dir)

    input_out_dir = args.out_dir / "src" / "data" / "input"
    input_out_dir.mkdir(parents=True)

    quotas = parse_quotas(args.quotas)
    selected = select_edges(
        config,
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
        input_out_dir / f"corpus_{config.pair_underscore}.csv",
        corpus_ids,
    )
    wordlists = copy_wordlists(config.langs, args.wordlist_dirs, input_out_dir)

    write_license(args.out_dir / "LICENSE-DATA.md", config)
    write_readme(args.out_dir / "README.md", config, args.name)
    elapsed = time.perf_counter() - start
    write_manifest(
        args.out_dir / "MANIFEST.json",
        args,
        config,
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
