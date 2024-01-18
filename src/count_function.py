import sys
import os
import pandas as pd
import traceback


def count_function_post_processing(
    i, corpus_row, translation, translation_id, output_corpus_row_num, output_l
):
    for index, command in enumerate(output_l):
        pos_tag = part_of_speach_tag_rev[command[0]]
        if command[1] + "_" + command[3] in translation[pos_tag]:
            translation[pos_tag][command[1] + "_" + command[3]][1] += 1
            translation[pos_tag][command[1] + "_" + command[3]][2].append(corpus_row[0])
            tmp_id = translation[pos_tag][command[1] + "_" + command[3]][0]
        else:
            tmp_id = translation_id[pos_tag]
            translation[pos_tag][command[1] + "_" + command[3]] = [
                tmp_id,
                1,
                [corpus_row[0]],
                "unknown",
                False,
            ]
            translation_id[pos_tag] += 1
        output_l[index].insert(1, str(tmp_id))
    # command_t = "/".join([":".join(output) for output in output_l])
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
    i,
    corpus_row,
    translation,
    translation_id,
    wordlists,
    output_corpus_row_num,
    passed_log_file,
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
            i, corpus_row, translation, translation_id, output_corpus_row_num, output_l
        )


def count_function_batch(
    i_l, corpus_rows, translation, translation_id, wordlists, output_corpus_row_num
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
            translation,
            translation_id,
            output_corpus_row_num,
            output_ls[i],
        )


# csv.field_size_limit(sys.maxsize)
args = sys.argv
start_id = int(args[1])
lang_a = args[2]
lang_b = args[3]
langs = lang_a + "_" + lang_b
sys.path.append("/root/src/alignment/" + langs)
from alignment import alignment, alignment_batch

base = os.path.dirname(os.path.abspath(__file__))
path_normalizer = os.path.normpath(os.path.join(base, "../normalizer/"))
sys.path.append(path_normalizer)
command = "from {}_normalizer import {}_normalizer as normalizer_lang_a".format(
    lang_a, lang_a
)
exec(command)
command = "from {}_normalizer import {}_normalizer as normalizer_lang_b".format(
    lang_b, lang_b
)
exec(command)

# check if output directory exists
if not os.path.isdir("./data/output"):
    os.makedirs("./data/output")

# corpusを一行毎に読み出す
# class CsvRowReader:
#     def __init__(self, path):
#         f = open(path, "r")
#         self.file = f
#         self.reader = csv.reader(f)
#         self.offset_list = []
#         while True:
#             self.offset_list.append(f.tell())
#             line = f.readline()
#             if line == "":
#                 break
#             # if len(self.offset_list) >= 201:
#             #     break
#         self.offset_list.pop()  # remove offset at end of file
#         self.num_rows = len(self.offset_list)

#     def __del__(self):
#         self.file.close()

#     def read_row(self, idx):
#         self.file.seek(self.offset_list[idx])
#         return next(self.reader)


# input_reader = CsvRowReader(f"./data/input/corpus_{langs}.csv")
input_corpus_filepath = f"./data/input/corpus_{langs}.csv"
df_corpus = pd.read_csv(input_corpus_filepath, header=0)

# pos_list = ["noun", "verb", "adj", "adverb"]
part_of_speach_tag_rev = {"n": "noun", "v": "verb", "a": "adj", "r": "adverb"}
part_of_speach_tag_code = {"noun": "n", "verb": "v", "adj": "a", "adverb": "r"}

