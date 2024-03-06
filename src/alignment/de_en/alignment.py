import itertools
import sys
import os
import torch
import transformers
import csv

config = transformers.BertConfig.from_pretrained(
    "/root/src/model/awesome_model_with_co/config.json"
)
model = transformers.BertModel.from_pretrained(
    "/root/src/model/awesome_model_with_co/pytorch_model.bin", config=config
)
tokenizer_config = transformers.BertConfig.from_pretrained(
    "/root/src/model/awesome_model_with_co/tokenizer_config.json"
)
tokenizer = transformers.BertTokenizer.from_pretrained(
    "/root/src/model/awesome_model_with_co/", config=tokenizer_config
)

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
model.to(device)

base = os.path.dirname(os.path.abspath(__file__))
path_morphological = os.path.normpath(os.path.join(base, "../../morphological/"))
path_normalizer = os.path.normpath(os.path.join(base, "../../normalizer/"))
path_exception = os.path.normpath(os.path.join(base, "./exceptions.csv"))

sys.path.append(path_morphological)
from en_morphological import en_morphological, en_morphological_batch
from de_morphological import de_morphological, de_morphological_batch

sys.path.append(path_normalizer)
from en_normalizer import en_normalizer
from de_normalizer import de_normalizer

# TODO: read by pandas
exceptions = list(csv.reader(open(path_exception, "r"), delimiter=","))[1:]

max_word_len = 3

part_of_speach_tag = {"noun": "n", "verb": "v", "adj": "a", "adverb": "r"}
part_of_speach_tag_rev = {"n": "noun", "v": "verb", "a": "adj", "r": "adverb"}

src_except_l = ["nicht"]
trg_except_l1 = ["not", "n't"]
trg_except_l2 = []
src_relative_index_except = 1
trg_relative_index_except1 = 1
trg_relative_index_except2 = -1

src_word_sep = " "
trg_word_sep = " "

# params
align_layer = 8
threshold = 4e-7


def awesome_alignment_preprocessing(sent_src, sent_tgt):
    token_src, token_tgt = [tokenizer.tokenize(word) for word in sent_src], [
        tokenizer.tokenize(word) for word in sent_tgt
    ]
    wid_src, wid_tgt = [tokenizer.convert_tokens_to_ids(x) for x in token_src], [
        tokenizer.convert_tokens_to_ids(x) for x in token_tgt
    ]
    ids_src, ids_tgt = (
        tokenizer.prepare_for_model(
            list(itertools.chain(*wid_src)),
            return_tensors="pt",
            model_max_length=tokenizer.model_max_length,
            truncation=True,
        )["input_ids"],
        tokenizer.prepare_for_model(
            list(itertools.chain(*wid_tgt)),
            return_tensors="pt",
            truncation=True,
            model_max_length=tokenizer.model_max_length,
        )["input_ids"],
    )
    sub2word_map_src = []
    for i, word_list in enumerate(token_src):
        sub2word_map_src += [i for x in word_list]
    sub2word_map_tgt = []
    for i, word_list in enumerate(token_tgt):
        sub2word_map_tgt += [i for x in word_list]

    return ids_src, ids_tgt, sub2word_map_src, sub2word_map_tgt


