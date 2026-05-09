"""Read and write relation state for the legacy CSV format."""

import ast
import csv
import os
import re

from ltc.constants import CONTENT_POS_NAMES


ID_RE = re.compile(r"-?\d+")


def parse_example_ids(raw):
    raw = (raw or "").strip()
    if not raw:
        return []

    try:
        parsed = ast.literal_eval(raw)
    except (SyntaxError, ValueError):
        return ID_RE.findall(raw)

    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    if isinstance(parsed, tuple):
        return [str(item) for item in parsed]
    if isinstance(parsed, set):
        return sorted(str(item) for item in parsed)
    if parsed is None:
        return []
    return [str(parsed)]


def build_empty_relations():
    relations = {pos_name: {} for pos_name in CONTENT_POS_NAMES}
    relation_ids = {pos_name: 0 for pos_name in CONTENT_POS_NAMES}
    return relations, relation_ids


def load_relation_snapshot(path):
    relation = {}
    max_id = -1
    with open(path, mode="r") as inp:
        reader = csv.reader(inp)
        for rows in reader:
            if len(rows) < 7:
                continue
            relation[rows[1] + "_" + rows[2]] = [
                int(rows[0]),
                int(rows[3]),
                parse_example_ids(rows[4]),
                rows[5],
                rows[6],
            ]
            if max_id < int(rows[0]):
                max_id = int(rows[0])
    return relation, max_id + 1


def load_relations_snapshot_dir(output_dir, language_pair):
    relations, relation_ids = build_empty_relations()
    for pos_name in CONTENT_POS_NAMES:
        path = os.path.join(output_dir, f"relations_{language_pair}_{pos_name}_totyu.csv")
        relations[pos_name], relation_ids[pos_name] = load_relation_snapshot(path)
    return relations, relation_ids


def count_output_corpus_rows(path):
    with open(path, "r") as f:
        return sum(1 for _ in f)


def format_final_examples(example_ids):
    return "{" + str(example_ids)[1:-1] + "}"


def write_relations_snapshot(output_dir, language_pair, relations):
    for pos_name in CONTENT_POS_NAMES:
        path = os.path.join(output_dir, f"relations_{language_pair}_{pos_name}_totyu.csv")
        with open(path, "w") as f:
            writer = csv.writer(f)
            for key, value in relations[pos_name].items():
                id_la1, id_la2 = key.split("_")
                writer.writerow(
                    [
                        value[0],
                        id_la1,
                        id_la2,
                        value[1],
                        value[2],
                        value[3],
                        value[4],
                    ]
                )


def write_final_relations(output_dir, language_pair, relations):
    for pos_name, relation in relations.items():
        path = os.path.join(output_dir, f"relations_{language_pair}_{pos_name}.csv")
        with open(path, "w") as f:
            writer = csv.writer(f)
            for key, value in relation.items():
                id_la1, id_la2 = key.split("_")
                writer.writerow(
                    [
                        value[0],
                        id_la1,
                        id_la2,
                        value[1],
                        format_final_examples(value[2]),
                        value[3],
                        value[4],
                    ]
                )
