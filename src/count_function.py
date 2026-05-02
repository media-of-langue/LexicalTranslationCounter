import argparse
import csv
import importlib
import os
import re
import sys
import traceback
import time

from timing_utils import TIMER, timed


# corpusを一行毎に読み出す
class CsvRowReader:
    def __init__(self, path):
        f = open(path, "r")
        self.file = f
        self.reader = csv.reader(f)
        self.offset_list = []
        while True:
            self.offset_list.append(f.tell())
            line = f.readline()
            if line == "":
                break
        self.offset_list.pop()  # remove offset at end of file
        self.num_rows = len(self.offset_list)

    def __del__(self):
        self.file.close()

    def read_row(self, idx):
        self.file.seek(self.offset_list[idx])
        return next(self.reader)


PART_OF_SPEACH_TAG_REV = {"n": "noun", "v": "verb", "a": "adj", "r": "adverb"}
PART_OF_SPEACH_TAG_CODE = {"noun": "n", "verb": "v", "adj": "a", "adverb": "r"}


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


def print_timing_summary(total_seconds, setup_seconds, processing_seconds, processed_rows):
    per_sentence = processing_seconds / processed_rows if processed_rows else 0.0
    print("\nLTC timing summary")
    print("------------------")
    print(f"total time: {total_seconds:.3f} sec")
    print(f"model load/setup time: {setup_seconds:.3f} sec")
    print(f"processing time: {processing_seconds:.3f} sec")
    print(f"processing time per sentence: {per_sentence:.6f} sec")
    print(f"processed sentences: {processed_rows}")


def read_corpus_batch(input_reader, start_idx, batch_size):
    corpus_rows = []
    for offset in range(batch_size):
        row_idx = start_idx + offset
        if row_idx < input_reader.num_rows:
            corpus_rows.append(input_reader.read_row(row_idx))
    return corpus_rows


def iter_corpus_batches(input_reader, start_id, batch_size, end_id=None):
    stop = input_reader.num_rows if end_id is None else min(end_id, input_reader.num_rows)
    for batch_start in range(start_id, stop, batch_size):
        this_batch = min(batch_size, stop - batch_start)
        corpus_rows = read_corpus_batch(input_reader, batch_start, this_batch)
        if corpus_rows:
            yield batch_start, corpus_rows


def should_write_checkpoint(batch_start, batch_len, checkpoint_interval_rows):
    if batch_len == 0:
        return False
    previous_checkpoint = batch_start // checkpoint_interval_rows
    current_checkpoint = (batch_start + batch_len) // checkpoint_interval_rows
    return current_checkpoint > previous_checkpoint


def write_relations_snapshot(output_dir, langs, relations):
    for pos_tag in PART_OF_SPEACH_TAG_REV.values():
        with open(
            os.path.join(output_dir, f"relations_{langs}_{pos_tag}_totyu.csv"),
            "w",
        ) as f:
            writer = csv.writer(f)
            for key, value in relations[pos_tag].items():
                [id_la1, id_la2] = key.split("_")
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


def write_final_relations(output_dir, langs, relations):
    for pos_tag, relation in relations.items():
        with open(os.path.join(output_dir, f"relations_{langs}_{pos_tag}.csv"), "w") as f:
            writer = csv.writer(f)
            for key, value in relation.items():
                [id_la1, id_la2] = key.split("_")
                writer.writerow(
                    [
                        value[0],
                        id_la1,
                        id_la2,
                        value[1],
                        "{" + str(value[2])[1:-1] + "}",
                        value[3],
                        value[4],
                    ]
                )


def process_corpus_batches(
    input_reader,
    start_id,
    batch_size,
    checkpoint_interval_rows,
    process_batch,
    process_single,
    write_checkpoint,
    progress=None,
    end_id=None,
):
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
            progress["last_processed_id"] = last_id
            progress["processed_rows"] = progress.get("processed_rows", 0) + len(
                corpus_rows
            )

        if should_write_checkpoint(
            batch_start, len(corpus_rows), checkpoint_interval_rows
        ):
            write_checkpoint(last_id)