def awesome_alignment_postprocessing(
    softmax_inter,
    sub2word_map_src,
    sub2word_map_tgt,
    pos_src,
    pos_trg,
    sent_src,
    sent_tgt,
):
    align_subwords = torch.nonzero(softmax_inter, as_tuple=False)
    index_pair_list = []
    for i_tmp, j_tmp in align_subwords:
        i = sub2word_map_src[i_tmp]
        j = sub2word_map_tgt[j_tmp]
        src_index = -1
        trg_index = -1
        for index_pair_index, index_pair in enumerate(index_pair_list):
            if i in index_pair[0]:
                src_index = index_pair_index
            if j in index_pair[1]:
                trg_index = index_pair_index
        if src_index == -1 and trg_index == -1:
            index_pair_list.append([{i}, {j}])
        elif src_index != -1 and trg_index != -1 and src_index != trg_index:
            index_pair_list[src_index][0] | index_pair_list[trg_index][0]
            index_pair_list[src_index][1] | index_pair_list[trg_index][1]
        elif src_index != -1:
            index_pair_list[src_index][0].add(i)
            index_pair_list[src_index][1].add(j)
        elif trg_index != -1:
            index_pair_list[trg_index][0].add(i)
            index_pair_list[trg_index][1].add(j)

        # align_words.add( (sub2word_map_src[i], sub2word_map_tgt[j]) )
    index_src_ignore = set()
    index_trg_ignore = set()
    alignmented_l = []
    alignmented_l_append = alignmented_l.append
    for word_src_except in src_except_l:
        if word_src_except in sent_src:
            for index_src, word_tmp in enumerate(sent_src):
                if word_tmp == word_src_except:
                    index_src_ignore.add(index_src + src_relative_index_except)
    for word_trg_except in trg_except_l1:
        if word_trg_except in sent_tgt:
            for index_trg, word_tmp in enumerate(sent_tgt):
                if word_tmp == word_trg_except:
                    index_trg_ignore.add(index_trg + trg_relative_index_except1)
    for word_trg_except in trg_except_l2:
        if word_trg_except in sent_tgt:
            for index_trg, word_tmp in enumerate(sent_tgt):
                if word_tmp == word_trg_except:
                    index_trg_ignore.add(index_trg + trg_relative_index_except2)

    for index_pair in index_pair_list:
        if index_pair[0].isdisjoint(index_src_ignore) and index_pair[1].isdisjoint(
            index_trg_ignore
        ):
            src_indexes_sorted = sorted(index_pair[0])
            trg_indexes_sorted = sorted(index_pair[1])
            src_index_independent = [
                index_src_index
                for index_src_index, src_index in enumerate(src_indexes_sorted)
                if pos_src[src_index] != ""
            ]
            if len(src_index_independent) > 1:
                if src_index_independent[-1] + 1 < len(src_indexes_sorted):
                    src_words_list = (
                        [
                            sent_src[src_index]
                            for src_index in src_indexes_sorted[
                                : src_index_independent[0]
                            ]
                        ]
                        + [
                            src_word_sep.join(
                                [
                                    sent_src[src_index]
                                    for src_index in src_indexes_sorted[
                                        src_index_independent[
                                            0
                                        ] : src_index_independent[-1]
                                        + 1
                                    ]
                                ]
                            )
                        ]
                        + [
                            sent_src[src_index]
                            for src_index in src_indexes_sorted[
                                src_index_independent[-1] + 1 :
                            ]
                        ]
                    )
                    src_pos_list = (
                        [
                            pos_src[src_index]
                            for src_index in src_indexes_sorted[
                                : src_index_independent[0]
                            ]
                        ]
                        + [
                            "/".join(
                                [
                                    pos_src[src_index]
                                    for src_index in src_indexes_sorted[
                                        src_index_independent[
                                            0
                                        ] : src_index_independent[-1]
                                        + 1
                                    ]
                                ]
                            )
                        ]
                        + [
                            pos_src[src_index]
                            for src_index in src_indexes_sorted[
                                src_index_independent[-1] + 1 :
                            ]
                        ]
                    )
                else:
                    src_words_list = [
                        sent_src[src_index]
                        for src_index in src_indexes_sorted[: src_index_independent[0]]
                    ] + [
                        src_word_sep.join(
                            [
                                sent_src[src_index]
                                for src_index in src_indexes_sorted[
                                    src_index_independent[0] :
                                ]
                            ]
                        )
                    ]
                    src_pos_list = [
                        pos_src[src_index]
                        for src_index in src_indexes_sorted[: src_index_independent[0]]
                    ] + [
                        "/".join(
                            [
                                pos_src[src_index]
                                for src_index in src_indexes_sorted[
                                    src_index_independent[0] :
                                ]
                            ]
                        )
                    ]
            else:
                src_words_list = [
                    sent_src[src_index] for src_index in src_indexes_sorted
                ]
                src_pos_list = [pos_src[src_index] for src_index in src_indexes_sorted]
            trg_index_independent = [
                index_trg_index
                for index_trg_index, trg_index in enumerate(trg_indexes_sorted)
                if pos_trg[trg_index] != ""
            ]
            if len(trg_index_independent) > 1:
                if trg_index_independent[-1] + 1 < len(trg_indexes_sorted):
                    trg_words_list = (
                        [
                            sent_tgt[trg_index]
                            for trg_index in trg_indexes_sorted[
                                : trg_index_independent[0]
                            ]
                        ]
                        + [
                            trg_word_sep.join(
                                [
                                    sent_tgt[trg_index]
                                    for trg_index in trg_indexes_sorted[
                                        trg_index_independent[
                                            0
                                        ] : trg_index_independent[-1]
                                        + 1
                                    ]
                                ]
                            )
                        ]
                        + [
                            sent_tgt[trg_index]
                            for trg_index in trg_indexes_sorted[
                                trg_index_independent[-1] + 1 :
                            ]
                        ]
                    )
                    trg_pos_list = (
                        [
                            pos_trg[trg_index]
                            for trg_index in trg_indexes_sorted[
                                : trg_index_independent[0]
                            ]
                        ]
                        + [
                            "/".join(
                                [
                                    pos_trg[trg_index]
                                    for trg_index in trg_indexes_sorted[
                                        trg_index_independent[
                                            0
                                        ] : trg_index_independent[-1]
                                        + 1
                                    ]
                                ]
                            )
                        ]
                        + [
                            pos_trg[trg_index]
                            for trg_index in trg_indexes_sorted[
                                trg_index_independent[-1] + 1 :
                            ]
                        ]
                    )
                else:
                    trg_words_list = [
                        sent_tgt[trg_index]
                        for trg_index in trg_indexes_sorted[: trg_index_independent[0]]
                    ] + [
                        trg_word_sep.join(
                            [
                                sent_tgt[trg_index]
                                for trg_index in trg_indexes_sorted[
                                    trg_index_independent[0] :
                                ]
                            ]
                        )
                    ]
                    trg_pos_list = [
                        pos_trg[trg_index]
                        for trg_index in trg_indexes_sorted[: trg_index_independent[0]]
                    ] + [
                        "/".join(
                            [
                                pos_trg[trg_index]
                                for trg_index in trg_indexes_sorted[
                                    trg_index_independent[0] :
                                ]
                            ]
                        )
                    ]
            else:
                trg_words_list = [
                    sent_tgt[trg_index] for trg_index in trg_indexes_sorted
                ]
                trg_pos_list = [pos_trg[trg_index] for trg_index in trg_indexes_sorted]
            alignmented_l_append(
                (src_pos_list, src_words_list, trg_pos_list, trg_words_list)
            )
    return alignmented_l


