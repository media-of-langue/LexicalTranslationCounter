"""Shared orchestration helpers for lexical translation counting."""

from __future__ import annotations

import os
from dataclasses import dataclass

from ltc.constants import CONTENT_POS_NAMES, POS_NAME_TO_TAG, POS_TAG_TO_NAME
from ltc.errors import FatalRuntimeError
from ltc.io.relations import (
    build_empty_relations,
    count_output_corpus_rows,
    load_relations_snapshot_dir,
)
from ltc.io.wordlists import read_wordlist, write_wordlist


@dataclass
class RunProgress:
    last_processed_id: int | None = None
    processed_rows: int = 0


@dataclass
class RelationState:
    relations: dict
    relation_ids: dict

    @classmethod
    def empty(cls):
        relations, relation_ids = build_empty_relations()
        return cls(relations=relations, relation_ids=relation_ids)

    @classmethod
    def from_snapshot_dir(cls, output_dir, language_pair):
        relations, relation_ids = load_relations_snapshot_dir(output_dir, language_pair)
        return cls(relations=relations, relation_ids=relation_ids)

    def apply_alignment_output(self, corpus_row, output_l):
        for index, command in enumerate(output_l):
            pos_name = POS_TAG_TO_NAME[command[0]]
            relation_key = command[1] + "_" + command[3]
            if relation_key in self.relations[pos_name]:
                self.relations[pos_name][relation_key][1] += 1
                self.relations[pos_name][relation_key][2].append(corpus_row[0])
                relation_id = self.relations[pos_name][relation_key][0]
            else:
                relation_id = self.relation_ids[pos_name]
                self.relations[pos_name][relation_key] = [
                    relation_id,
                    1,
                    [corpus_row[0]],
                    "unknown",
                    False,
                ]
                self.relation_ids[pos_name] += 1
            output_l[index].insert(1, str(relation_id))
        return output_l


def build_corpus_output_row(corpus_row, output_l):
    return [
        corpus_row[0],
        corpus_row[1].replace("\n", ""),
        corpus_row[2].replace("\n", ""),
        "{" + str(output_l)[1:-1].replace('"', "") + "}",
        False,
    ]


def expand_wordlist_with_normalized_forms(wordlist, pos_name, normalizer):
    max_id = max(wordlist.values())
    additions = {}
    pos_tag_code = POS_NAME_TO_TAG[pos_name]
    for key in wordlist:
        normalized = normalizer(key, pos_tag_code, "", test=True)
        if normalized not in wordlist.keys():
            max_id += 1
            additions[normalized] = max_id
    updated = dict(wordlist)
    updated.update(additions)
    return updated, bool(additions)


def prepare_wordlists(input_dir, output_dir, la1, la2, normalizer_la1, normalizer_la2):
    wordlists = {}
    for pos_name in CONTENT_POS_NAMES:
        wordlist_la1 = read_wordlist(
            os.path.join(input_dir, f"wordlist_{la1}_{pos_name}.csv")
        )
        wordlist_la2 = read_wordlist(
            os.path.join(input_dir, f"wordlist_{la2}_{pos_name}.csv")
        )
        wordlist_la1, flag_la1 = expand_wordlist_with_normalized_forms(
            wordlist_la1, pos_name, normalizer_la1
        )
        wordlist_la2, flag_la2 = expand_wordlist_with_normalized_forms(
            wordlist_la2, pos_name, normalizer_la2
        )

        key_la1 = f"{la1}_{pos_name}"
        key_la2 = f"{la2}_{pos_name}"
        wordlists[key_la1] = wordlist_la1
        wordlists[key_la2] = wordlist_la2

        if flag_la1:
            write_wordlist(os.path.join(output_dir, f"wordlist_{la1}_{pos_name}.csv"), wordlist_la1)
        if flag_la2:
            write_wordlist(os.path.join(output_dir, f"wordlist_{la2}_{pos_name}.csv"), wordlist_la2)
    return wordlists


def load_resume_state(output_dir, language_pair):
    relation_state = RelationState.from_snapshot_dir(output_dir, language_pair)
    output_corpus_path = os.path.join(output_dir, f"corpus_{language_pair}.csv")
    output_corpus_row_num = count_output_corpus_rows(output_corpus_path)
    return relation_state, output_corpus_row_num


def should_write_checkpoint(batch_start, batch_len, checkpoint_interval_rows):
    if batch_len == 0:
        return False
    previous_checkpoint = batch_start // checkpoint_interval_rows
    current_checkpoint = (batch_start + batch_len) // checkpoint_interval_rows
    return current_checkpoint > previous_checkpoint


def process_corpus_batches(
    input_reader,
    start_id,
    batch_size,
    checkpoint_interval_rows,
    process_batch,
    process_single,
    write_checkpoint,
    timed,
    progress=None,
    end_id=None,
):
    from ltc.io.corpus import iter_corpus_batches

    for batch_start, corpus_rows in iter_corpus_batches(
        input_reader, start_id, batch_size, end_id=end_id
    ):
        try:
            with timed(
                "loop.batch_total",
                items=len(corpus_rows),
                metadata={"start_id": batch_start, "rows": len(corpus_rows)},
            ):
                process_batch(batch_start, corpus_rows)
        except FatalRuntimeError:
            raise
        except Exception:
            with timed(
                "loop.fallback_single_rows",
                items=len(corpus_rows),
                metadata={"start_id": batch_start, "rows": len(corpus_rows)},
            ):
                for row_offset, corpus_row in enumerate(corpus_rows):
                    process_single(batch_start + row_offset, corpus_row)

        last_id = batch_start + len(corpus_rows) - 1
        if progress is not None:
            progress.last_processed_id = last_id
            progress.processed_rows += len(corpus_rows)

        if should_write_checkpoint(
            batch_start, len(corpus_rows), checkpoint_interval_rows
        ):
            write_checkpoint(last_id)
