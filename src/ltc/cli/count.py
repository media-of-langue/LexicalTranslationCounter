"""Compatibility CLI for lexical translation counting."""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
import traceback

from ltc.errors import FatalRuntimeError
from ltc.io.corpus import CsvRowReader
from ltc.io.relations import write_final_relations, write_relations_snapshot
from ltc.pipeline.counting import (
    RelationState,
    RunProgress,
    build_corpus_output_row,
    load_resume_state,
    prepare_wordlists,
    process_corpus_batches,
)
from ltc.runtime import load_alignment_runtime, load_normalizer
from ltc.schema import CountCommandConfig
from ltc.timing import TIMER, timed


def get_positive_int_env(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer: {value!r}") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be positive: {value!r}")
    return parsed


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Count lexical translation relations for a bilingual corpus."
    )
    parser.add_argument("start_id", type=int)
    parser.add_argument("la1")
    parser.add_argument("la2")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Process at most this many rows from start_id.",
    )
    parser.add_argument(
        "--end-id",
        type=int,
        default=None,
        help="Stop before this row offset. Overrides LTC_END_ID.",
    )
    parser.add_argument(
        "--input-dir",
        default=os.environ.get("LTC_INPUT_DIR", "./data/input"),
        help="Directory containing corpus and wordlist CSV files.",
    )
    parser.add_argument(
        "--input-csv-path",
        default=os.environ.get("LTC_INPUT_CSV_PATH"),
        help="Corpus CSV path. Defaults to <input-dir>/corpus_{la1}_{la2}.csv.",
    )
    parser.add_argument(
        "--output-dir",
        default=os.environ.get("LTC_OUTPUT_DIR", "./data/output"),
        help="Directory where output CSV files are written.",
    )
    return parser.parse_args(argv[1:])


def resolve_end_id(start_id, max_rows, cli_end_id):
    end_id = cli_end_id
    if end_id is None:
        end_id_env = os.environ.get("LTC_END_ID")
        end_id = int(end_id_env) if end_id_env else None
    if max_rows is not None:
        if max_rows <= 0:
            raise ValueError(f"--max-rows must be positive: {max_rows!r}")
        max_rows_end = start_id + max_rows
        end_id = max_rows_end if end_id is None else min(end_id, max_rows_end)
    if end_id is not None and end_id <= start_id:
        raise ValueError(
            f"end_id ({end_id}) must be greater than start_id ({start_id})"
        )
    return end_id


def print_timing_summary(
    total_seconds, setup_seconds, processing_seconds, processed_rows
):
    per_sentence = processing_seconds / processed_rows if processed_rows else 0.0
    print("\nLTC timing summary")
    print("------------------")
    print(f"total time: {total_seconds:.3f} sec")
    print(f"model load/setup time: {setup_seconds:.3f} sec")
    print(f"processing time: {processing_seconds:.3f} sec")
    print(f"processing time per sentence: {per_sentence:.6f} sec")
    print(f"processed sentences: {processed_rows}")


def build_config(args):
    return CountCommandConfig(
        start_id=args.start_id,
        la1=args.la1,
        la2=args.la2,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        batch_size=get_positive_int_env("LTC_BATCH_SIZE", 10),
        checkpoint_interval_rows=get_positive_int_env(
            "LTC_CHECKPOINT_INTERVAL_ROWS", 1000
        ),
        input_csv_path=args.input_csv_path,
        end_id=resolve_end_id(args.start_id, args.max_rows, args.end_id),
        max_rows=args.max_rows,
        skip_resume=os.environ.get("LTC_NO_RESUME", "0").lower()
        in ("1", "true", "yes", "on"),
    )