word_columns = ["id_word", "name"]
translation_columns = [
    "id_translation",
    f"id_{lang_a}",
    f"id_{lang_b}",
    "id_corpus_list",
    "count",
]
corpus_columns = [
    "id_corpus",
    f"sentence_{lang_a}",
    f"sentence_{lang_b}",
    "alignment_info",
]
translation = (
    {}
)  # {pos_tag:{id_lang_a}_{id_lang_b}:[id,count,example,convert_from,invalid]}
translation_id = {}  # {pos_tag:id}
wordlists = {}  # {pos_tag:{word:id}}
process_list = []
output_corpus_row_num = 0
for pos_tag in part_of_speach_tag_rev.values():
    translation[pos_tag] = {}
    translation_id[pos_tag] = 0
    # Get wordlist
    input_wordlist_filepath = f"./data/input/wordlist_{lang_a}_{pos_tag}.csv"
    df_wordlist_lang_a = pd.read_csv(input_wordlist_filepath, header=0)
    wordlists[lang_a + "_" + pos_tag] = {
        rows[1]: int(rows[0]) for rows in df_wordlist_lang_a.values
    }
    # with open("./data/input/wordlist_" + lang_a + "_" + pos_tag + ".csv", mode="r") as inp:
    #     reader = list(csv.reader(inp))
    #     if not re.fullmatch("[-+]?\d+", reader[0][0]):
    #         reader = reader[1:]
    #     wordlists[lang_a + "_" + pos_tag] = {rows[1]: int(rows[0]) for rows in reader}
    #     max_id_lang_a = max(wordlists[lang_a + "_" + pos_tag].values())
    input_wordlist_filepath = f"./data/input/wordlist_{lang_b}_{pos_tag}.csv"
    df_wordlist_lang_b = pd.read_csv(input_wordlist_filepath, header=0)
    wordlists[lang_b + "_" + pos_tag] = {
        rows[1]: int(rows[0]) for rows in df_wordlist_lang_b.values
    }
    # with open("./data/input/wordlist_" + lang_b + "_" + pos_tag + ".csv", mode="r") as inp:
    #     reader = list(csv.reader(inp))
    #     if not re.fullmatch("[-+]?\d+", reader[0][0]):
    #         reader = reader[1:]
    #     wordlists[lang_b + "_" + pos_tag] = {rows[1]: int(rows[0]) for rows in reader}
    #     max_id_lang_b = max(wordlists[lang_b + "_" + pos_tag].values())
    flag_lang_a = False
    flag_lang_b = False
    wordlists_add = {}
    wordlists_add[lang_a + "_" + pos_tag] = {}
    wordlists_add[lang_b + "_" + pos_tag] = {}
    for key, word_id in wordlists[lang_a + "_" + pos_tag].items():
        if (
            normalizer_lang_a(key, part_of_speach_tag_code[pos_tag], "", test=True)
            not in wordlists[lang_a + "_" + pos_tag].keys()
        ):
            flag_lang_a = True
            max_id_lang_a = max_id_lang_a + 1
            wordlists_add[lang_a + "_" + pos_tag][
                normalizer_lang_a(key, part_of_speach_tag_code[pos_tag], "", test=True)
            ] = max_id_lang_a
    for key, word_id in wordlists[lang_b + "_" + pos_tag].items():
        if (
            normalizer_lang_b(key, part_of_speach_tag_code[pos_tag], "", test=True)
            not in wordlists[lang_b + "_" + pos_tag].keys()
        ):
            flag_lang_b = True
            max_id_lang_b = max_id_lang_b + 1
            wordlists_add[lang_b + "_" + pos_tag][
                normalizer_lang_b(key, part_of_speach_tag_code[pos_tag], "", test=True)
            ] = max_id_lang_b
    print("wordlist_add", wordlists_add)
    wordlists[lang_a + "_" + pos_tag].update(wordlists_add[lang_a + "_" + pos_tag])
    wordlists[lang_b + "_" + pos_tag].update(wordlists_add[lang_b + "_" + pos_tag])
    # if flag_lang_a:
    #     writer = csv.writer(
    #         open("./data/output/wordlist_" + lang_a + "_" + pos_tag + ".csv", "w")
    #     )
    #     for key, word_id in wordlists[lang_a + "_" + pos_tag].items():
    #         writer.writerow([word_id, key, "f"])
    if flag_lang_a:
        output_wordlist_filepath = f"./data/output/wordlist_{lang_a}_{pos_tag}.csv"
        df_wordlist_lang_a = pd.DataFrame(
            [
                [word_id, key, "f"]
                for key, word_id in wordlists[lang_a + "_" + pos_tag].items()
            ],
            columns=word_columns,
        )
        df_wordlist_lang_a.to_csv(output_wordlist_filepath, index=False)
    # if flag_lang_b:
    #     writer = csv.writer(
    #         open("./data/output/wordlist_" + lang_b + "_" + pos_tag + ".csv", "w")
    #     )
    #     for key, word_id in wordlists[lang_b + "_" + pos_tag].items():
    #         writer.writerow([word_id, key, "f"])
    if flag_lang_b:
        output_wordlist_filepath = f"./data/output/wordlist_{lang_b}_{pos_tag}.csv"
        df_wordlist_lang_b = pd.DataFrame(
            [
                [word_id, key, "f"]
                for key, word_id in wordlists[lang_b + "_" + pos_tag].items()
            ],
            columns=word_columns,
        )
        df_wordlist_lang_b.to_csv(output_wordlist_filepath, index=False)

