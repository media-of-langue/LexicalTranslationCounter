"""Merge multiple partial LTC run outputs into a single combined output.

Produces output bit-equivalent to a single end-to-end run, by streaming the
input corpus files in row_id order and assigning relation_ids on first
appearance.

Usage:
    python merge_runs.py \\
        --inputs <data_output_dir_1> <data_output_dir_2> [...] \\
        --output <merged_output_dir> \\
        --langs de_en
"""

import argparse
import csv
import re
import shutil
import sys
import time
from array import array
from pathlib import Path

import psutil


POS_TAGS = ["noun", "verb", "adj", "adverb"]
POS_CODE_TO_TAG = {"n": "noun", "v": "verb", "a": "adj", "r": "adverb"}

# The 4th corpus column is written by count_function.py as
#     "{" + str(output_l)[1:-1].replace('"', "") + "}"
# Each inner list has 6 fields:
#     [pos_code, rel_id, id_la1, word_la1, id_la2, word_la2]
# Fields 0/1/2/4 are always clean single-quoted strings (pos_code is a single
# letter in "nvar"; rel_id/id_la1/id_la2 are digit strings). Fields 3 and 5 are
# words that *may lose their surrounding quotes*: if a word contains "'",
# Python renders it with double quotes in str(), and the ''-removal then
# leaves it bare (e.g. ging's). The format is therefore not a valid Python
# literal and ast.literal_eval cannot be used.
#
# We parse by positional regex: capture the four clean fields plus the two
# raw word tokens, and reconstruct items by splicing new rel_ids in.
_ITEM_RE = re.compile(
    r"\['([nvar])',\s*"       # pos_code
    r"'(\d+)',\s*"            # rel_id
    r"'(\d+)',\s*"            # id_la1
    r"(.*?),\s*"              # word_la1 (raw; may be 'foo' or bare)
    r"'(\d+)',\s*"            # id_la2
    r"(.*?)"                  # word_la2 (raw)
    r"\]",
    re.DOTALL,
)


def parse_output_l(s):
    """Parse the 4th corpus column into a list of 6-tuples (raw strings).

    Returns: list of (pos_code, rel_id, id_la1, word_la1_raw, id_la2, word_la2_raw).
    The word fields are preserved verbatim (with or without surrounding quotes)
    so they round-trip losslessly through format_output_l.
    """
    s = s.strip()
    if not (s.startswith("{") and s.endswith("}")):
        raise ValueError(f"Unexpected output_l bracket format: {s[:100]!r}")
    inner = s[1:-1].strip()
    if not inner:
        return []
    matches = list(_ITEM_RE.finditer(inner))
    if not matches:
        raise ValueError(f"No items matched: {s[:200]!r}")
    # Coverage check: gaps between matches (and leading/trailing) must contain
    # only comma + whitespace. This is robust to '[' / ']' / ',' / apostrophes
    # appearing inside word fields.
    prev_end = 0
    for m in matches:
        gap = inner[prev_end : m.start()]
        if gap.strip(" ,\t\n"):
            raise ValueError(
                f"Unexpected content between items [{prev_end}:{m.start()}]: "
                f"{gap!r} in {s[:200]!r}"
            )
        prev_end = m.end()
    trailing = inner[prev_end:]
    if trailing.strip(" ,\t\n"):
        raise ValueError(f"Unexpected trailing content: {trailing!r} in {s[:200]!r}")
    return [m.groups() for m in matches]


def format_output_l(items):
    """Reconstruct the 4th corpus column from parsed items.

    items: list of 6-tuples (pos_code, rel_id, id_la1, w1_raw, id_la2, w2_raw).
    Word fields are inserted verbatim to preserve the lossy original formatting
    (bare tokens for words containing apostrophes, etc.).
    """
    if not items:
        return "{}"
    parts = [
        f"['{pos}', '{rid}', '{id1}', {w1}, '{id2}', {w2}]"
        for (pos, rid, id1, w1, id2, w2) in items
    ]
    return "{" + ", ".join(parts) + "}"


