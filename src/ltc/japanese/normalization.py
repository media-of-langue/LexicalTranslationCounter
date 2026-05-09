"""Japanese normalization helpers layered on top of backend-agnostic morphology."""

from __future__ import annotations

import os
from pathlib import Path

import environ
import pandas as pd

from jumanpp_safety import analyze_jumanpp
from ltc.japanese.backends import current_japanese_text_backend_name
from ltc.japanese.morphology import get_japanese_raw_morphemes, raw_morphemes_to_dicts


env = environ.Env()
POS_TAG_REV = {"n": "noun", "a": "adj", "v": "verb", "r": "adverb"}
INDEPENDENT_MRPH = ["形容詞", "名詞", "動詞", "副詞"]
EXPERIMENTAL_NORMALIZATION_MAP = {
    "飽きる": "飽く",
    "また": "又",
    "いう": "言う",
    "なぜ": "何故",
    "なあ": "なる",
    "乗せる": "載せる",
    "払わさ": "払う",
    "払わす": "払う",
}
EXPERIMENTAL_CONTEXTLESS_VERB_MAP = {
    "当て": "当てる",
    "考え": "考える",
    "作り": "作る",
    "使い": "使う",
    "なっ": "なる",
    "変え": "変える",
    "感じ": "感じる",
    "離れ": "離れる",
    "思い": "思う",
}
TRAILING_HEAD_NOUN_MODIFIERS = {"自体", "自身"}
TRAILING_HEAD_NOUN_SUFFIXES = {"等", "達", "ら"}
TRAILING_HEAD_NOUN_SUFFIX_SURFACES = {"たち"}

NORMALIZE_DATA_DIR = (
    Path(__file__).resolve().parents[2] / "normalizer" / "normalize_data" / "ja"
)
except_dict_dict = {}
for pos_tag in POS_TAG_REV:
    path_normalize = os.path.normpath(
        os.path.join(str(NORMALIZE_DATA_DIR), pos_tag + "_normalize.csv")
    )
    except_dict_dict[pos_tag] = pd.read_csv(
        path_normalize,
        header=None,
        index_col=0,
    ).to_dict()


def get_jumanpp():
    from pyknp import Juman

    return Juman(timeout=300, jumanpp=True)


def get_jumanpp_detail():
    from pyknp import Juman

    return Juman(timeout=300, jumanpp=True, option="-s 5")


def parse_juman_normalizer_dicts(word):
    raw_items = analyze_jumanpp(get_jumanpp(), word)
    return [
        {
            "midasi": mrph_item.midasi,
            "repname": getattr(mrph_item, "repname", "") or mrph_item.genkei,
            "hinsi": mrph_item.hinsi,
            "bunrui": mrph_item.bunrui,
            "katuyou1": mrph_item.katuyou1,
            "genkei": mrph_item.genkei,
        }
        for mrph_item in raw_items
    ]


def parse_generic_normalizer_dicts(word, backend_name):
    raw_morphs = get_japanese_raw_morphemes(word, backend_name=backend_name)
    return raw_morphemes_to_dicts(raw_morphs)


def ja_normalizer(word, pos_tag, wordlist, test=False):
    backend_name = current_japanese_text_backend_name()
    if backend_name == "jumanpp":
        return ja_juman_normalizer(word, pos_tag, wordlist, test=test)
    return ja_experimental_normalizer(
        word,
        pos_tag,
        wordlist,
        test=test,
        backend_name=backend_name,
    )


def ja_juman_normalizer(word, pos_tag, wordlist, test=False):
    return normalize_with_backend(word, pos_tag, wordlist, test, backend_name="jumanpp")


def ja_experimental_normalizer(word, pos_tag, wordlist, test=False, backend_name=None):
    backend_name = backend_name or current_japanese_text_backend_name()
    return normalize_with_backend(word, pos_tag, wordlist, test, backend_name=backend_name)