# if start_id != 0:
#     output_file = open(f"./data/output/corpus_{langs}.csv", "a")
#     for pos_tag in part_of_speach_tag_rev.values():
#         translation[pos_tag] = {}
#         max_id = 0
#         with open(
#             "./data/output/translation_" + langs + "_" + pos_tag + "_midst.csv", mode="r"
#         ) as inp:
#             reader = csv.reader(inp)
#             for rows in reader:
#                 translation[pos_tag][rows[1] + "_" + rows[2]] = [
#                     int(rows[0]),
#                     int(rows[3]),
#                     eval(rows[4]),
#                     rows[5],
#                     rows[6],
#                 ]
#                 if max_id < int(rows[0]):
#                     max_id = int(rows[0])
#             translation_id[pos_tag] = max_id + 1
#     output_corpus_row_num = len(
#         [None for l in open(f"./data/output/corpus_{langs}.csv", "r")]
#     )
# else:
#     output_file = open(f"./data/output/corpus_{langs}.csv", "w")
if start_id != 0:
    output_corpus_filepath = f"./data/output/corpus_{langs}.csv"
    df_corpus = pd.read_csv(output_corpus_filepath, header=0)
    output_corpus_row_num = len(df_corpus)
else:
    output_corpus_filepath = f"./data/output/corpus_{langs}.csv"
    df_corpus = pd.DataFrame(columns=["id", "lang_a", "lang_b", "commands", "invalid"])
    df_corpus.to_csv(output_corpus_filepath, index=False)

# if start_id == 0:
#     passed_log_file = open("./data/output/passed_log.txt", "w")
# else:
#     passed_log_file = open("./data/output/passed_log.txt", "a")
# output_writer = csv.writer(output_file)
if start_id != 0:
    output_passed_log_filepath = f"./data/output/passed_log.txt"
    with open(output_passed_log_filepath, mode="r") as inp:
        passed_id_list = inp.readlines()
        passed_id_list = [int(passed_id) for passed_id in passed_id_list]
else:
    output_passed_log_filepath = f"./data/output/passed_log.txt"
    with open(output_passed_log_filepath, mode="w") as inp:
        pass
    passed_id_list = []


try:
    batch_size = 10
    midst_interval = 100

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
                translation,
                translation_id,
                wordlists,
                output_corpus_row_num,
            )
        except Exception as e:
            for j in range(batch_size):
                if i + j < input_reader.num_rows:
                    count_function(
                        i + j,
                        input_reader.read_row(i + j),
                        translation,
                        translation_id,
                        wordlists,
                        output_corpus_row_num,
                    )

        if (i // batch_size) % midst_interval == midst_interval - 1:
            for pos_tag in part_of_speach_tag_rev.values():
                with open(
                    f"./data/output/translation_{langs}_{pos_tag}_midst.csv", "w"
                ) as f:
                    writer = csv.writer(f)
                    for key, value in translation[pos_tag].items():
                        [id_lang_a, id_lang_b] = key.split("_")
                        writer.writerow(
                            [
                                value[0],
                                id_lang_a,
                                id_lang_b,
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
    for pos_tag, relation in translation.items():
        with open(f"./data/output/translation_{langs}_{pos_tag}.csv", "w") as f:
            writer = csv.writer(f)
            for key, value in relation.items():
                [id_lang_a, id_lang_b] = key.split("_")
                writer.writerow(
                    [
                        value[0],
                        id_lang_a,
                        id_lang_b,
                        value[1],
                        "{" + str(value[2])[1:-1] + "}",
                        value[3],
                        value[4],
                    ]
                )