def awesome_alignment_batch(
    sentence_srcs, sentence_trgs, src_morphological_batch, trg_morphological_batch
):
    # morphological analysis
    sent_srcs, pos_srcs = src_morphological_batch(sentence_srcs)
    sent_tgts, pos_trgs = trg_morphological_batch(sentence_trgs)

    # pre-processing
    ids_srcs, ids_trgs, sub2word_map_srcs, sub2word_map_trgs = zip(
        *[
            awesome_alignment_preprocessing(sent_src, sent_tgt)
            for sent_src, sent_tgt in zip(sent_srcs, sent_tgts)
        ]
    )

    # alignment
    def padding(ids_list):
        pad_token_id = tokenizer.pad_token_id

        max_size = max([ids.size(0) for ids in ids_list])
        ids_list = [
            torch.cat(
                [
                    ids,
                    torch.tensor(
                        [pad_token_id] * (max_size - ids.size(0)),
                        dtype=torch.long,
                        device=ids.device,
                    ),
                ]
            )
            for ids in ids_list
        ]

        return torch.stack(ids_list)

    padded_ids_src_tensor = padding(ids_srcs)
    padded_ids_trg_tensor = padding(ids_trgs)

    model.eval()

    with torch.no_grad():
        padded_out_src_tensor = model(
            padded_ids_src_tensor.to(device), output_hidden_states=True
        )[2][align_layer].to("cpu")
        padded_out_trg_tensor = model(
            padded_ids_trg_tensor.to(device), output_hidden_states=True
        )[2][align_layer].to("cpu")

    softmax_inter_list = []

    for ids_src, ids_trg, out_src, out_trg in zip(
        ids_srcs, ids_trgs, padded_out_src_tensor, padded_out_trg_tensor
    ):
        out_src = out_src[1 : ids_src.size(0) - 1]
        out_trg = out_trg[1 : ids_trg.size(0) - 1]

        dot_prod = torch.matmul(out_src, out_trg.transpose(-1, -2))

        softmax_srctrg = torch.nn.Softmax(dim=-1)(dot_prod)
        softmax_trgsrc = torch.nn.Softmax(dim=-2)(dot_prod)

        softmax_inter = (softmax_srctrg > threshold) * (softmax_trgsrc > threshold)

        softmax_inter_list.append(softmax_inter)

    # post-processing
    alignmented_ls = [
        awesome_alignment_postprocessing(
            softmax_inter,
            sub2word_map_src,
            sub2word_map_trg,
            pos_src,
            pos_trg,
            sent_src,
            sent_trg,
        )
        for softmax_inter, sub2word_map_src, sub2word_map_trg, pos_src, pos_trg, sent_src, sent_trg in zip(
            softmax_inter_list,
            sub2word_map_srcs,
            sub2word_map_trgs,
            pos_srcs,
            pos_trgs,
            sent_srcs,
            sent_tgts,
        )
    ]

    return alignmented_ls


def alignment_preprocess(corpus_row):
    corpus_row = list(corpus_row)
    corpus_row[1] = corpus_row[1].replace("@", "")
    corpus_row[2] = corpus_row[2].replace("@", "")
    return corpus_row