def normalize_with_backend(word, pos_tag, wordlist, test, backend_name):
    except_dict = except_dict_dict[pos_tag]
    lookup_word = word.replace(" ", "　") if backend_name == "jumanpp" else word
    if lookup_word in except_dict:
        word_normalized = except_dict[lookup_word]
        mrph_dict_l = [
            {
                "midasi": lookup_word,
                "repname": lookup_word,
                "hinsi": "",
                "bunrui": "",
                "katuyou1": "",
                "genkei": lookup_word,
            }
        ]
    else:
        mrph_dict_l = (
            parse_juman_normalizer_dicts(lookup_word)
            if backend_name == "jumanpp"
            else parse_generic_normalizer_dicts(lookup_word, backend_name)
        )
        if not mrph_dict_l:
            word_normalized = word
        else:
            word_normalized, pos_tag_flag = get_normalize_word(mrph_dict_l, pos_tag)
            if backend_name == "jumanpp" and not pos_tag_flag:
                found_flag, word_normalized_tmp = recheck(lookup_word, pos_tag)
                if found_flag:
                    word_normalized = word_normalized_tmp
            elif backend_name != "jumanpp":
                word_normalized, pos_tag_flag = normalize_contextless_experimental_fragment(
                    lookup_word,
                    pos_tag,
                    word_normalized,
                    pos_tag_flag,
                )
                word_normalized = normalize_experimental_compatibility(word_normalized)
    if test:
        return word_normalized
    tmp_key = "ja_" + POS_TAG_REV[pos_tag]
    if word_normalized in wordlist[tmp_key]:
        identifier = wordlist[tmp_key][word_normalized]
    else:
        if len(mrph_dict_l) > 1 and is_productive_sahen_verb(mrph_dict_l):
            identifier = max(wordlist[tmp_key].values()) + 1
            wordlist[tmp_key][word_normalized] = identifier
        else:
            identifier = None
    return identifier, word_normalized


def is_productive_sahen_verb(mrph_dict_l):
    last = mrph_dict_l[-1]
    prev = mrph_dict_l[-2]
    return (
        last["genkei"] in {"する", "為る"}
        and last["hinsi"] == "動詞"
        and last["katuyou1"] in {"サ変動詞", "サ行変格"}
        and prev["hinsi"] in INDEPENDENT_MRPH
    )


def normalize_experimental_compatibility(word_normalized):
    return EXPERIMENTAL_NORMALIZATION_MAP.get(word_normalized, word_normalized)


def normalize_contextless_experimental_fragment(word, pos_tag, word_normalized, pos_tag_flag):
    if pos_tag == "v" and not pos_tag_flag and word in EXPERIMENTAL_CONTEXTLESS_VERB_MAP:
        return EXPERIMENTAL_CONTEXTLESS_VERB_MAP[word], True
    if pos_tag == "v" and not pos_tag_flag and word.endswith("さ") and len(word) > 1:
        return word[:-1] + "する", True
    return word_normalized, pos_tag_flag


def resolve_head_noun_last_index(mrph_dict_l):
    last_index = len(mrph_dict_l) - 1
    while last_index >= 1:
        mrph_item = mrph_dict_l[last_index]
        prev_item = mrph_dict_l[last_index - 1]
        trailing_key = mrph_item["genkei"] or mrph_item["midasi"]
        if (
            mrph_item["hinsi"] == "名詞"
            and prev_item["hinsi"] == "名詞"
            and trailing_key in TRAILING_HEAD_NOUN_MODIFIERS
        ):
            last_index -= 1
            continue
        if (
            mrph_item["hinsi"] == "接尾辞"
            and prev_item["hinsi"] in {"名詞", "接尾辞"}
            and (
                trailing_key in TRAILING_HEAD_NOUN_SUFFIXES
                or mrph_item["midasi"] in TRAILING_HEAD_NOUN_SUFFIX_SURFACES
            )
        ):
            last_index -= 1
            continue
        break
    return last_index


def recheck(word, pos_tag):
    juman_mrph_l = analyze_jumanpp(get_jumanpp_detail(), word)
    ranking_l = [[], [], [], [], []]
    for mrph_detail in juman_mrph_l:
        mrph_l = mrph_detail.midasi.split("\t")
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
                ranking_l[rank - 1].append(info_dict)
            except Exception:
                pass
    for mrph_dict_l in ranking_l:
        if mrph_dict_l == []:
            break
        word_normalized, pos_tag_flag = get_normalize_word(mrph_dict_l, pos_tag)
        if pos_tag_flag:
            return True, word_normalized
    return False, word


