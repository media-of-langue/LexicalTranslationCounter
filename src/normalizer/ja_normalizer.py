import environ
import pandas as pd
from pyknp import Juman
import os

base = os.path.dirname(os.path.abspath(__file__))
env = environ.Env()

jumanpp = Juman(timeout=300, jumanpp=True)
jumanpp_detail = Juman(timeout=300, jumanpp=True, option="-s 5")
pos_list = ["adj", "adverb", "noun", "verb"]
pos_list_ja = ["形容詞", "副詞", "名詞", "動詞"]

except_dict_dict = {}
for pos in pos_list:
    path_normalize = os.path.normpath(
        os.path.join(base, "./data/ja/" + pos + "_normalize.csv")
    )
    except_dict_dict[pos] = pd.read_csv(
        path_normalize,
        header=None,
        index_col=0,
    ).to_dict()


def ja_normalizer(word, pos, wordlist, test=False):
    except_dict = except_dict_dict[pos]
    word = word.replace(" ", "　")
    if word in except_dict:
        word_normalized = except_dict[word]
    else:
        juman_mrph_list = jumanpp.analysis(word).mrph_list()
        mrph_dict_list = []
        for mrph_item in juman_mrph_list:
            mrph_dict_list.append(
                {
                    "midasi": mrph_item.midasi,
                    "repname": mrph_item.repname,
                    "hinsi": mrph_item.hinsi,
                    "bunrui": mrph_item.bunrui,
                    "katuyou1": mrph_item.katuyou1,
                    "genkei": mrph_item.genkei,
                }
            )
        word_normalized, pos_flag = get_normalize_word(mrph_dict_list, pos)
        if not pos_flag:
            found_flag, word_normalized_tmp = recheck(word, pos)
            if found_flag:
                word_normalized = word_normalized_tmp
    if test:
        return word_normalized
    tmp_key = "ja_" + pos_list[pos]
    if word_normalized in wordlist[tmp_key]:
        id_word = wordlist[tmp_key][word_normalized]
    else:
        if len(juman_mrph_list) > 1:
            if (
                juman_mrph_list[-1].genkei == "する"
                and juman_mrph_list[-1].hinsi == "動詞"
                and juman_mrph_list[-1].katuyou1 == "サ変動詞"
                and juman_mrph_list[-2] in pos_list_ja
            ):
                id_word = max(wordlist[tmp_key].values()) + 1
                wordlist[tmp_key][word_normalized] = id_word
            else:
                id_word = None
        else:
            id_word = None
    return id_word, word_normalized


def recheck(word, pos):
    juman_mrph_list = jumanpp_detail.analysis(word).mrph_list()
    ranking_list = [[], [], [], [], []]
    for mrph_detail in juman_mrph_list:
        mrph_l = mrph_detail.midasi.split("\t")
        # print(mrph_l)
        detail_l = mrph_l[-1].split("|")
        ranks = detail_l[-1].replace("ランク:", "").split(";")
        for rank in ranks:
            try:
                rank = int(rank)
                info_dict = {
                    "midasi": mrph_l[5],
                    "repname": mrph_l[6],
                    "hinsi": mrph_l[9],
                    "bunrui": mrph_l[11],
                    "katuyou1": mrph_l[13],
                    "genkei": mrph_l[7],
                }

                ranking_list[rank - 1].append(info_dict)
            except Exception as e:
                print(e)
                pass
    for mrph_dict_list in ranking_list:
        if mrph_dict_list == []:
            break
        word_normalized, pos_flag = get_normalize_word(mrph_dict_list, pos)
        if pos_flag:
            return True, word_normalized
    return False, word


