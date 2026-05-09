"""Small tracked-corpus audit helpers for en_ja alignment work."""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from alignment.en_ja import alignment, runtime_metadata

from ltc.evaluation.en_ja_quality import observe_alignment_output


@dataclass(frozen=True)
class CorpusAuditRow:
    corpus_id: str
    source: str
    target: str


@dataclass(frozen=True)
class CorpusAuditResult:
    corpus_id: str
    source: str
    target: str
    actual_pairs: tuple

    def as_dict(self):
        return {
            "corpus_id": self.corpus_id,
            "source": self.source,
            "target": self.target,
            "actual_pairs": [asdict(item) for item in self.actual_pairs],
        }


def source_length_bucket(row):
    token_count = len(row.source.split())
    if token_count <= 8:
        return "short"
    if token_count <= 12:
        return "medium"
    if token_count <= 18:
        return "long"
    return "xlong"


def default_corpus_path():
    return Path(__file__).resolve().parents[3] / "src" / "test" / "data" / "corpus_en_ja.csv"


def load_corpus_rows(path=None):
    corpus_path = default_corpus_path() if path is None else Path(path)
    rows = []
    with corpus_path.open() as handle:
        reader = csv.reader(handle)
        for row in reader:
            rows.append(CorpusAuditRow(corpus_id=row[0], source=row[1], target=row[2]))
    return tuple(rows)


def sample_random_rows(rows, sample_size, seed):
    if sample_size is None or sample_size >= len(rows):
        return rows
    rng = random.Random(seed)
    sampled_indices = sorted(rng.sample(range(len(rows)), sample_size))
    return tuple(rows[index] for index in sampled_indices)


def sample_stratified_rows(rows, sample_size, seed):
    if sample_size is None or sample_size >= len(rows):
        return rows
    grouped_rows = defaultdict(list)
    for row in rows:
        grouped_rows[source_length_bucket(row)].append(row)
    active_groups = [
        list(grouped_rows[name])
        for name in ("short", "medium", "long", "xlong")
        if grouped_rows[name]
    ]
    if not active_groups:
        return ()
    rng = random.Random(seed)
    target = min(sample_size, len(rows))
    allocations = [0] * len(active_groups)
    if target >= len(active_groups):
        allocations = [1] * len(active_groups)
        remaining = target - len(active_groups)
    else:
        chosen_group_indices = rng.sample(range(len(active_groups)), target)
        for index in chosen_group_indices:
            allocations[index] = 1
        remaining = 0
    while remaining > 0:
        made_progress = False
        for index, group in enumerate(active_groups):
            if allocations[index] >= len(group):
                continue
            allocations[index] += 1
            remaining -= 1
            made_progress = True
            if remaining == 0:
                break
        if not made_progress:
            break
    sampled_rows = []
    for allocation, group in zip(allocations, active_groups):
        if allocation <= 0:
            continue
        sampled_rows.extend(rng.sample(group, allocation))
    selected_ids = {row.corpus_id for row in sampled_rows}
    return tuple(row for row in rows if row.corpus_id in selected_ids)


def select_corpus_rows(
    path=None,
    selected_ids=None,
    limit=None,
    selection="head",
    seed=13,
):
    rows = load_corpus_rows(path)
    if selected_ids:
        selected = {str(item) for item in selected_ids}
        rows = tuple(row for row in rows if row.corpus_id in selected)
    if limit is None:
        return rows
    if selection == "head":
        rows = rows[:limit]
    elif selection == "random":
        rows = sample_random_rows(rows, limit, seed)
    elif selection == "stratified":
        rows = sample_stratified_rows(rows, limit, seed)
    else:
        raise ValueError(f"Unsupported corpus audit selection: {selection}")
    return rows


def run_corpus_audit(path=None, selected_ids=None, limit=None, selection="head", seed=13):
    rows = select_corpus_rows(
        path=path,
        selected_ids=selected_ids,
        limit=limit,
        selection=selection,
        seed=seed,
    )
    results = []
    for row in rows:
        corpus_row = [row.corpus_id, row.source, row.target, "{null}", "False"]
        actual_pairs = tuple(
            item.normalized_pair()
            for item in observe_alignment_output(alignment(corpus_row, "", test=True))
        )
        results.append(
            CorpusAuditResult(
                corpus_id=row.corpus_id,
                source=row.source,
                target=row.target,
                actual_pairs=actual_pairs,
            )
        )
    return {
        "runtime": runtime_metadata(),
        "selection": {
            "strategy": selection,
            "seed": seed,
            "limit": limit,
            "row_ids": [row.corpus_id for row in rows],
        },
        "rows": tuple(results),
    }
