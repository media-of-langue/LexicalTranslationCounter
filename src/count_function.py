import os
import sys
import traceback

import pandas as pd


def output_translation(
    output_translation_filename: str,
    output_translation_filepath: str,
    df_translation: pd.DataFrame,
) -> None:
    df_translation.to_csv(output_translation_filepath, index=False)


def output_corpus(
    output_corpus_filename: str,
    output_corpus_filepath: str,
    df_corpus: pd.DataFrame,
) -> None:
    df_corpus.to_csv(output_corpus_filepath, index=False)


def create_translation(
    index: int,
    corpus_row: list,
    translation_dict: dict,
    translation_id_dict: dict,
    output_corpus_row_num: int,
    alignment_info: list,
) -> dict:
    for output_index, output_values in enumerate(alignment_info):
        pos = output_values[0]
        lang_a = output_values[1]
        lang_b = output_values[3]
        lang_pair = lang_a + "_" + lang_b
        if lang_pair in translation_dict[pos]:
            translation_dict[pos][lang_pair][1] += 1
            translation_dict[pos][lang_pair][2].append(corpus_row[0])
            id_translation = translation_dict[pos][lang_pair][0]
        else:
            id_translation = translation_id_dict[pos]
            translation_dict[pos][lang_pair] = [
                id_translation,  # id_translation
                lang_a,  # id_lang_a
                lang_b,  # id_lang_b
                1,  # count
                [corpus_row[0]],  # id_corpus_list
            ]
            translation_id_dict[pos] += 1
        alignment_info[output_index].insert(1, str(id_translation))
    return translation_dict


def create_alignment_info(
    index: int,
    corpus_row: list,  # [id_corpus, sentence_lang_a, sentence_lang_b, alignment_info]
    wordlist_dict: dict,
    passed_log_filepath: str,
) -> dict:
    """ """
    alignment_info = []
    if len(corpus_row) == 4:
        try:
            alignment_info = alignment(corpus_row, wordlist_dict)
        except Exception as e:
            print(traceback.format_exc())
            with open(passed_log_filepath, mode="a") as passed_log_file:
                passed_log_file.write(str(index))
                passed_log_file.write(str(corpus_row))
    return alignment_info