def get_normalize_word(mrph_dict_l, pos_tag):
    word_normalized = ""
    pos_tag_flag = False
    if pos_tag == "a":
        last_index = len(mrph_dict_l) - 1
        if (
            last_index >= 1
            and mrph_dict_l[last_index]["hinsi"] == "助動詞"
            and mrph_dict_l[last_index]["genkei"] in {"だ", "です"}
            and (
                "形容詞" in mrph_dict_l[last_index - 1]["hinsi"]
                or "形容詞" in mrph_dict_l[last_index - 1]["bunrui"]
                or "形状詞" in mrph_dict_l[last_index - 1]["hinsi"]
                or "形状詞" in mrph_dict_l[last_index - 1]["bunrui"]
            )
        ):
            last_index -= 1
        for index_mrph in range(last_index):
            mrph_item = mrph_dict_l[index_mrph]
            if mrph_item["hinsi"] == "名詞":
                if "/" in mrph_item["repname"]:
                    word_normalized += mrph_item["repname"].split("/")[0]
                else:
                    word_normalized += mrph_item["midasi"]
            else:
                word_normalized += mrph_item["midasi"]
        mrph_item = mrph_dict_l[last_index]
        if (
            "形容詞" in mrph_item["bunrui"]
            or "形容詞" in mrph_item["hinsi"]
            or "形状詞" in mrph_item["bunrui"]
            or "形状詞" in mrph_item["hinsi"]
        ):
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
            pos_tag_flag = True
        else:
            word_normalized += mrph_item["midasi"]
    elif pos_tag == "v":
        last_index = len(mrph_dict_l) - 1
        if (
            last_index >= 1
            and mrph_dict_l[last_index]["midasi"] in {"て", "で"}
            and "動詞" in mrph_dict_l[last_index - 1]["hinsi"]
        ):
            last_index -= 1
        for index_mrph in range(last_index):
            mrph_item = mrph_dict_l[index_mrph]
            if mrph_item["hinsi"] == "名詞":
                if "/" in mrph_item["repname"]:
                    word_normalized += mrph_item["repname"].split("/")[0]
                else:
                    word_normalized += mrph_item["midasi"]
            elif (
                mrph_item["midasi"] == "して"
                and mrph_item["hinsi"] == "接続詞"
                and word_normalized == ""
            ):
                continue
            elif (
                mrph_item["hinsi"] == "動詞"
                and mrph_item["genkei"] == "する"
                and word_normalized == ""
            ):
                continue
            else:
                word_normalized += mrph_item["midasi"]
        mrph_item = mrph_dict_l[last_index]
        if "動詞" in mrph_item["hinsi"] or "動詞" in mrph_item["bunrui"]:
            if "/" in mrph_item["repname"]:
                word_last = mrph_item["repname"].split("/")[0]
            else:
                word_last = mrph_item["genkei"]
            word_normalized += word_last
            word_normalized = normalize_experimental_compatibility(word_normalized)
            pos_tag_flag = True
        else:
            word_normalized += mrph_item["midasi"]
    elif pos_tag == "r":
        for index_mrph in range(len(mrph_dict_l) - 1):
            mrph_item = mrph_dict_l[index_mrph]
            if mrph_item["hinsi"] == "名詞":
                if "/" in mrph_item["repname"]:
                    word_normalized += mrph_item["repname"].split("/")[0]
                else:
                    word_normalized += mrph_item["midasi"]
            else:
                word_normalized += mrph_item["midasi"]
        mrph_item = mrph_dict_l[-1]
        if "副詞" in mrph_item["hinsi"] or "副詞" in mrph_item["bunrui"]:
            if "/" in mrph_item["repname"]:
                word_last = mrph_item["repname"].split("/")[0]
            else:
                word_last = mrph_item["genkei"]
            word_normalized += word_last
            pos_tag_flag = True
        else:
            word_normalized += mrph_item["midasi"]
    elif pos_tag == "n":
        last_index = resolve_head_noun_last_index(mrph_dict_l)
        for index_mrph in range(last_index):
            mrph_item = mrph_dict_l[index_mrph]
            if mrph_item["hinsi"] == "名詞":
                if "/" in mrph_item["repname"]:
                    word_normalized += mrph_item["repname"].split("/")[0]
                else:
                    word_normalized += mrph_item["midasi"]
            else:
                word_normalized += mrph_item["midasi"]
        mrph_item = mrph_dict_l[last_index]
        if "名詞" in mrph_item["hinsi"] or "名詞" in mrph_item["bunrui"]:
            if "/" in mrph_item["repname"]:
                word_normalized += mrph_item["repname"].split("/")[0]
            else:
                word_normalized += mrph_item["genkei"]
            pos_tag_flag = True
        else:
            if "/" in mrph_item["repname"]:
                word_normalized += mrph_item["repname"].split("/")[0]
            else:
                word_normalized += mrph_item["genkei"]
    return word_normalized, pos_tag_flag