def get_normalize_word(mrph_dict_list, pos):
    word_normalized = ""
    pos_flag = False
    if pos == "adj":
        for index_mrph in range(len(mrph_dict_list) - 1):
            mrph_item = mrph_dict_list[index_mrph]
            # 本当はjumanの持っている活用データを用いて感じに戻した上で活用させる方が良い
            if mrph_item["hinsi"] == "名詞":
                if "/" in mrph_item["repname"]:
                    word_normalized += mrph_item["repname"].split("/")[0]
                else:
                    word_normalized += mrph_item["midasi"]
            else:
                word_normalized += mrph_item["midasi"]
        mrph_item = mrph_dict_list[-1]
        if "形容詞" in mrph_item["bunrui"] or "形容詞" in mrph_item["hinsi"]:
            if "/" in mrph_item["repname"]:
                word_last = mrph_item["repname"].split("/")[0]
            else:
                word_last = mrph_item["genkei"]
            if "ナ" in mrph_item["katuyou1"] and (
                word_last[-1] == "だ" or word_last[-1] == "な"
            ):
                word_normalized += word_last[:-1]
            else:
                word_normalized += word_last
            pos_flag = True
        else:
            word_normalized += mrph_item["midasi"]
    elif pos == "verb":
        for index_mrph in range(len(mrph_dict_list) - 1):
            mrph_item = mrph_dict_list[index_mrph]
            # 本当はjumanの持っている活用データを用いて感じに戻した上で活用させる方が良い
            if mrph_item["hinsi"] == "名詞":
                if "/" in mrph_item["repname"]:
                    word_normalized += mrph_item["repname"].split("/")[0]
                else:
                    word_normalized += mrph_item["midasi"]
            else:
                word_normalized += mrph_item["midasi"]
        mrph_item = mrph_dict_list[-1]
        if "動詞" in mrph_item["hinsi"] or "動詞" in mrph_item["bunrui"]:
            if "/" in mrph_item["repname"]:
                word_last = mrph_item["repname"].split("/")[0]
            else:
                word_last = mrph_item["genkei"]
            word_normalized += word_last
            pos_flag = True
        else:
            word_normalized += mrph_item["midasi"]
    elif pos == "adverb":
        for index_mrph in range(len(mrph_dict_list) - 1):
            mrph_item = mrph_dict_list[index_mrph]
            # 本当はjumanの持っている活用データを用いて感じに戻した上で活用させる方が良い
            if mrph_item["hinsi"] == "名詞":
                if "/" in mrph_item["repname"]:
                    word_normalized += mrph_item["repname"].split("/")[0]
                else:
                    word_normalized += mrph_item["midasi"]
            else:
                word_normalized += mrph_item["midasi"]
        mrph_item = mrph_dict_list[-1]
        if "副詞" in mrph_item["hinsi"] or "副詞" in mrph_item["bunrui"]:
            if "/" in mrph_item["repname"]:
                word_last = mrph_item["repname"].split("/")[0]
            else:
                word_last = mrph_item["genkei"]
            word_normalized += word_last
            pos_flag = True
        else:
            word_normalized += mrph_item["midasi"]
    elif pos == "noun":
        for index_mrph in range(len(mrph_dict_list) - 1):
            mrph_item = mrph_dict_list[index_mrph]
            # 本当はjumanの持っている活用データを用いて感じに戻した上で活用させる方が良い
            if mrph_item["hinsi"] == "名詞":
                if "/" in mrph_item["repname"]:
                    word_normalized += mrph_item["repname"].split("/")[0]
                else:
                    word_normalized += mrph_item["midasi"]
            else:
                word_normalized += mrph_item["midasi"]
        mrph_item = mrph_dict_list[-1]
        # if "形容詞" in mrph_item["bunrui"] or "形容詞" in mrph_item["hinsi"]:
        #     if "?" in mrph_item["repname"]():
        #         word_last = mrph_item["genkei"]
        #     elif "/" in mrph_item["repname"]:
        #         word_last = mrph_item["repname"].split("/")[0]
        #     else:
        #         word_last = mrph_item["genkei"]
        #     if "ナ" in mrph_item["katuyou1"] and (
        #         word_last[-1] == "だ" or word_last[-1] == "な"
        #     ):
        #         word_normalized += word_last[:-1]
        #     else:
        #         word_normalized += word_last
        #     pos_flag = True
        # elif "名詞" in mrph_item["hinsi"] or "名詞" in mrph_item["bunrui"]:
        if "名詞" in mrph_item["hinsi"] or "名詞" in mrph_item["bunrui"]:
            if "/" in mrph_item["repname"]:
                word_normalized += mrph_item["repname"].split("/")[0]
            else:
                word_normalized += mrph_item["genkei"]
            pos_flag = True
        else:
            if "/" in mrph_item["repname"]:
                word_normalized += mrph_item["repname"].split("/")[0]
            else:
                word_normalized += mrph_item["genkei"]
    return word_normalized, pos_flag