def main(
    lang_a: str,
    lang_b: str,
    lang_pair: str,
    start_id: int,
    input_dir: str,
    output_dir: str,
) -> None:
    input_corpus_filename = f"corpus_{lang_pair}.csv"
    input_corpus_filepath = os.path.join(input_dir, input_corpus_filename)
    df_corpus = pd.read_csv(input_corpus_filepath, header=0)
    print(len(df_corpus))
    pos_list = ["noun", "verb", "adj", "adverb"]
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

    # {pos:{id_lang_a}_{id_lang_b}:[id_translation,count,example,convert_from]}
    translation_dict = {}
    translation_id_dict = {}  # {pos:id}
    wordlist_dict = {}  # {pos:{word:id}}
    output_corpus_row_num = 0
    """
    品詞ごとに処理を行う。
    Process for each part of speech.
    """
    for pos in pos_list:
        translation_dict[pos] = {}
        translation_id_dict[pos] = 0
        # Get wordlist
        input_wordlist_filename = f"wordlist_{lang_a}_{pos}.csv"
        input_wordlist_filepath = os.path.join(input_dir, input_wordlist_filename)
        df_wordlist_lang_a = pd.read_csv(input_wordlist_filepath, header=0)
        wordlist_dict[lang_a + "_" + pos] = {
            int(rows[0]): rows[1] for rows in df_wordlist_lang_a.values
        }
        max_id_lang_a = max(wordlist_dict[lang_a + "_" + pos].keys())
        input_wordlist_filename = f"wordlist_{lang_b}_{pos}.csv"
        input_wordlist_filepath = os.path.join(input_dir, input_wordlist_filename)
        df_wordlist_lang_b = pd.read_csv(input_wordlist_filepath, header=0)
        wordlist_dict[lang_b + "_" + pos] = {
            int(rows[0]): rows[1] for rows in df_wordlist_lang_b.values
        }
        max_id_lang_b = max(wordlist_dict[lang_b + "_" + pos].keys())
        flag_lang_a = False
        flag_lang_b = False
        wordlist_normalized_dict = {}
        wordlist_normalized_dict[lang_a + "_" + pos] = {}
        wordlist_normalized_dict[lang_b + "_" + pos] = {}
        """
        normalizer_lang_a, normalizer_lang_bを用いて、wordlistに追加する単語を標準化する。
        Use normalizer_lang_a and normalizer_lang_b to standardize the words to be added to the wordlist.
        """
        for id_word, name in wordlist_dict[lang_a + "_" + pos].items():
            if (
                normalizer_lang_a(name, pos, "", test=True)
                not in wordlist_dict[lang_a + "_" + pos]
            ):
                flag_lang_a = True
                max_id_lang_a = max_id_lang_a + 1
                wordlist_normalized_dict[lang_a + "_" + pos][
                    normalizer_lang_a(name, pos, "", test=True)
                ] = max_id_lang_a
        for id_word, name in wordlist_dict[lang_b + "_" + pos].items():
            if (
                normalizer_lang_b(name, pos, "", test=True)
                not in wordlist_dict[lang_b + "_" + pos]
            ):
                flag_lang_b = True
                max_id_lang_b = max_id_lang_b + 1
                wordlist_normalized_dict[lang_b + "_" + pos][
                    normalizer_lang_b(name, pos, "", test=True)
                ] = max_id_lang_b
        # print("wordlist_normalized_dict", wordlist_normalized_dict)
        wordlist_dict[lang_a + "_" + pos].update(
            wordlist_normalized_dict[lang_a + "_" + pos]
        )
        wordlist_dict[lang_b + "_" + pos].update(
            wordlist_normalized_dict[lang_b + "_" + pos]
        )
        if flag_lang_a:
            output_wordlist_filename = f"wordlist_{lang_a}_{pos}.csv"
            output_wordlist_filepath = os.path.join(
                output_dir, output_wordlist_filename
            )
            df_wordlist_lang_a = pd.DataFrame(
                [
                    [id_word, name]
                    for id_word, name in wordlist_dict[lang_a + "_" + pos].items()
                ],
                columns=word_columns,
            )
            df_wordlist_lang_a.to_csv(output_wordlist_filepath, index=False)
        if flag_lang_b:
            output_wordlist_filename = f"wordlist_{lang_b}_{pos}.csv"
            output_wordlist_filepath = os.path.join(
                output_dir, output_wordlist_filename
            )
            df_wordlist_lang_b = pd.DataFrame(
                [
                    [id_word, name]
                    for id_word, name in wordlist_dict[lang_b + "_" + pos].items()
                ],
                columns=word_columns,
            )
            df_wordlist_lang_b.to_csv(output_wordlist_filepath, index=False)

    # Create corpus data
    output_corpus_filename = f"corpus_{lang_pair}.csv"
    output_corpus_filepath = os.path.join(output_dir, output_corpus_filename)
    # df_corpus = pd.read_csv(output_corpus_filepath, header=0)
    # output_corpus_row_num = len(df_corpus)
    # if start_id != 0:
    #     df_corpus = pd.read_csv(output_corpus_filepath, header=0)
    #     output_corpus_row_num = len(df_corpus)
    # else:
    #     df_corpus = pd.DataFrame(columns=corpus_columns)
    #     df_corpus.to_csv(output_corpus_filepath, index=False)

    # Get passed_id_list
    output_passed_log_filename = f"passed_log.txt"
    output_passed_log_filepath = os.path.join(output_dir, output_passed_log_filename)
    passed_id_list = []
    # if start_id != 0:
    #     output_passed_log_filename = f"passed_log.txt"
    #     output_passed_log_filepath = os.path.join(
    #         output_dir, output_passed_log_filename
    #     )
    #     with open(output_passed_log_filepath, mode="r") as output_passed_log_file:
    #         passed_id_list = output_passed_log_file.readlines()
    #         passed_id_list = [int(passed_id) for passed_id in passed_id_list]
    # else:
    #     passed_id_list = []

    # Count function
    batch_size = 10
    midst_interval = 100

    for index, corpus_row in df_corpus.iterrows():
        if index < start_id:
            continue
        if index in passed_id_list:
            continue
        if index >= start_id + batch_size:
            break
        alignment_info = create_alignment_info(
            index,
            corpus_row,
            wordlist_dict,
            output_passed_log_filepath,
        )
        translation_dict = create_translation(
            index,
            corpus_row,
            translation_dict,
            translation_id_dict,
            output_corpus_row_num,
            alignment_info,
        )
        output_corpus_row_num += 1
        if index % midst_interval == midst_interval - 1:
            for pos in pos_list:
                output_translation_filename = f"translation_{lang_pair}_{pos}.csv"
                output_translation_filepath = os.path.join(
                    output_dir, output_translation_filename
                )
                print(f"translation_dict[pos].items(): {translation_dict[pos].items()}")
                df_translation = pd.DataFrame(
                    [
                        [
                            value[0],
                            id_lang_a,
                            id_lang_b,
                            alignment_info,
                            value[4],
                        ]
                        for key, value in translation_dict[pos].items()
                        for id_lang_a, id_lang_b in [key.split("_")]
                    ],
                    columns=translation_columns,
                )
                output_translation(
                    output_translation_filename,
                    output_translation_filepath,
                    df_translation,
                )
            output_passed_log_filename = f"passed_log.txt"
            output_passed_log_filepath = os.path.join(
                output_dir, output_passed_log_filename
            )
            with open(output_passed_log_filepath, mode="w") as output_passed_log_file:
                for passed_id in passed_id_list:
                    output_passed_log_file.write(str(passed_id) + "\n")

    # try:
    #     print("Try")
    #     for index, corpus_row in df_corpus.iterrows():
    #         if index in passed_id_list:
    #             continue
    #         if index < start_id:
    #             continue
    #         if index >= start_id + batch_size:
    #             break
    #         alignment_info = create_alignment_info(
    #             index,
    #             corpus_row,
    #             wordlist_dict,
    #             output_passed_log_filepath,
    #         )
    #         translation_dict = create_translation(
    #             index,
    #             corpus_row,
    #             translation_dict,
    #             translation_id_dict,
    #             output_corpus_row_num,
    #             alignment_info,
    #         )
    #         output_corpus_row_num += 1
    #         if index % midst_interval == midst_interval - 1:
    #             for pos in pos_list:
    #                 output_translation_filename = f"translation_{lang_pair}_{pos}.csv"
    #                 output_translation_filepath = os.path.join(
    #                     output_dir, output_translation_filename
    #                 )
    #                 df_translation = pd.DataFrame(
    #                     [
    #                         [
    #                             value[0],
    #                             id_lang_a,
    #                             id_lang_b,
    #                             value[1],
    #                             "{" + str(value[2])[1:-1] + "}",
    #                             value[3],
    #                             value[4],
    #                         ]
    #                         for key, value in translation_dict[pos].items()
    #                         for id_lang_a, id_lang_b in [key.split("_")]
    #                     ],
    #                     columns=translation_columns,
    #                 )
    #                 output_translation(
    #                     output_translation_filename,
    #                     output_translation_filepath,
    #                     df_translation,
    #                 )
    #             output_passed_log_filename = f"passed_log.txt"
    #             output_passed_log_filepath = os.path.join(
    #                 output_dir, output_passed_log_filename
    #             )
    #             with open(
    #                 output_passed_log_filepath, mode="w"
    #             ) as output_passed_log_file:
    #                 for passed_id in passed_id_list:
    #                     output_passed_log_file.write(str(passed_id) + "\n")
    # except Exception as e:
    #     print(f"Error: {traceback.format_exc()}")
    # finally:
    #     print("Finally")
    #     for pos, translation in translation_dict.items():
    #         print(f"pos: {pos}, translation: {translation}")
    #         output_translation_filename = f"translation_{lang_pair}_{pos}.csv"
    #         output_translation_filepath = os.path.join(
    #             output_dir, output_translation_filename
    #         )
    #         df_translation = pd.DataFrame(
    #             [
    #                 [
    #                     value[0],
    #                     id_lang_a,
    #                     id_lang_b,
    #                     value[1],
    #                     "{" + str(value[2])[1:-1] + "}",
    #                     value[3],
    #                     value[4],
    #                 ]
    #                 for key, value in translation.items()
    #                 for id_lang_a, id_lang_b in [key.split("_")]
    #             ],
    #             columns=translation_columns,
    #         )
    #         output_translation(
    #             output_translation_filename, output_translation_filepath, df_translation
    #         )


if __name__ == "__main__":
    # Get arguments
    args = sys.argv
    if len(args) < 3:
        print("Usage: python count_function.py lang_a lang_b [start_id]")
        sys.exit(1)
    lang_a = args[1]
    lang_b = args[2]
    if len(args) == 3:
        start_id = 0
    else:
        start_id = int(args[3])
    lang_pair = lang_a + "_" + lang_b

    # import alignment function
    path_alignment = "/root/src/alignment/"
    sys.path.append(os.path.join(path_alignment + lang_pair))
    from alignment import alignment

    # import normalizer
    path_normalizer = "/root/src/normalizer/"
    sys.path.append(path_normalizer)

    # import normalizer
    command = "from {}_normalizer import {}_normalizer as normalizer_lang_a".format(
        lang_a, lang_a
    )
    exec(command)
    command = "from {}_normalizer import {}_normalizer as normalizer_lang_b".format(
        lang_b, lang_b
    )
    exec(command)

    input_dir = "./data/input/"
    output_dir = "./data/output/"
    os.makedirs(output_dir, exist_ok=True)

    main(lang_a, lang_b, lang_pair, start_id, input_dir, output_dir)