def format_examples_final(examples):
    """'{\\'id1\\', \\'id2\\', ...}' — matches write_final_relations in count_function.py."""
    return "{" + ", ".join(f"'{x}'" for x in examples) + "}"


def format_examples_totyu(examples):
    """'[\\'id1\\', \\'id2\\', ...]' — matches write_relations_snapshot in count_function.py."""
    return "[" + ", ".join(f"'{x}'" for x in examples) + "]"


def log_mem(label):
    rss_gb = psutil.Process().memory_info().rss / (1024**3)
    print(f"[mem] {label}: RSS = {rss_gb:.2f} GB", flush=True)


def verify_wordlists_identical(input_dirs, wordlist_names):
    for wname in wordlist_names:
        present = [d / wname for d in input_dirs if (d / wname).exists()]
        if len(present) < 2:
            continue
        ref = present[0].read_bytes()
        for other in present[1:]:
            if other.read_bytes() != ref:
                raise ValueError(
                    f"Wordlist mismatch across runs: {present[0]} vs {other}. "
                    "Refusing to merge — wordlist additions diverge."
                )
        print(f"[verify] {wname}: identical across {len(present)} run(s)", flush=True)


def merge(input_dirs, output_dir, langs, progress_every, write_totyu):
    corpus_name = f"corpus_{langs}.csv"
    for d in input_dirs:
        if not (d / corpus_name).exists():
            raise FileNotFoundError(f"Missing {corpus_name} in {d}")
    output_dir.mkdir(parents=True, exist_ok=False)

    wordlist_names = set()
    for d in input_dirs:
        for f in d.iterdir():
            if f.name.startswith("wordlist_") and f.suffix == ".csv":
                wordlist_names.add(f.name)
    verify_wordlists_identical(input_dirs, sorted(wordlist_names))

    csv.field_size_limit(sys.maxsize)

    relations = {pos: {} for pos in POS_TAGS}
    next_id = {pos: 0 for pos in POS_TAGS}

    output_corpus_path = output_dir / corpus_name
    total_rows = 0
    t_start = time.perf_counter()
    log_mem("start")

    with open(output_corpus_path, "w", newline="", buffering=1 << 20) as fout:
        writer = csv.writer(fout)
        for input_dir in input_dirs:
            corpus_path = input_dir / corpus_name
            print(f"[read] {corpus_path}", flush=True)
            first_row_id = None
            last_row_id = None
            rows_in_file = 0
            with open(corpus_path, "r", newline="") as fin:
                reader = csv.reader(fin)
                for row in reader:
                    if len(row) < 4:
                        raise ValueError(
                            f"Unexpected corpus row format in {corpus_path}: {row!r}"
                        )
                    row_id_str = row[0]
                    row_id = int(row_id_str)
                    if first_row_id is None:
                        first_row_id = row_id
                    last_row_id = row_id

                    parsed = parse_output_l(row[3])
                    new_items = []
                    for pos_code, _old_rid, id_la1, w1_raw, id_la2, w2_raw in parsed:
                        pos = POS_CODE_TO_TAG[pos_code]
                        key = (id_la1, id_la2)
                        rec = relations[pos].get(key)
                        if rec is not None:
                            rec[1] += 1
                            rec[2].append(row_id)
                            new_id = rec[0]
                        else:
                            new_id = next_id[pos]
                            next_id[pos] += 1
                            relations[pos][key] = [
                                new_id,
                                1,
                                array("l", [row_id]),
                                "unknown",
                                False,
                            ]
                        new_items.append(
                            (pos_code, str(new_id), id_la1, w1_raw, id_la2, w2_raw)
                        )

                    writer.writerow(
                        [
                            row_id_str,
                            row[1],
                            row[2],
                            format_output_l(new_items),
                            row[4] if len(row) > 4 else "False",
                        ]
                    )
                    total_rows += 1
                    rows_in_file += 1
                    if progress_every and total_rows % progress_every == 0:
                        elapsed = time.perf_counter() - t_start
                        rate = total_rows / elapsed if elapsed else 0.0
                        print(
                            f"[progress] total={total_rows:,} rows, "
                            f"elapsed={elapsed:.1f}s, rate={rate:.0f} rows/s, "
                            f"current_row_id={row_id}",
                            flush=True,
                        )
            print(
                f"[done-file] {corpus_path.name}: rows={rows_in_file:,} "
                f"(row_id {first_row_id}..{last_row_id})",
                flush=True,
            )
            log_mem(f"after {input_dir.name}")

    elapsed = time.perf_counter() - t_start
    print(
        f"[done-corpus] total_rows={total_rows:,} in {elapsed:.1f}s "
        f"({total_rows / elapsed:.0f} rows/s)",
        flush=True,
    )
    for pos in POS_TAGS:
        print(f"[stat] {pos}: {len(relations[pos]):,} unique relations", flush=True)

    for pos in POS_TAGS:
        out_final = output_dir / f"relations_{langs}_{pos}.csv"
        with open(out_final, "w", newline="", buffering=1 << 20) as f:
            w = csv.writer(f)
            for (id_la1, id_la2), value in relations[pos].items():
                rid, count, examples, cf, inv = value
                w.writerow(
                    [
                        rid,
                        id_la1,
                        id_la2,
                        count,
                        format_examples_final(examples),
                        cf,
                        inv,
                    ]
                )
        print(f"[write] {out_final.name}", flush=True)

        if write_totyu:
            out_totyu = output_dir / f"relations_{langs}_{pos}_totyu.csv"
            with open(out_totyu, "w", newline="", buffering=1 << 20) as f:
                w = csv.writer(f)
                for (id_la1, id_la2), value in relations[pos].items():
                    rid, count, examples, cf, inv = value
                    w.writerow(
                        [
                            rid,
                            id_la1,
                            id_la2,
                            count,
                            format_examples_totyu(examples),
                            cf,
                            inv,
                        ]
                    )
            print(f"[write] {out_totyu.name}", flush=True)

    for wname in sorted(wordlist_names):
        for d in input_dirs:
            src = d / wname
            if src.exists():
                shutil.copy(src, output_dir / wname)
                print(f"[copy] {wname} from {d.name}", flush=True)
                break

    last_passed = input_dirs[-1] / "passed_id.txt"
    if last_passed.exists():
        shutil.copy(last_passed, output_dir / "passed_id.txt")
        print(f"[copy] passed_id.txt from {input_dirs[-1].name}", flush=True)

    with open(output_dir / "passed_log.txt", "w") as f:
        for d in input_dirs:
            src = d / "passed_log.txt"
            if src.exists():
                content = src.read_text()
                if content:
                    f.write(f"# from {d.name}\n{content}")

    timings_dir = output_dir / "timings"
    timings_dir.mkdir()
    for d in input_dirs:
        src = d / f"timing_{langs}.json"
        if src.exists():
            # Use the parent (job) dir name, not d.name which is always
            # "data_output" and would collide across inputs.
            shutil.copy(src, timings_dir / f"{d.parent.name}.json")
    print(f"[copy] per-run timings -> {timings_dir}", flush=True)

    log_mem("end")
    print(f"[complete] output: {output_dir}", flush=True)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--inputs",
        nargs="+",
        required=True,
        help="data_output directories to merge, in row_id-ascending order",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="merged output directory (must not exist)",
    )
    parser.add_argument(
        "--langs",
        required=True,
        help="language pair (e.g., de_en)",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=100_000,
        help="log progress every N rows (0 disables)",
    )
    parser.add_argument(
        "--write-totyu",
        action="store_true",
        help="also write relations_*_totyu.csv (same content, [] instead of {})",
    )
    args = parser.parse_args()

    input_dirs = [Path(d).resolve() for d in args.inputs]
    output_dir = Path(args.output).resolve()

    for d in input_dirs:
        if not d.is_dir():
            raise FileNotFoundError(f"Not a directory: {d}")

    merge(
        input_dirs=input_dirs,
        output_dir=output_dir,
        langs=args.langs,
        progress_every=args.progress_every,
        write_totyu=args.write_totyu,
    )


if __name__ == "__main__":
    main()
