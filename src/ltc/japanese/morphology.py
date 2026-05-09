"""Japanese morphological processing with swappable backends.

Sudachi is the preferred default backend. Juman++ remains supported as a legacy
comparison path, and fugashi+UniDic is available as a MeCab-family route.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from functools import lru_cache

from jumanpp_safety import analyze_jumanpp
from ltc.japanese.backends import current_japanese_text_backend_name

ja_nounsetsubi = [
    "症",
    "酢",
    "度",
    "感",
    "性",
    "法",
    "語",
    "系",
    "率",
    "律",
    "史",
    "論",
    "学",
    "観",
    "器",
    "集",
    "説",
    "録",
    "書",
    "等",
    "者",
    "制",
    "座",
    "員",
    "体",
    "生",
    "帯",
    "量",
    "分",
    "数",
    "作用",
    "機",
    "器",
    "盤",
    "金",
    "種",
    "地",
    "場",
    "先",
    "軍",
    "業",
    "物",
    "中",
    "者",
    "権",
    "室",
    "線",
    "教",
    "丸",
    "界",
]
INDEPENDENT_MRPH = ["形容詞", "名詞", "動詞", "副詞"]
BLOCKED_NOUN_MERGE_BUNRUI = {"時相名詞", "副詞的名詞", "形式名詞", "数詞"}
BLOCKED_NOUN_MERGE_GENKEI = {"私", "誰", "何", "自分"}
SURFACE_PREFERRED_POS = {"名詞", "副詞", "形状詞", "連体詞"}
LEGACY_LEMMA_MAP = {
    "為る": "する",
    "成る": "なる",
    "有る": "ある",
    "居る": "いる",
    "出来る": "できる",
}
ADVERBIAL_NOUN_SURFACE_MAP = {
    "時々": "時々",
    "最近": "最近",
    "絶対": "絶対",
    "概ね": "概ね",
}
SHAPE_ADJECTIVE_NOUN_SURFACE_MAP = {
    "完璧": "完璧",
}
THIRD_NOUN_SUFFIX_MERGE_GENKEI = {"側"}
NOUN_LIKE_SUFFIX_BUNRUI = {"名詞的", "名詞的接尾辞"}
SHAPE_ADJECTIVE_SUFFIX_BUNRUI = {"形状詞的"}


@dataclass
class JapaneseRawMorph:
    midasi: str
    hinsi: str
    bunrui: str
    genkei: str
    katuyou1: str = ""
    katuyou2: str = ""
    repname: str = ""


def normalize_japanese_sentence_for_morphology(sentence):
    return sentence.replace("\u3000", " ").replace("\r", " ").replace("\n", " ")


def should_merge_adjacent_nouns(previous_bunrui, previous_genkei, current_mrph):
    if previous_bunrui in BLOCKED_NOUN_MERGE_BUNRUI:
        return False
    if current_mrph.bunrui in BLOCKED_NOUN_MERGE_BUNRUI:
        return False
    if previous_genkei in BLOCKED_NOUN_MERGE_GENKEI:
        return False
    if current_mrph.genkei in BLOCKED_NOUN_MERGE_GENKEI:
        return False
    if (
        previous_genkei.isascii()
        and previous_genkei.upper() == previous_genkei
        and current_mrph.genkei == "対策"
    ):
        return False
    return True


def normalize_backend_base_form(surface, base_form, pos_major):
    if pos_major in SURFACE_PREFERRED_POS:
        return surface
    normalized = base_form or surface
    return LEGACY_LEMMA_MAP.get(normalized, normalized)


def is_suru_like(mrph):
    return mrph.hinsi == "動詞" and normalize_backend_base_form(
        mrph.midasi,
        mrph.genkei,
        mrph.hinsi,
    ) == "する"


def is_copular_auxiliary(mrph):
    if mrph.hinsi != "助動詞":
        return False
    normalized = normalize_backend_base_form(mrph.midasi, mrph.genkei, mrph.hinsi)
    return normalized in {"だ", "です"}


def make_raw_morph(midasi, hinsi, bunrui, genkei, katuyou1="", katuyou2="", repname=""):
    return JapaneseRawMorph(
        midasi=midasi,
        hinsi=hinsi,
        bunrui=bunrui,
        genkei=genkei,
        katuyou1=katuyou1,
        katuyou2=katuyou2,
        repname=repname or genkei,
    )


def normalize_suffix_output_pos(bunrui):
    if bunrui in NOUN_LIKE_SUFFIX_BUNRUI:
        return "名詞"
    if bunrui in SHAPE_ADJECTIVE_SUFFIX_BUNRUI:
        return "形状詞"
    if bunrui.endswith("接尾辞"):
        return bunrui[:-3]
    return bunrui


def apply_backend_compatibility(raw_morphs):
    compatible = []
    index = 0
    while index < len(raw_morphs):
        window = raw_morphs[index : index + 4]
        if [mrph.midasi for mrph in window] == ["もし", "か", "し", "たら"]:
            compatible.append(
                make_raw_morph(
                    midasi="もしかしたら",
                    hinsi="副詞",
                    bunrui="*",
                    genkei="もしかしたら",
                    repname="もしかしたら",
                )
            )
            index += 4
            continue
        window = raw_morphs[index : index + 2]
        if [mrph.midasi for mrph in window] == ["常", "に"]:
            compatible.append(
                make_raw_morph(
                    midasi="常に",
                    hinsi="副詞",
                    bunrui="*",
                    genkei="常に",
                    repname="常に",
                )
            )
            index += 2
            continue
        if (
            len(window) == 2
            and window[0].midasi == "つまら"
            and window[0].genkei in {"詰まる", "つまる"}
            and window[1].midasi == "なく"
            and window[1].genkei == "ない"
        ):
            compatible.append(
                make_raw_morph(
                    midasi="つまらなく",
                    hinsi="形容詞",
                    bunrui="*",
                    genkei="つまらない",
                    repname="つまらない",
                )
            )
            index += 2
            continue

        mrph = raw_morphs[index]
        if mrph.midasi == "また":
            compatible.append(
                make_raw_morph(
                    midasi="また",
                    hinsi="副詞",
                    bunrui="*",
                    genkei="また",
                    katuyou1=mrph.katuyou1,
                    katuyou2=mrph.katuyou2,
                    repname="また",
                )
            )
            index += 1
            continue
        if mrph.hinsi == "名詞" and mrph.midasi in ADVERBIAL_NOUN_SURFACE_MAP:
            normalized = ADVERBIAL_NOUN_SURFACE_MAP[mrph.midasi]
            compatible.append(
                make_raw_morph(
                    midasi=normalized,
                    hinsi="副詞",
                    bunrui="*",
                    genkei=normalized,
                    katuyou1=mrph.katuyou1,
                    katuyou2=mrph.katuyou2,
                    repname=normalized,
                )
            )
        elif mrph.hinsi == "名詞" and mrph.midasi in SHAPE_ADJECTIVE_NOUN_SURFACE_MAP:
            normalized = SHAPE_ADJECTIVE_NOUN_SURFACE_MAP[mrph.midasi]
            compatible.append(
                make_raw_morph(
                    midasi=normalized,
                    hinsi="形状詞",
                    bunrui="*",
                    genkei=normalized,
                    katuyou1=mrph.katuyou1,
                    katuyou2=mrph.katuyou2,
                    repname=normalized,
                )
            )
        else:
            compatible.append(mrph)
        index += 1
    return compatible


def make_space_raw_morph():
    return JapaneseRawMorph(
        midasi=" ",
        hinsi="特殊",
        bunrui="空白",
        genkei=" ",
        repname=" ",
    )


@lru_cache(maxsize=1)
def get_jumanpp():
    from pyknp import Juman

    return Juman(timeout=300, jumanpp=True)


def convert_juman_mrph_to_raw(mrph):
    return JapaneseRawMorph(
        midasi=mrph.midasi,
        hinsi=mrph.hinsi,
        bunrui=mrph.bunrui,
        genkei=mrph.genkei,
        katuyou1=mrph.katuyou1,
        katuyou2=mrph.katuyou2,
        repname=getattr(mrph, "repname", "") or mrph.genkei,
    )


def parse_juman_raw(sentence):
    jumanpp = get_jumanpp()
    sentence = normalize_japanese_sentence_for_morphology(sentence)
    try:
        mrph_l = analyze_jumanpp(jumanpp, sentence)
    except Exception as error:
        print("jumanpp error", error, file=sys.stderr)
        print("sentence", sentence, file=sys.stderr)
        fallback_sentence = sentence.replace(" ", "")
        if fallback_sentence == sentence:
            return []
        try:
            mrph_l = analyze_jumanpp(jumanpp, fallback_sentence)
        except Exception as fallback_error:
            print("jumanpp fallback error", fallback_error, file=sys.stderr)
            print("fallback_sentence", fallback_sentence, file=sys.stderr)
            return []
    return [convert_juman_mrph_to_raw(mrph) for mrph in mrph_l]


def map_backend_pos_to_japanese(pos_major, pos_minor):
    if pos_major == "代名詞":
        return "名詞", "代名詞"
    if pos_major == "補助記号":
        return "特殊", pos_minor or "補助記号"
    if pos_major == "空白":
        return "特殊", "空白"
    return pos_major, pos_minor


@lru_cache(maxsize=1)
def get_fugashi_tagger():
    from fugashi import Tagger

    return Tagger()


def parse_fugashi_segment(segment):
    tagger = get_fugashi_tagger()
    raw_morphs = []
    for word in tagger(segment):
        feature = word.feature
        pos_major, pos_minor = map_backend_pos_to_japanese(
            getattr(feature, "pos1", "") or "",
            getattr(feature, "pos2", "") or "",
        )
        lemma = getattr(feature, "lemma", None) or word.surface
        base_form = normalize_backend_base_form(word.surface, lemma, pos_major)
        raw_morphs.append(
            JapaneseRawMorph(
                midasi=word.surface,
                hinsi=pos_major,
                bunrui=pos_minor,
                genkei=base_form,
                katuyou1=getattr(feature, "cType", "") or "",
                katuyou2=getattr(feature, "cForm", "") or "",
                repname=base_form,
            )
        )
    return raw_morphs


@lru_cache(maxsize=4)
def get_sudachi_tokenizer(split_mode_name):
    from sudachipy import Dictionary, SplitMode

    mode_lookup = {
        "sudachi_a": SplitMode.A,
        "sudachi_b": SplitMode.B,
        "sudachi_c": SplitMode.C,
    }
    return Dictionary().create(), mode_lookup[split_mode_name]


def parse_sudachi_segment(segment, split_mode_name):
    tokenizer, split_mode = get_sudachi_tokenizer(split_mode_name)
    raw_morphs = []
    for morpheme in tokenizer.tokenize(segment, split_mode):
        pos = morpheme.part_of_speech()
        pos_major, pos_minor = map_backend_pos_to_japanese(
            pos[0] if len(pos) > 0 else "",
            pos[1] if len(pos) > 1 else "",
        )
        dictionary_form = morpheme.dictionary_form() or morpheme.surface()
        normalized_form = morpheme.normalized_form() or dictionary_form
        sudachi_base = (
            normalized_form if pos_major not in SURFACE_PREFERRED_POS else dictionary_form
        )
        base_form = normalize_backend_base_form(
            morpheme.surface(),
            sudachi_base,
            pos_major,
        )
        raw_morphs.append(
            JapaneseRawMorph(
                midasi=morpheme.surface(),
                hinsi=pos_major,
                bunrui=pos_minor,
                genkei=base_form,
                katuyou1=pos[4] if len(pos) > 4 else "",
                katuyou2=pos[5] if len(pos) > 5 else "",
                repname=base_form,
            )
        )
    return raw_morphs


def parse_segmented_raw(sentence, segment_parser):
    sentence = normalize_japanese_sentence_for_morphology(sentence)
    raw_morphs = []
    for part in re.split(r"( )", sentence):
        if not part:
            continue
        if part == " ":
            raw_morphs.append(make_space_raw_morph())
            continue
        raw_morphs.extend(segment_parser(part))
    return raw_morphs


def get_japanese_raw_morphemes(sentence, backend_name=None):
    backend_name = backend_name or current_japanese_text_backend_name()
    if backend_name == "jumanpp":
        return parse_juman_raw(sentence)
    if backend_name == "fugashi_unidic":
        return apply_backend_compatibility(
            parse_segmented_raw(sentence, parse_fugashi_segment)
        )
    if backend_name in {"sudachi_a", "sudachi_b", "sudachi_c"}:
        return apply_backend_compatibility(
            parse_segmented_raw(
                sentence,
                lambda part: parse_sudachi_segment(part, backend_name),
            )
        )
    raise RuntimeError(f"unsupported Japanese text backend: {backend_name}")


def raw_morphemes_to_dicts(raw_morphs):
    return [
        {
            "midasi": mrph.midasi,
            "repname": mrph.repname,
            "hinsi": mrph.hinsi,
            "bunrui": mrph.bunrui,
            "katuyou1": mrph.katuyou1,
            "genkei": mrph.genkei,
        }
        for mrph in raw_morphs
        if not (mrph.hinsi == "特殊" and mrph.bunrui == "空白")
    ]


def combine_raw_morphemes(raw_mrph_l, backend_name=None):
    backend_name = backend_name or current_japanese_text_backend_name()
    tokenized = []
    mrph_out = []
    bunrui_out = []
    genkei_out = []
    noun_piece_count_out = []
    last_katuyou2 = ""
    boundary_since_last_token = False

    for mrph in raw_mrph_l:
        if mrph.hinsi == "特殊" and mrph.bunrui == "空白":
            last_katuyou2 = ""
            boundary_since_last_token = True
            continue
        if len(mrph_out) == 0 or len(tokenized) == 0:
            tokenized.append(mrph.midasi)
            mrph_out.append(mrph.hinsi)
            bunrui_out.append(mrph.bunrui)
            genkei_out.append(mrph.genkei)
            noun_piece_count_out.append(1 if mrph.hinsi == "名詞" else 0)
            last_katuyou2 = mrph.katuyou2
            boundary_since_last_token = False
        elif mrph.midasi in ja_nounsetsubi and (
            mrph_out[-1] == "名詞" or last_katuyou2 == "語幹"
        ):
            tokenized[-1] += mrph.midasi
            bunrui_out[-1] = mrph.bunrui
            genkei_out[-1] = mrph.genkei
            if noun_piece_count_out[-1] > 0:
                noun_piece_count_out[-1] += 1
            last_katuyou2 = ""
            boundary_since_last_token = False
        elif mrph.hinsi == "接尾辞" and mrph.bunrui != "動詞性接尾辞":
            tokenized[-1] += mrph.midasi
            mrph_out[-1] = normalize_suffix_output_pos(mrph.bunrui)
            bunrui_out[-1] = mrph.bunrui
            genkei_out[-1] = mrph.genkei
            last_katuyou2 = ""
            boundary_since_last_token = False
        elif is_copular_auxiliary(mrph) and mrph_out[-1] in {"形容詞", "形状詞"}:
            tokenized[-1] += mrph.midasi
            last_katuyou2 = mrph.katuyou2
            boundary_since_last_token = False
        elif is_suru_like(mrph) and mrph.hinsi == "動詞" and mrph_out[-1] in INDEPENDENT_MRPH:
            tokenized[-1] += mrph.midasi
            mrph_out[-1] = "動詞"
            bunrui_out[-1] = mrph.bunrui
            genkei_out[-1] = "する"
            noun_piece_count_out[-1] = 0
            last_katuyou2 = mrph.katuyou2
            boundary_since_last_token = False
        elif mrph.hinsi in {"名詞", "形状詞", "形容詞"} and mrph_out[-1] == "接頭辞":
            tokenized[-1] += mrph.midasi
            mrph_out[-1] = mrph.hinsi
            bunrui_out[-1] = mrph.bunrui
            genkei_out[-1] = mrph.genkei
            noun_piece_count_out[-1] = (
                max(1, noun_piece_count_out[-1] + 1) if mrph.hinsi == "名詞" else 0
            )
            last_katuyou2 = mrph.katuyou2
            boundary_since_last_token = False
        elif (
            mrph.hinsi == "名詞"
            and mrph_out[-1] == "名詞"
            and not boundary_since_last_token
            and (
                backend_name == "jumanpp"
                or noun_piece_count_out[-1] < 2
                or (
                    noun_piece_count_out[-1] == 2
                    and mrph.genkei in THIRD_NOUN_SUFFIX_MERGE_GENKEI
                )
            )
            and should_merge_adjacent_nouns(
                bunrui_out[-1], genkei_out[-1], mrph
            )
        ):
            tokenized[-1] += mrph.midasi
            bunrui_out[-1] = mrph.bunrui
            genkei_out[-1] = mrph.genkei
            noun_piece_count_out[-1] += 1
            last_katuyou2 = mrph.katuyou2
            boundary_since_last_token = False
        elif mrph.hinsi == "動詞" and mrph_out[-1] == "動詞":
            tokenized[-1] += mrph.midasi
            bunrui_out[-1] = mrph.bunrui
            genkei_out[-1] = mrph.genkei
            noun_piece_count_out[-1] = 0
            last_katuyou2 = mrph.katuyou2
            boundary_since_last_token = False
        else:
            tokenized.append(mrph.midasi)
            mrph_out.append(mrph.hinsi)
            bunrui_out.append(mrph.bunrui)
            genkei_out.append(mrph.genkei)
            noun_piece_count_out.append(1 if mrph.hinsi == "名詞" else 0)
            last_katuyou2 = mrph.katuyou2
            boundary_since_last_token = False

    for index, con in enumerate(mrph_out):
        if con in {"形容詞", "形状詞"}:
            mrph_out[index] = "a"
        elif con == "名詞":
            mrph_out[index] = "n"
        elif con == "動詞":
            mrph_out[index] = "v"
        elif con == "副詞":
            mrph_out[index] = "r"
        else:
            mrph_out[index] = ""
    return tokenized, mrph_out


def ja_juman_morphological(sentence):
    return combine_raw_morphemes(parse_juman_raw(sentence), backend_name="jumanpp")


def ja_juman_morphological_batch(sentences):
    tokenized = []
    mrph = []
    for sentence in sentences:
        tokenized_sentence, mrph_sentence = ja_juman_morphological(sentence)
        tokenized.append(tokenized_sentence)
        mrph.append(mrph_sentence)
    return tokenized, mrph


def ja_morphological(sentence):
    backend_name = current_japanese_text_backend_name()
    return combine_raw_morphemes(
        get_japanese_raw_morphemes(sentence, backend_name=backend_name),
        backend_name=backend_name,
    )


def ja_morphological_batch(sentences):
    tokenized = []
    mrph = []
    for sentence in sentences:
        tokenized_sentence, mrph_sentence = ja_morphological(sentence)
        tokenized.append(tokenized_sentence)
        mrph.append(mrph_sentence)
    return tokenized, mrph
