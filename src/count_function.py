import csv
import importlib
import os
import re
import sys
import traceback


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


def main():
    csv.field_size_limit(sys.maxsize)
    args = sys.argv
    start_id = int(args[1])
    la1 = args[2]
    la2 = args[3]
    langs = la1 + "_" + la2

    _alignment_module = importlib.import_module(f"alignment.{langs}")
    alignment = _alignment_module.alignment
    alignment_batch = _alignment_module.alignment_batch

    normalizer_la1 = getattr(
        importlib.import_module(f"normalizer.{la1}_normalizer"),
        f"{la1}_normalizer",
    )
    normalizer_la2 = getattr(
        importlib.import_module(f"normalizer.{la2}_normalizer"),
        f"{la2}_normalizer",
    )

    input_reader = CsvRowReader(f"./data/input/corpus_{langs}.csv")

    if not os.path.isdir("./data/output"):
        os.makedirs("./data/output")

    relations = {}  # {pos_tag:{id_la1}_{id_la2}:[id,count,example,convert_from,invalid]}
    relations_id = {}  # {pos_tag:id}
    wordlists = {}  # {pos_tag:{word:id}}
    output_corpus_row_num = 0
    for pos_tag in PART_OF_SPEACH_TAG_REV.values():
        relations[pos_tag] = {}
        relations_id[pos_tag] = 0
        with open(
            "./data/input/wordlist_" + la1 + "_" + pos_tag + ".csv", mode="r"
        ) as inp:
            reader = list(csv.reader(inp))
            if not re.fullmatch(r"[-+]?\d+", reader[0][0]):
                reader = reader[1:]
            wordlists[la1 + "_" + pos_tag] = {rows[1]: int(rows[0]) for rows in reader}
            max_id_la1 = max(wordlists[la1 + "_" + pos_tag].values())
        with open(
            "./data/input/wordlist_" + la2 + "_" + pos_tag + ".csv", mode="r"
        ) as inp:
            reader = list(csv.reader(inp))
            if not re.fullmatch(r"[-+]?\d+", reader[0][0]):
                reader = reader[1:]
            wordlists[la2 + "_" + pos_tag] = {rows[1]: int(rows[0]) for rows in reader}
            max_id_la2 = max(wordlists[la2 + "_" + pos_tag].values())
        flag_la1 = False
        flag_la2 = False
        wordlists_add = {}
        wordlists_add[la1 + "_" + pos_tag] = {}
        wordlists_add[la2 + "_" + pos_tag] = {}
        for key, word_id in wordlists[la1 + "_" + pos_tag].items():
            if (
                normalizer_la1(key, PART_OF_SPEACH_TAG_CODE[pos_tag], "", test=True)
                not in wordlists[la1 + "_" + pos_tag].keys()
            ):
                flag_la1 = True
                max_id_la1 = max_id_la1 + 1
                wordlists_add[la1 + "_" + pos_tag][
                    normalizer_la1(key, PART_OF_SPEACH_TAG_CODE[pos_tag], "", test=True)
                ] = max_id_la1
        for key, word_id in wordlists[la2 + "_" + pos_tag].items():
            if (
                normalizer_la2(key, PART_OF_SPEACH_TAG_CODE[pos_tag], "", test=True)
                not in wordlists[la2 + "_" + pos_tag].keys()
            ):
                flag_la2 = True
                max_id_la2 = max_id_la2 + 1
                wordlists_add[la2 + "_" + pos_tag][
                    normalizer_la2(key, PART_OF_SPEACH_TAG_CODE[pos_tag], "", test=True)
                ] = max_id_la2
        print("wordlist_add", wordlists_add)
        wordlists[la1 + "_" + pos_tag].update(wordlists_add[la1 + "_" + pos_tag])
        wordlists[la2 + "_" + pos_tag].update(wordlists_add[la2 + "_" + pos_tag])
        if flag_la1:
            with open(
                "./data/output/wordlist_" + la1 + "_" + pos_tag + ".csv", "w"
            ) as f:
                writer = csv.writer(f)
                for key, word_id in wordlists[la1 + "_" + pos_tag].items():
                    writer.writerow([word_id, key, "f"])
        if flag_la2:
            with open(
                "./data/output/wordlist_" + la2 + "_" + pos_tag + ".csv", "w"
            ) as f:
                writer = csv.writer(f)
                for key, word_id in wordlists[la2 + "_" + pos_tag].items():
                    writer.writerow([word_id, key, "f"])

    output_mode = "a" if start_id != 0 else "w"
    log_mode = "a" if start_id != 0 else "w"

    if start_id != 0:
        for pos_tag in PART_OF_SPEACH_TAG_REV.values():
            relations[pos_tag] = {}
            max_id = 0
            with open(
                "./data/output/relations_" + langs + "_" + pos_tag + "_totyu.csv",
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
        with open(f"./data/output/corpus_{langs}.csv", "r") as f:
            output_corpus_row_num = sum(1 for _ in f)

    with open(f"./data/output/corpus_{langs}.csv", output_mode) as output_file, open(
        "./data/output/passed_log.txt", log_mode
    ) as passed_log_file:
        output_writer = csv.writer(output_file)

        def count_function_post_processing(
            i, corpus_row, relations, relations_id, output_corpus_row_num, output_l
        ):
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

        try:
            batch_size = 10
            totyu_interval = 100

            for i in range(start_id, input_reader.num_rows, batch_size):
                corpus_rows = []
                for j in range(batch_size):
                    if i + j < input_reader.num_rows:
                        corpus_rows.append(input_reader.read_row(i + j))

                i_l = i

                try:
                    count_function_batch(
                        i_l,
                        corpus_rows,
                        relations,
                        relations_id,
                        wordlists,
                        output_corpus_row_num,
                    )
                except Exception as e:
                    for j in range(batch_size):
                        if i + j < input_reader.num_rows:
                            count_function(
                                i + j,
                                input_reader.read_row(i + j),
                                relations,
                                relations_id,
                                wordlists,
                                output_corpus_row_num,
                            )

                if (i // batch_size) % totyu_interval == totyu_interval - 1:
                    for pos_tag in PART_OF_SPEACH_TAG_REV.values():
                        with open(
                            f"./data/output/relations_{langs}_{pos_tag}_totyu.csv", "w"
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
                    with open(f"./data/output/passed_id.txt", "w") as f:
                        f.write(str(i + batch_size - 1))
        except Exception as e:
            print(traceback.format_exc())
        finally:
            for pos_tag, relation in relations.items():
                with open(
                    f"./data/output/relations_{langs}_{pos_tag}.csv", "w"
                ) as f:
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


if __name__ == "__main__":
    main()