def alignment_postprocess(alignmented, wordlist, test=False):
    output_l = []
    output_l_append = output_l.append
    src_normalized_dict = {}
    trg_normalized_dict = {}
    for word_pair in alignmented:
        src_pos_l = word_pair[0]
        src_word_l = word_pair[1]
        trg_pos_l = word_pair[2]
        trg_word_l = word_pair[3]
        independent_index_src = -1
        for src_index, pos_tag in enumerate(src_pos_l):
            if pos_tag != "":
                independent_index_src = src_index
        independent_index_trg = -1
        for trg_index, pos_tag in enumerate(trg_pos_l):
            if pos_tag != "":
                independent_index_trg = trg_index
        # independent_pos_tag = set(src_pos_l[independent_index_src].split("/")+trg_pos_l[independent_index_trg].split("/"))
        independent_pos_tag = set(src_pos_l[independent_index_src].split("/")) & set(
            trg_pos_l[independent_index_trg].split("/")
        )
        independent_pos_tag.discard("")
        find_flag_src = False
        find_flag_trg = False
        src_pos_tag_s = set()
        trg_pos_tag_s = set()
        for src_len in range(min(len(src_word_l), max_word_len), 0, -1):
            for src_con in itertools.combinations(range(len(src_word_l)), src_len):
                if independent_index_src in src_con:
                    src_word = src_word_sep.join(
                        [src_word_l[src_index] for src_index in src_con]
                    )
                    for pos_tag in independent_pos_tag:
                        if test:
                            src_normalized = de_normalizer(
                                src_word, pos_tag, wordlist, test
                            )
                            src_id = -1
                        else:
                            src_id, src_normalized = de_normalizer(
                                src_word, pos_tag, wordlist, test
                            )
                        if src_id is not None:
                            if src_word not in src_normalized_dict:
                                src_normalized_dict[src_word] = {}
                            src_normalized_dict[src_word][pos_tag] = {
                                "id": int(src_id),
                                "word_normalized": src_normalized,
                            }
                            find_flag_src = True
                            src_pos_tag_s.add(pos_tag)
                if find_flag_src:
                    break
            else:
                continue
            break

        for trg_len in range(min(len(trg_word_l), max_word_len), 0, -1):
            for trg_con in itertools.combinations(range(len(trg_word_l)), trg_len):
                if independent_index_trg in trg_con:
                    trg_word = trg_word_sep.join(
                        [trg_word_l[trg_index] for trg_index in trg_con]
                    )
                    for pos_tag in independent_pos_tag:
                        if test:
                            trg_normalized = en_normalizer(
                                trg_word, pos_tag, wordlist, test
                            )
                            trg_id = -1
                        else:
                            trg_id, trg_normalized = en_normalizer(
                                trg_word, pos_tag, wordlist, test
                            )
                        if trg_id is not None:
                            if trg_word not in trg_normalized_dict:
                                trg_normalized_dict[trg_word] = {}
                            trg_normalized_dict[trg_word][pos_tag] = {
                                "id": int(trg_id),
                                "word_normalized": trg_normalized,
                            }
                            find_flag_trg = True
                            trg_pos_tag_s.add(pos_tag)
                if find_flag_trg:
                    break
            else:
                continue
            break
        if find_flag_src and find_flag_trg:
            for pos_tag in src_pos_tag_s & trg_pos_tag_s:
                if [
                    src_normalized_dict[src_word][pos_tag]["word_normalized"],
                    trg_normalized_dict[trg_word][pos_tag]["word_normalized"],
                ] not in exceptions:
                    output_l_append(
                        [
                            pos_tag,
                            str(src_normalized_dict[src_word][pos_tag]["id"]),
                            src_word,
                            str(trg_normalized_dict[trg_word][pos_tag]["id"]),
                            trg_word,
                        ]
                    )
    return output_l


def alignment_batch(corpus_rows, wordlist, test=False):
    # pre-processing
    corpus_rows = [alignment_preprocess(corpus_row) for corpus_row in corpus_rows]

    # morphological analysis and alignment
    alignmented_ls = awesome_alignment_batch(
        [corpus_row[1] for corpus_row in corpus_rows],
        [corpus_row[2] for corpus_row in corpus_rows],
        de_morphological_batch,
        en_morphological_batch,
    )

    # post-processing
    assert len(alignmented_ls) == len(corpus_rows)

    output_ls = [
        alignment_postprocess(alignmented, wordlist, test)
        for alignmented in alignmented_ls
    ]

    return output_ls


def alignment(corpus_row, wordlist, test=False):
    corpus_rows = [corpus_row]
    return alignment_batch(corpus_rows, wordlist, test)[0]