def main(argv=None):
    argv = sys.argv if argv is None else argv
    run_start = time.perf_counter()
    csv.field_size_limit(sys.maxsize)
    args = parse_args(argv)
    config = build_config(args)

    TIMER.set_metadata("language_pair", config.language_pair)
    TIMER.set_metadata("start_id", config.start_id)
    TIMER.set_metadata("pid", os.getpid())
    TIMER.set_metadata("cwd", os.getcwd())
    TIMER.set_metadata("output_dir", config.output_dir)
    TIMER.set_metadata("input_dir", config.input_dir)
    TIMER.set_metadata("batch_size", config.batch_size)
    TIMER.set_metadata(
        "checkpoint_interval_rows", config.checkpoint_interval_rows
    )
    TIMER.set_metadata("end_id", config.end_id)
    TIMER.set_metadata("skip_resume", config.skip_resume)

    setup_start = time.perf_counter()
    with timed("startup.import_alignment"):
        alignment, alignment_batch = load_alignment_runtime(config.language_pair)

    with timed("startup.import_normalizers"):
        normalizer_la1 = load_normalizer(config.la1)
        normalizer_la2 = load_normalizer(config.la2)

    input_path = config.input_csv_path or os.path.join(
        config.input_dir, f"corpus_{config.language_pair}.csv"
    )
    TIMER.set_metadata("input_path", input_path)
    with timed("input.index_corpus"):
        input_reader = CsvRowReader(input_path)
    TIMER.set_metadata("input_rows", input_reader.num_rows)

    if not os.path.isdir(config.output_dir):
        os.makedirs(config.output_dir)

    with timed("wordlists.total"):
        wordlists = prepare_wordlists(
            config.input_dir,
            config.output_dir,
            config.la1,
            config.la2,
            normalizer_la1,
            normalizer_la2,
        )
    setup_seconds = time.perf_counter() - setup_start
    TIMER.record("setup.model_load_and_prepare", setup_seconds)

    relation_state = RelationState.empty()
    output_corpus_row_num = 0
    if config.resume_active:
        with timed("resume.load_previous_outputs"):
            relation_state, output_corpus_row_num = load_resume_state(
                config.output_dir, config.language_pair
            )

    output_mode = "a" if config.resume_active else "w"
    log_mode = "a" if config.resume_active else "w"
    with open(
        os.path.join(config.output_dir, f"corpus_{config.language_pair}.csv"), output_mode
    ) as output_file, open(
        os.path.join(config.output_dir, "passed_log.txt"), log_mode
    ) as passed_log_file:
        output_writer = csv.writer(output_file)

        def post_process_alignment(i, corpus_row, output_l):
            with timed("count.post_processing", metadata={"row_id": corpus_row[0]}):
                output_l = relation_state.apply_alignment_output(corpus_row, output_l)
                if output_corpus_row_num <= i:
                    output_writer.writerow(build_corpus_output_row(corpus_row, output_l))
            print("passed_id:", i)
            print(corpus_row[1], corpus_row[2])
            print(output_l)
            print("\n")

        def process_single(i, corpus_row):
            if len(corpus_row) != 5:
                return
            try:
                with timed("count.alignment_single", metadata={"row_id": i}):
                    output_l = alignment(corpus_row, wordlists)
            except FatalRuntimeError:
                raise
            except Exception:
                print(traceback.format_exc())
                passed_log_file.write(str(i))
                passed_log_file.write(str(corpus_row))
                output_l = []
            post_process_alignment(i, corpus_row, output_l)

        def process_batch(batch_start, corpus_rows):
            try:
                for corpus_row in corpus_rows:
                    if len(corpus_row) != 5:
                        raise Exception("corpus_row length is not 5")
                with timed(
                    "count.alignment_batch",
                    items=len(corpus_rows),
                    metadata={"start_id": batch_start, "rows": len(corpus_rows)},
                ):
                    output_ls = alignment_batch(corpus_rows, wordlists)

                assert len(output_ls) == len(corpus_rows)
            except FatalRuntimeError:
                raise
            except Exception:
                print(traceback.format_exc())
                passed_log_file.write(
                    f"batch ({batch_start} ~ {batch_start + len(corpus_rows)})\n"
                )
                raise

            for row_offset, corpus_row in enumerate(corpus_rows):
                post_process_alignment(
                    batch_start + row_offset,
                    corpus_row,
                    output_ls[row_offset],
                )

        def write_checkpoint(passed_id):
            with timed("checkpoint.write_totyu"):
                write_relations_snapshot(
                    config.output_dir, config.language_pair, relation_state.relations
                )
                with open(os.path.join(config.output_dir, "passed_id.txt"), "w") as f:
                    f.write(str(passed_id))

        progress = RunProgress()
        processing_start = time.perf_counter()
        processing_seconds = 0.0
        try:
            process_corpus_batches(
                input_reader,
                config.start_id,
                config.batch_size,
                config.checkpoint_interval_rows,
                process_batch,
                process_single,
                write_checkpoint,
                timed=timed,
                progress=progress,
                end_id=config.end_id,
            )
        except FatalRuntimeError:
            raise
        except Exception:
            print(traceback.format_exc())
        finally:
            processing_seconds = time.perf_counter() - processing_start
            TIMER.record(
                "processing.total",
                processing_seconds,
                items=progress.processed_rows,
            )
            with timed("output.write_final_relations"):
                write_final_relations(
                    config.output_dir,
                    config.language_pair,
                    relation_state.relations,
                )
            with timed("output.write_final_totyu"):
                write_relations_snapshot(
                    config.output_dir,
                    config.language_pair,
                    relation_state.relations,
                )
                if progress.last_processed_id is not None:
                    with open(os.path.join(config.output_dir, "passed_id.txt"), "w") as f:
                        f.write(str(progress.last_processed_id))
            TIMER.record("run.total", time.perf_counter() - run_start)
            TIMER.dump_json(
                os.path.join(config.output_dir, f"timing_{config.language_pair}.json")
            )
            total_seconds = time.perf_counter() - run_start
            print_timing_summary(
                total_seconds,
                setup_seconds,
                processing_seconds,
                progress.processed_rows,
            )


if __name__ == "__main__":
    raise SystemExit(main())