def main():
    run_start = time.perf_counter()
    csv.field_size_limit(sys.maxsize)
    args = parse_args(sys.argv)
    start_id = args.start_id
    la1 = args.la1
    la2 = args.la2
    langs = la1 + "_" + la2

    TIMER.set_metadata("language_pair", langs)
    TIMER.set_metadata("start_id", start_id)
    TIMER.set_metadata("pid", os.getpid())
    TIMER.set_metadata("cwd", os.getcwd())
    output_dir = args.output_dir
    input_dir = args.input_dir
    batch_size = get_positive_int_env("LTC_BATCH_SIZE", 10)
    checkpoint_interval_rows = get_positive_int_env(
        "LTC_CHECKPOINT_INTERVAL_ROWS", 1000
    )
    end_id = resolve_end_id(start_id, args.max_rows, args.end_id)
    skip_resume = os.environ.get("LTC_NO_RESUME", "0").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    TIMER.set_metadata("output_dir", output_dir)
    TIMER.set_metadata("input_dir", input_dir)
    TIMER.set_metadata("batch_size", batch_size)
    TIMER.set_metadata("checkpoint_interval_rows", checkpoint_interval_rows)
    TIMER.set_metadata("end_id", end_id)
    TIMER.set_metadata("skip_resume", skip_resume)

    setup_start = time.perf_counter()
    with timed("startup.import_alignment"):
        _alignment_module = importlib.import_module(f"alignment.{langs}")
    alignment = _alignment_module.alignment
    alignment_batch = _alignment_module.alignment_batch

    with timed("startup.import_normalizers"):
        normalizer_la1 = getattr(
            importlib.import_module(f"normalizer.{la1}_normalizer"),
            f"{la1}_normalizer",
        )
        normalizer_la2 = getattr(
            importlib.import_module(f"normalizer.{la2}_normalizer"),
            f"{la2}_normalizer",
        )

    input_path = args.input_csv_path or os.path.join(input_dir, f"corpus_{langs}.csv")
    TIMER.set_metadata("input_path", input_path)
    with timed("input.index_corpus"):
        input_reader = CsvRowReader(input_path)
    TIMER.set_metadata("input_rows", input_reader.num_rows)

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    relations = {}  # {pos_tag:{id_la1}_{id_la2}:[id,count,example,convert_from,invalid]}
    relations_id = {}  # {pos_tag:id}
    wordlists = {}  # {pos_tag:{word:id}}
    output_corpus_row_num = 0
    with timed("wordlists.total"):
        for pos_tag in PART_OF_SPEACH_TAG_REV.values():
            relations[pos_tag] = {}
            relations_id[pos_tag] = 0
            with timed(f"wordlists.load.{la1}.{pos_tag}"):
                with open(
                    os.path.join(input_dir, f"wordlist_{la1}_{pos_tag}.csv"),
                    mode="r",
                ) as inp:
                    reader = list(csv.reader(inp))
                    if not re.fullmatch(r"[-+]?\d+", reader[0][0]):
                        reader = reader[1:]
                    wordlists[la1 + "_" + pos_tag] = {
                        rows[1]: int(rows[0]) for rows in reader
                    }
                    max_id_la1 = max(wordlists[la1 + "_" + pos_tag].values())
            with timed(f"wordlists.load.{la2}.{pos_tag}"):
                with open(
                    os.path.join(input_dir, f"wordlist_{la2}_{pos_tag}.csv"),
                    mode="r",
                ) as inp:
                    reader = list(csv.reader(inp))
                    if not re.fullmatch(r"[-+]?\d+", reader[0][0]):
                        reader = reader[1:]
                    wordlists[la2 + "_" + pos_tag] = {
                        rows[1]: int(rows[0]) for rows in reader
                    }
                    max_id_la2 = max(wordlists[la2 + "_" + pos_tag].values())
            flag_la1 = False
            flag_la2 = False
            wordlists_add = {}
            wordlists_add[la1 + "_" + pos_tag] = {}
            wordlists_add[la2 + "_" + pos_tag] = {}
            with timed(
                f"wordlists.normalize_missing.{la1}.{pos_tag}",
                items=len(wordlists[la1 + "_" + pos_tag]),
            ):
                for key, word_id in wordlists[la1 + "_" + pos_tag].items():
                    if (
                        normalizer_la1(
                            key, PART_OF_SPEACH_TAG_CODE[pos_tag], "", test=True
                        )
                        not in wordlists[la1 + "_" + pos_tag].keys()
                    ):
                        flag_la1 = True
                        max_id_la1 = max_id_la1 + 1
                        wordlists_add[la1 + "_" + pos_tag][
                            normalizer_la1(
                                key, PART_OF_SPEACH_TAG_CODE[pos_tag], "", test=True
                            )
                        ] = max_id_la1
            with timed(
                f"wordlists.normalize_missing.{la2}.{pos_tag}",
                items=len(wordlists[la2 + "_" + pos_tag]),
            ):
                for key, word_id in wordlists[la2 + "_" + pos_tag].items():
                    if (
                        normalizer_la2(
                            key, PART_OF_SPEACH_TAG_CODE[pos_tag], "", test=True
                        )
                        not in wordlists[la2 + "_" + pos_tag].keys()
                    ):
                        flag_la2 = True
                        max_id_la2 = max_id_la2 + 1
                        wordlists_add[la2 + "_" + pos_tag][
                            normalizer_la2(
                                key, PART_OF_SPEACH_TAG_CODE[pos_tag], "", test=True
                            )
                        ] = max_id_la2
            print("wordlist_add", wordlists_add)
            wordlists[la1 + "_" + pos_tag].update(wordlists_add[la1 + "_" + pos_tag])
            wordlists[la2 + "_" + pos_tag].update(wordlists_add[la2 + "_" + pos_tag])
            if flag_la1:
                with timed(f"wordlists.write_added.{la1}.{pos_tag}"):
                    with open(
                        os.path.join(output_dir, "wordlist_" + la1 + "_" + pos_tag + ".csv"),
                        "w",
                    ) as f:
                        writer = csv.writer(f)
                        for key, word_id in wordlists[la1 + "_" + pos_tag].items():
                            writer.writerow([word_id, key, "f"])
            if flag_la2:
                with timed(f"wordlists.write_added.{la2}.{pos_tag}"):
                    with open(
                        os.path.join(output_dir, "wordlist_" + la2 + "_" + pos_tag + ".csv"),
                        "w",
                    ) as f:
                        writer = csv.writer(f)
                        for key, word_id in wordlists[la2 + "_" + pos_tag].items():
                            writer.writerow([word_id, key, "f"])
    setup_seconds = time.perf_counter() - setup_start
    TIMER.record("setup.model_load_and_prepare", setup_seconds)

    # W (write-only, no resume): LTC_NO_RESUME=1 で start_id != 0 でも
    #   output_dir を新規扱いし、relations は空から開始、corpus/log も 'w' で上書き
    # A (append/resume): 従来通り start_id != 0 なら output_dir 内の前回 state を読む
    resume_active = (start_id != 0) and not skip_resume
    output_mode = "a" if resume_active else "w"
    log_mode = "a" if resume_active else "w"

    if resume_active:
        with timed("resume.load_previous_outputs"):
            for pos_tag in PART_OF_SPEACH_TAG_REV.values():
                relations[pos_tag] = {}
                max_id = 0
                with open(
                    os.path.join(
                        output_dir, "relations_" + langs + "_" + pos_tag + "_totyu.csv"
                    ),
                    mode="r",
                ) as inp:
                    reader = csv.reader(inp)
                    for rows in reader:
                        relations[pos_tag][rows[1] + "_" + rows[2]] = [
                            int(rows[0]),
                            int(rows[3]),
                            eval(rows[4]),
                            rows[5],
                            rows[6],
                        ]
                        if max_id < int(rows[0]):
                            max_id = int(rows[0])
                    relations_id[pos_tag] = max_id + 1
        with open(os.path.join(output_dir, f"corpus_{langs}.csv"), "r") as f:
            output_corpus_row_num = sum(1 for _ in f)

    with open(
        os.path.join(output_dir, f"corpus_{langs}.csv"), output_mode
    ) as output_file, open(
        os.path.join(output_dir, "passed_log.txt"), log_mode
    ) as passed_log_file:
        output_writer = csv.writer(output_file)

        def count_function_post_processing(
            i, corpus_row, relations, relations_id, output_corpus_row_num, output_l
        ):
            with timed("count.post_processing", metadata={"row_id": corpus_row[0]}):
                for index, command in enumerate(output_l):
                    pos_tag = PART_OF_SPEACH_TAG_REV[command[0]]
                    if command[1] + "_" + command[3] in relations[pos_tag]:
                        relations[pos_tag][command[1] + "_" + command[3]][1] += 1
                        relations[pos_tag][command[1] + "_" + command[3]][2].append(
                            corpus_row[0]
                        )
                        tmp_id = relations[pos_tag][command[1] + "_" + command[3]][0]
                    else:
                        tmp_id = relations_id[pos_tag]
                        relations[pos_tag][command[1] + "_" + command[3]] = [
                            tmp_id,
                            1,
                            [corpus_row[0]],
                            "unknown",
                            False,
                        ]
                        relations_id[pos_tag] += 1
                    output_l[index].insert(1, str(tmp_id))
                if output_corpus_row_num <= i:
                    output_writer.writerow(
                        [
                            corpus_row[0],
                            corpus_row[1].replace("\n", ""),
                            corpus_row[2].replace("\n", ""),
                            "{" + str(output_l)[1:-1].replace('"', "") + "}",
                            False,
                        ]
                    )
            print("passed_id:", i)
            print(corpus_row[1], corpus_row[2])
            print(output_l)
            print("\n")

        def count_function(
            i, corpus_row, relations, relations_id, wordlists, output_corpus_row_num
        ):
            if len(corpus_row) == 5:
                try:
                    with timed("count.alignment_single", metadata={"row_id": i}):
                        output_l = alignment(corpus_row, wordlists)
                except Exception as e:
                    print(traceback.format_exc())
                    passed_log_file.write(str(i))
                    passed_log_file.write(str(corpus_row))
                    output_l = []

                count_function_post_processing(
                    i,
                    corpus_row,
                    relations,
                    relations_id,
                    output_corpus_row_num,
                    output_l,
                )

        def count_function_batch(
            i_l,
            corpus_rows,
            relations,
            relations_id,
            wordlists,
            output_corpus_row_num,
        ):
            try:
                for corpus_row in corpus_rows:
                    if len(corpus_row) != 5:
                        raise Exception("corpus_row length is not 5")
                with timed(
                    "count.alignment_batch",
                    items=len(corpus_rows),
                    metadata={"start_id": i_l, "rows": len(corpus_rows)},
                ):
                    output_ls = alignment_batch(corpus_rows, wordlists)

                assert len(output_ls) == len(corpus_rows)

            except Exception as e:
                print(traceback.format_exc())
                passed_log_file.write(f"batch ({i_l} ~ {i_l + len(corpus_rows)})\n")
                raise e

            for i, corpus_row in enumerate(corpus_rows):
                count_function_post_processing(
                    i_l + i,
                    corpus_row,
                    relations,
                    relations_id,
                    output_corpus_row_num,
                    output_ls[i],
                )

        def process_batch(i_l, corpus_rows):
            count_function_batch(
                i_l,
                corpus_rows,
                relations,
                relations_id,
                wordlists,
                output_corpus_row_num,
            )

        def process_single(i, corpus_row):
            count_function(
                i,
                corpus_row,
                relations,
                relations_id,
                wordlists,
                output_corpus_row_num,
            )

        def write_checkpoint(passed_id):
            with timed("checkpoint.write_totyu"):
                write_relations_snapshot(output_dir, langs, relations)
                with open(os.path.join(output_dir, "passed_id.txt"), "w") as f:
                    f.write(str(passed_id))

        progress = {"last_processed_id": None, "processed_rows": 0}
        processing_start = time.perf_counter()
        processing_seconds = 0.0
        try:
            process_corpus_batches(
                input_reader,
                start_id,
                batch_size,
                checkpoint_interval_rows,
                process_batch,
                process_single,
                write_checkpoint,
                progress=progress,
                end_id=end_id,
            )
        except Exception as e:
            print(traceback.format_exc())
        finally:
            processing_seconds = time.perf_counter() - processing_start
            TIMER.record(
                "processing.total",
                processing_seconds,
                items=progress["processed_rows"],
            )
            with timed("output.write_final_relations"):
                write_final_relations(output_dir, langs, relations)
            with timed("output.write_final_totyu"):
                write_relations_snapshot(output_dir, langs, relations)
                if progress["last_processed_id"] is not None:
                    with open(
                        os.path.join(output_dir, "passed_id.txt"), "w"
                    ) as f:
                        f.write(str(progress["last_processed_id"]))
            TIMER.record("run.total", time.perf_counter() - run_start)
            TIMER.dump_json(os.path.join(output_dir, f"timing_{langs}.json"))
            total_seconds = time.perf_counter() - run_start
            print_timing_summary(
                total_seconds,
                setup_seconds,
                processing_seconds,
                progress["processed_rows"],
            )


if __name__ == "__main__":
    main()
