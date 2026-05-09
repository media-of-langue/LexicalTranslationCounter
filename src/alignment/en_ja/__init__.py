import itertools
import sys
import os
import re
import torch
import csv
import numpy as np

base = os.path.dirname(os.path.abspath(__file__))
path_exception = os.path.normpath(os.path.join(base, "./exceptions.csv"))

from morphological.en_morphological import en_morphological, en_morphological_batch
from ltc.japanese.backends import (
    current_japanese_text_backend_name,
    runtime_check_japanese_text_backend,
)
from ltc.japanese.morphology import ja_morphological, ja_morphological_batch

import time

from normalizer.en_normalizer import en_normalizer
from ltc.japanese.normalization import ja_normalizer
from ltc.backends.alignment.awesome_utils import (
    build_awesome_input_ids_and_subword_map,
    check_awesome_model_runtime,
    ensure_production_model,
    load_awesome_model_and_tokenizer,
    resolve_awesome_model_selection,
    warn_on_smoke_model,
)

exceptions = list(csv.reader(open(path_exception, "r"), delimiter=","))

MODEL_SELECTION = resolve_awesome_model_selection(
    __file__,
    "awesome_model_without_co",
    pair_name="en_ja",
)
MODEL_SPEC = MODEL_SELECTION.model_spec

device = torch.device("cuda:0") if torch.cuda.is_available() else torch.device("cpu")
model = None
tokenizer = None
_model_profile_warned = False

max_word_len = 3

part_of_speach_tag = {"noun": "n", "verb": "v", "adj": "a", "adverb": "r"}
part_of_speach_tag_rev = {"n": "noun", "v": "verb", "a": "adj", "r": "adverb"}

src_except_l = ["not", "n't"]
trg_except_l = ["ない", "なかろう", "なく", "なかっ", "なければ"]
be_l = ["is", "are", "was", "were", "am", "be", "been", "being", "'s", "'re", "'m"]
src_relative_index_except = 1
trg_relative_index_except = -1

# ignore be + verb

src_word_sep = " "
trg_word_sep = ""

# params
align_layer = 8
threshold = 1e-3


def parse_minimum_alignment_confidence():
    value = os.environ.get("LTC_EN_JA_MIN_ALIGNMENT_CONFIDENCE", "0.2")
    try:
        parsed = float(value)
    except ValueError:
        return 0.2
    return max(0.0, parsed)


minimum_alignment_confidence = parse_minimum_alignment_confidence()
honorific_variant_suffixes = ("さん", "様")
abstract_adjective_nominal_suffixes = ("性", "さ")
source_noun_compound_merge_min_score = 0.95
competing_source_pair_strong_confidence = 0.95
competing_source_pair_weak_confidence = 0.6
competing_source_pair_min_margin = 0.3
source_lexicalized_noun_compounds = {
    (("living", "room"), "リビング"),
}

always_suppress_source_verbs = {"be", "'re", "'s", "'m"}
support_target_verbs = {"なる", "鳴る"}
support_target_source_verbs = {"become", "get", "hide"}
low_value_direct_pairs = {
    ("get", "得る"),
    ("get", "得"),
    ("get", "経過する"),
    ("get", "程度経過する"),
}
always_suppress_source_nouns = {"%", "one"}
low_value_direct_pairs_by_pos = {
    "n": {
        ("thing", "もの"),
        ("thing", "こと"),
        ("case", "わけ"),
        ("company", "社"),
        ("hand every time", "毎回手"),
        ("hobby", "対策"),
        ("youtube", "ソフトバンク関連"),
        ("month", "文賢"),
        ("post", "サービス"),
        ("fan", "芸能人"),
        ("real fan", "プチ芸能人"),
        ("article", "今回"),
        ("small portion", "大半"),
    },
    "a": {
        ("least", "少ない"),
    },
    "v": {
        ("stream", "使う"),
        ("please", "思う"),
        ("look", "感じる"),
        ("come", "取る"),
        ("do", "なれる"),
        ("do", "おこう"),
        ("duplicate", "なる"),
        ("have", "あり"),
        ("have", "き"),
        ("use", "疲れる"),
        ("have", "見る"),
        ("find", "見る"),
        ("make", "き"),
        ("base", "記載する"),
        ("set", "すすめする"),
        ("set", "すすめし"),
        ("say", "言い切る"),
        ("feel", "感じた事"),
        ("notice", "見る"),
        ("stop", "なる"),
        ("want", "考える"),
    },
    "r": {
        ("later", "最近"),
        ("personally", "実際"),
        ("ago", "最近"),
    },
}


def parse_alignment_backend_name():
    value = os.environ.get("LTC_EN_JA_ALIGNMENT_BACKEND", "awesome").strip().lower()
    if value not in {"awesome", "simalign"}:
        raise ValueError(
            "LTC_EN_JA_ALIGNMENT_BACKEND must be one of: awesome, simalign"
        )
    return value


def parse_simalign_method():
    value = os.environ.get("LTC_EN_JA_SIMALIGN_METHOD", "mwmf").strip().lower()
    if value not in {"inter", "mwmf", "itermax"}:
        raise ValueError(
            "LTC_EN_JA_SIMALIGN_METHOD must be one of: inter, mwmf, itermax"
        )
    return value


def parse_simalign_model_spec():
    return os.environ.get("LTC_EN_JA_SIMALIGN_MODEL", "bert").strip() or "bert"


alignment_backend_name = parse_alignment_backend_name()
simalign_method = parse_simalign_method()
simalign_model_spec = parse_simalign_model_spec()
simalign_aligner = None


def get_model_and_tokenizer():
    global model, tokenizer, _model_profile_warned
    ensure_production_model(
        MODEL_SELECTION, backend_name="alignment.en_ja", pair_name="en_ja"
    )
    if not _model_profile_warned:
        warn_on_smoke_model(MODEL_SELECTION, backend_name="alignment.en_ja")
        _model_profile_warned = True
    if model is None or tokenizer is None:
        model_loaded, tokenizer_loaded = load_awesome_model_and_tokenizer(MODEL_SPEC)
        model = model_loaded.to(device)
        tokenizer = tokenizer_loaded
    return model, tokenizer


def get_simalign_aligner():
    global simalign_aligner
    if simalign_aligner is None:
        from simalign import SentenceAligner

        matching_methods = {
            "inter": "a",
            "mwmf": "m",
            "itermax": "i",
        }
        simalign_aligner = SentenceAligner(
            model=simalign_model_spec,
            token_type="bpe",
            matching_methods=matching_methods[simalign_method],
            device="cuda" if torch.cuda.is_available() else "cpu",
            layer=align_layer,
        )
    return simalign_aligner


def merge_aligned_index_pairs(align_subwords, sub2word_map_src, sub2word_map_tgt):
    index_pair_list = []
    for i_tmp, j_tmp in align_subwords:
        i = sub2word_map_src[i_tmp]
        j = sub2word_map_tgt[j_tmp]
        matching_pair_indexes = [
            index_pair_index
            for index_pair_index, index_pair in enumerate(index_pair_list)
            if i in index_pair[0] or j in index_pair[1]
        ]
        if not matching_pair_indexes:
            index_pair_list.append([{i}, {j}])
            continue

        primary_index = matching_pair_indexes[0]
        index_pair_list[primary_index][0].add(i)
        index_pair_list[primary_index][1].add(j)
        for merge_index in reversed(matching_pair_indexes[1:]):
            index_pair_list[primary_index][0].update(index_pair_list[merge_index][0])
            index_pair_list[primary_index][1].update(index_pair_list[merge_index][1])
            del index_pair_list[merge_index]
    return index_pair_list


def collect_src_ignore_indexes(sent_src, pos_src):
    index_src_ignore = set()
    sent_src_lower = [word.lower() for word in sent_src]
    for word_src_except in src_except_l:
        for index_src, word_tmp in enumerate(sent_src_lower):
            if word_tmp == word_src_except and index_src + src_relative_index_except < len(
                sent_src
            ):
                index_src_ignore.add(index_src + src_relative_index_except)

    # Ignore auxiliary/copula "be" in patterns like "be not ..." or "be + verb".
    for index_src, word_tmp in enumerate(sent_src_lower):
        if word_tmp not in be_l:
            continue
        if index_src + 1 < len(sent_src):
            next_word = sent_src_lower[index_src + 1]
            next_pos = pos_src[index_src + 1]
            if next_pos in {"v", "a"} or next_word in src_except_l:
                index_src_ignore.add(index_src)
    return index_src_ignore


def collect_trg_ignore_indexes(sent_tgt):
    index_trg_ignore = set()
    for word_trg_except in trg_except_l:
        if word_trg_except in sent_tgt:
            for index_trg, word_tmp in enumerate(sent_tgt):
                if word_tmp == word_trg_except and index_trg + trg_relative_index_except >= 0:
                    index_trg_ignore.add(index_trg + trg_relative_index_except)
    return index_trg_ignore


def trim_indexes_to_content(indexes_sorted, pos_tags):
    independent_positions = [
        index_position
        for index_position, token_index in enumerate(indexes_sorted)
        if pos_tags[token_index] != ""
    ]
    if not independent_positions:
        return indexes_sorted
    return indexes_sorted[
        independent_positions[0] : independent_positions[-1] + 1
    ]


def collapse_honorific_target_variants(indexes_sorted, sent_tgt, pos_trg):
    if len(indexes_sorted) <= 1:
        return indexes_sorted
    token_lookup = {index: sent_tgt[index] for index in indexes_sorted}
    surface_lookup = {token_lookup[index] for index in indexes_sorted if pos_trg[index] == "n"}
    collapsed = []
    for target_index in indexes_sorted:
        if pos_trg[target_index] != "n":
            collapsed.append(target_index)
            continue
        target_surface = token_lookup[target_index]
        if any(
            target_surface.endswith(suffix)
            and target_surface[: -len(suffix)] in surface_lookup
            for suffix in honorific_variant_suffixes
        ):
            continue
        collapsed.append(target_index)
    return collapsed


def collect_alignment_scores(
    src_indexes_sorted,
    trg_indexes_sorted,
    align_subwords,
    sub2word_map_src,
    sub2word_map_tgt,
    softmax_srctrg,
    softmax_trgsrc,
):
    if align_subwords is None or softmax_srctrg is None or softmax_trgsrc is None:
        return []

    src_index_set = set(src_indexes_sorted)
    trg_index_set = set(trg_indexes_sorted)
    scores = []
    for index_src_subword, index_trg_subword in align_subwords.tolist():
        if (
            sub2word_map_src[index_src_subword] in src_index_set
            and sub2word_map_tgt[index_trg_subword] in trg_index_set
        ):
            scores.append(
                min(
                    float(softmax_srctrg[index_src_subword, index_trg_subword]),
                    float(softmax_trgsrc[index_src_subword, index_trg_subword]),
                )
            )
    return scores


def describe_token_sequence(tokens, pos_tags):
    return [
        {"index": index, "text": token, "pos_tag": pos_tags[index]}
        for index, token in enumerate(tokens)
    ]


def collect_top_target_candidates(
    sent_src,
    pos_src,
    sent_tgt,
    pos_tgt,
    sub2word_map_src,
    sub2word_map_tgt,
    softmax_srctrg,
    top_k=3,
):
    payload = []
    for src_index, (src_token, src_pos_tag) in enumerate(zip(sent_src, pos_src)):
        if src_pos_tag == "":
            continue
        subword_indexes = [
            subword_index
            for subword_index, word_index in enumerate(sub2word_map_src)
            if word_index == src_index
        ]
        candidate_scores = {}
        for src_subword_index in subword_indexes:
            for tgt_subword_index, tgt_word_index in enumerate(sub2word_map_tgt):
                candidate_scores[tgt_word_index] = max(
                    candidate_scores.get(tgt_word_index, 0.0),
                    float(softmax_srctrg[src_subword_index, tgt_subword_index]),
                )
        candidates = sorted(
            candidate_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:top_k]
        payload.append(
            {
                "source_index": src_index,
                "source_token": src_token,
                "source_pos_tag": src_pos_tag,
                "candidates": [
                    {
                        "target_index": tgt_word_index,
                        "target_token": sent_tgt[tgt_word_index],
                        "target_pos_tag": pos_tgt[tgt_word_index],
                        "score": score,
                    }
                    for tgt_word_index, score in candidates
                ],
            }
        )
    return payload


def collect_top_target_candidates_from_matrix(
    sent_src,
    pos_src,
    sent_tgt,
    pos_tgt,
    src_to_matrix_index,
    tgt_to_matrix_index,
    score_matrix,
    top_k=3,
):
    payload = []
    for src_index, (src_token, src_pos_tag) in enumerate(zip(sent_src, pos_src)):
        if src_pos_tag == "":
            continue
        matrix_indexes = src_to_matrix_index.get(src_index, [])
        candidate_scores = {}
        for src_matrix_index in matrix_indexes:
            for tgt_index, tgt_matrix_indexes in tgt_to_matrix_index.items():
                for tgt_matrix_index in tgt_matrix_indexes:
                    candidate_scores[tgt_index] = max(
                        candidate_scores.get(tgt_index, 0.0),
                        float(score_matrix[src_matrix_index, tgt_matrix_index]),
                    )
        candidates = sorted(
            candidate_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:top_k]
        payload.append(
            {
                "source_index": src_index,
                "source_token": src_token,
                "source_pos_tag": src_pos_tag,
                "candidates": [
                    {
                        "target_index": tgt_index,
                        "target_token": sent_tgt[tgt_index],
                        "target_pos_tag": pos_tgt[tgt_index],
                        "score": score,
                    }
                    for tgt_index, score in candidates
                ],
            }
        )
    return payload


def collect_best_target_for_source_word(
    source_index,
    sub2word_map_src,
    sub2word_map_tgt,
    softmax_srctrg,
):
    if softmax_srctrg is None:
        return None, 0.0
    candidate_scores = {}
    for src_subword_index, src_word_index in enumerate(sub2word_map_src):
        if src_word_index != source_index:
            continue
        for tgt_subword_index, tgt_word_index in enumerate(sub2word_map_tgt):
            candidate_scores[tgt_word_index] = max(
                candidate_scores.get(tgt_word_index, 0.0),
                float(softmax_srctrg[src_subword_index, tgt_subword_index]),
            )
    if not candidate_scores:
        return None, 0.0
    return max(candidate_scores.items(), key=lambda item: item[1])


def maybe_expand_source_noun_compound(
    src_indexes_sorted,
    trg_indexes_sorted,
    sent_src,
    pos_src,
    sub2word_map_src,
    sub2word_map_tgt,
    softmax_srctrg,
):
    if softmax_srctrg is None or len(trg_indexes_sorted) != 1 or not src_indexes_sorted:
        return src_indexes_sorted
    if any(pos_src[src_index] != "n" for src_index in src_indexes_sorted):
        return src_indexes_sorted

    target_index = trg_indexes_sorted[0]
    expanded = list(src_indexes_sorted)

    left_index = expanded[0] - 1
    while left_index >= 0 and left_index + 1 == expanded[0]:
        if pos_src[left_index] != "n":
            break
        best_target_index, best_score = collect_best_target_for_source_word(
            left_index,
            sub2word_map_src,
            sub2word_map_tgt,
            softmax_srctrg,
        )
        if (
            best_target_index != target_index
            or best_score < source_noun_compound_merge_min_score
        ):
            break
        expanded.insert(0, left_index)
        left_index -= 1

    right_index = expanded[-1] + 1
    while right_index < len(sent_src) and right_index == expanded[-1] + 1:
        if pos_src[right_index] != "n":
            break
        best_target_index, best_score = collect_best_target_for_source_word(
            right_index,
            sub2word_map_src,
            sub2word_map_tgt,
            softmax_srctrg,
        )
        if (
            best_target_index != target_index
            or best_score < source_noun_compound_merge_min_score
        ):
            break
        expanded.append(right_index)
        right_index += 1

    return expanded


def normalize_source_noun_for_compound(surface):
    normalized = en_normalizer(surface, "n", {}, test=True)
    return normalized.lower() if isinstance(normalized, str) else ""


def maybe_expand_source_lexicalized_noun_compound(
    src_indexes_sorted,
    trg_indexes_sorted,
    sent_src,
    pos_src,
    sent_tgt,
):
    if len(src_indexes_sorted) != 1 or len(trg_indexes_sorted) != 1:
        return src_indexes_sorted
    source_index = src_indexes_sorted[0]
    target_index = trg_indexes_sorted[0]
    if pos_src[source_index] != "n":
        return src_indexes_sorted
    next_source_index = source_index + 1
    if next_source_index >= len(sent_src) or pos_src[next_source_index] != "n":
        return src_indexes_sorted
    first_normalized = normalize_source_noun_for_compound(sent_src[source_index])
    second_normalized = normalize_source_noun_for_compound(sent_src[next_source_index])
    target_surface = sent_tgt[target_index]
    for (compound_parts, target_token) in source_lexicalized_noun_compounds:
        if (
            first_normalized == compound_parts[0]
            and second_normalized == compound_parts[1]
            and target_surface == target_token
        ):
            return [source_index, next_source_index]
    return src_indexes_sorted


def convert_word_pairs_to_index_pair_list(word_pairs):
    return [({src_index}, {tgt_index}) for src_index, tgt_index in word_pairs]


def build_simalign_score_map(word_pairs, src_to_matrix_index, tgt_to_matrix_index, sim_matrix):
    score_map = {}
    for src_index, tgt_index in word_pairs:
        scores = []
        for src_matrix_index in src_to_matrix_index.get(src_index, []):
            for tgt_matrix_index in tgt_to_matrix_index.get(tgt_index, []):
                scores.append(float(sim_matrix[src_matrix_index, tgt_matrix_index]))
        if scores:
            score_map[(src_index, tgt_index)] = scores
    return score_map


def collect_content_pos_tags(pos_list):
    content_pos_tags = set()
    for pos_tag in pos_list:
        if not pos_tag:
            continue
        content_pos_tags.update(
            part for part in pos_tag.split("/") if part
        )
    return content_pos_tags


def target_tokens_look_like_abstract_adjective_nominalization(target_tokens):
    return any(
        token.endswith(suffix)
        for token in target_tokens
        for suffix in abstract_adjective_nominal_suffixes
    )


def content_pos_sets_are_compatible(
    src_content_pos_tags,
    trg_content_pos_tags,
    trg_words_list,
):
    if not src_content_pos_tags.isdisjoint(trg_content_pos_tags):
        return True
    if (
        src_content_pos_tags == {"a"}
        and trg_content_pos_tags == {"n"}
        and target_tokens_look_like_abstract_adjective_nominalization(trg_words_list)
    ):
        return True
    return False


def resolve_independent_output_pos_tags(src_pos_l, trg_pos_l, trg_word_l):
    shared_pos_tags = set()
    for src_pos_tag in src_pos_l:
        shared_pos_tags.update(part for part in src_pos_tag.split("/") if part)
    target_pos_tags = set()
    for trg_pos_tag in trg_pos_l:
        target_pos_tags.update(part for part in trg_pos_tag.split("/") if part)
    shared_pos_tags &= target_pos_tags
    if shared_pos_tags:
        return shared_pos_tags
    if (
        collect_content_pos_tags(src_pos_l) == {"a"}
        and collect_content_pos_tags(trg_pos_l) == {"n"}
        and target_tokens_look_like_abstract_adjective_nominalization(trg_word_l)
    ):
        return {"a"}
    return set()


def indexes_are_consecutive(indexes):
    if len(indexes) <= 1:
        return True
    return all(
        next_index == current_index + 1
        for current_index, next_index in zip(indexes, indexes[1:])
    )


def count_content_tokens(indexes, pos_tags):
    return sum(1 for index in indexes if pos_tags[index] != "")


def join_english_tokens_for_surface(tokens):
    surface = ""
    for token in tokens:
        if not surface:
            surface = token
            continue
        if token in {".", ",", ";", ":", "?", "!", ")"}:
            surface += token
        elif surface.endswith("("):
            surface += token
        else:
            surface += f" {token}"
    return surface


def build_alignment_lookup_text(tokens, pos_tags, separator):
    content_tokens = []
    for token, pos_tag in zip(tokens, pos_tags):
        if pos_tag == "":
            continue
        cleaned = re.sub(r"[()\[\]{}.,;:!?]+", " ", token)
        cleaned = " ".join(cleaned.split())
        if cleaned:
            content_tokens.append(cleaned)
    if content_tokens:
        return separator.join(content_tokens)
    return separator.join(tokens)


def describe_merged_index_pair(
    index_pair,
    sent_src,
    pos_src,
    sent_tgt,
    pos_trg,
    index_src_ignore,
    index_trg_ignore,
):
    src_indexes = sorted(index_pair[0])
    trg_indexes = sorted(index_pair[1])
    return {
        "source_indices": src_indexes,
        "source_tokens": [sent_src[index] for index in src_indexes],
        "source_pos_tags": [pos_src[index] for index in src_indexes],
        "target_indices": trg_indexes,
        "target_tokens": [sent_tgt[index] for index in trg_indexes],
        "target_pos_tags": [pos_trg[index] for index in trg_indexes],
        "ignored_by_source_rule": not index_pair[0].isdisjoint(index_src_ignore),
        "ignored_by_target_rule": not index_pair[1].isdisjoint(index_trg_ignore),
    }


def describe_postprocessed_alignment_group(word_pair):
    metadata = word_pair[4] if len(word_pair) > 4 else {}
    payload = {
        "source_pos_tags": list(word_pair[0]),
        "source_tokens": list(word_pair[1]),
        "target_pos_tags": list(word_pair[2]),
        "target_tokens": list(word_pair[3]),
    }
    if metadata:
        payload["source_indices"] = list(metadata.get("source_indices", []))
        payload["target_indices"] = list(metadata.get("target_indices", []))
        payload["best_alignment_score"] = metadata.get("best_alignment_score")
        payload["average_alignment_score"] = metadata.get("average_alignment_score")
        payload["alignment_evidence_count"] = metadata.get("alignment_evidence_count")
    return payload


def describe_final_alignment_item(item, test=False):
    pos_tag = item[0]
    src_id = item[1]
    src_word = item[2]
    tgt_id = item[3]
    tgt_word = item[4]
    metadata = item[5] if len(item) > 5 else {}
    payload = {
        "pos_tag": pos_tag,
        "source_id": src_id,
        "source_surface": src_word,
        "source_normalized": metadata.get("source_normalized")
        or en_normalizer(src_word, pos_tag, {}, test=True),
        "target_id": tgt_id,
        "target_surface": tgt_word,
        "target_normalized": metadata.get("target_normalized")
        or ja_normalizer(tgt_word, pos_tag, {}, test=True),
    }
    if metadata:
        payload["best_alignment_score"] = metadata.get("best_alignment_score")
        payload["average_alignment_score"] = metadata.get("average_alignment_score")
        payload["alignment_evidence_count"] = metadata.get("alignment_evidence_count")
    return payload


def runtime_check():
    runtime_check_japanese_text_backend()
    if alignment_backend_name == "awesome":
        check_awesome_model_runtime(MODEL_SPEC, backend_name="alignment.en_ja")
        ensure_production_model(
            MODEL_SELECTION, backend_name="alignment.en_ja", pair_name="en_ja"
        )
        return
    if alignment_backend_name == "simalign":
        get_simalign_aligner()
        return
    raise RuntimeError(f"unsupported en_ja alignment backend: {alignment_backend_name}")


def runtime_metadata():
    if alignment_backend_name == "simalign":
        return {
            "note": (
                f"experimental backend simalign:{simalign_method} "
                f"using model {simalign_model_spec}"
            ),
            "alignment_backend": "simalign",
            "simalign_method": simalign_method,
            "simalign_model": simalign_model_spec,
            "minimum_alignment_confidence": minimum_alignment_confidence,
        }
    return {
        "note": MODEL_SELECTION.note,
        "alignment_backend": "awesome",
        "japanese_text_backend": current_japanese_text_backend_name(),
        "model_spec": MODEL_SELECTION.model_spec,
        "model_profile": MODEL_SELECTION.profile,
        "production_ready": MODEL_SELECTION.production_ready,
        "resolution_source": MODEL_SELECTION.resolution_source,
        "registry_dir": MODEL_SELECTION.registry_dir,
        "model_metadata": MODEL_SELECTION.metadata,
        "minimum_alignment_confidence": minimum_alignment_confidence,
    }


def should_suppress_precision_verb_pair(
    source_normalized,
    target_normalized,
    target_surface,
):
    if source_normalized in always_suppress_source_verbs:
        return True
    if (
        source_normalized in support_target_source_verbs
        and target_normalized in support_target_verbs
    ):
        return True
    if (source_normalized, target_normalized) in low_value_direct_pairs:
        return True
    if target_surface in {"なって", "なる", "なり"} and source_normalized in {
        "be",
        "become",
        "get",
        "hide",
    }:
        return True
    return False


def should_suppress_low_value_pair(
    pos_tag,
    source_normalized,
    target_normalized,
):
    if pos_tag == "n" and source_normalized in always_suppress_source_nouns:
        return True
    return (source_normalized, target_normalized) in low_value_direct_pairs_by_pos.get(
        pos_tag, set()
    )


def should_suppress_competing_duplicate_source_pair(candidate, grouped_candidates):
    if candidate["pos_tag"] != "n":
        return False
    if " " in candidate["source_surface"].strip():
        return False
    average_alignment_score = candidate.get("average_alignment_score")
    if average_alignment_score is None:
        return False
    if average_alignment_score > competing_source_pair_weak_confidence:
        return False
    siblings = grouped_candidates.get(
        (candidate["pos_tag"], candidate["source_normalized"]), ()
    )
    competing_candidates = [
        sibling
        for sibling in siblings
        if sibling["target_normalized"] != candidate["target_normalized"]
        and sibling.get("average_alignment_score") is not None
    ]
    if not competing_candidates:
        return False
    strongest_competing_score = max(
        sibling["average_alignment_score"] for sibling in competing_candidates
    )
    return (
        strongest_competing_score >= competing_source_pair_strong_confidence
        and strongest_competing_score - average_alignment_score
        >= competing_source_pair_min_margin
    )


def awesome_alignment_preprocessing(sent_src, sent_tgt, tokenizer):
    ids_src, sub2word_map_src = build_awesome_input_ids_and_subword_map(
        tokenizer, sent_src
    )
    ids_tgt, sub2word_map_tgt = build_awesome_input_ids_and_subword_map(
        tokenizer, sent_tgt
    )

    return ids_src, ids_tgt, sub2word_map_src, sub2word_map_tgt


def build_word_to_subword_index_map(word_tokens):
    mapping = {}
    index = 0
    for word_index, token_list in enumerate(word_tokens):
        mapping[word_index] = list(range(index, index + len(token_list)))
        index += len(token_list)
    return mapping


def compute_simalign_word_pairs_and_scores(sent_src, sent_tgt):
    aligner = get_simalign_aligner()
    src_word_tokens = [aligner.embed_loader.tokenizer.tokenize(word) for word in sent_src]
    tgt_word_tokens = [aligner.embed_loader.tokenizer.tokenize(word) for word in sent_tgt]
    src_bpe_to_word = [word_index for word_index, token_list in enumerate(src_word_tokens) for _ in token_list]
    tgt_bpe_to_word = [word_index for word_index, token_list in enumerate(tgt_word_tokens) for _ in token_list]
    src_word_to_bpe = build_word_to_subword_index_map(src_word_tokens)
    tgt_word_to_bpe = build_word_to_subword_index_map(tgt_word_tokens)

    vectors = aligner.embed_loader.get_embed_list([sent_src, sent_tgt]).cpu().detach().numpy()
    src_bpe_count = len(src_bpe_to_word)
    tgt_bpe_count = len(tgt_bpe_to_word)
    src_vectors = vectors[0, :src_bpe_count]
    tgt_vectors = vectors[1, :tgt_bpe_count]

    sim_matrix = aligner.get_similarity(src_vectors, tgt_vectors)
    sim_matrix = aligner.apply_distortion(sim_matrix, aligner.distortion)

    all_mats = {}
    all_mats["fwd"], all_mats["rev"] = aligner.get_alignment_matrix(sim_matrix)
    all_mats["inter"] = all_mats["fwd"] * all_mats["rev"]
    if simalign_method == "mwmf":
        all_mats["mwmf"] = aligner.get_max_weight_match(sim_matrix)
    elif simalign_method == "itermax":
        all_mats["itermax"] = aligner.iter_max(sim_matrix)

    active_matrix = all_mats[simalign_method]
    aligned_word_pairs = set()
    for src_bpe_index in range(src_bpe_count):
        for tgt_bpe_index in range(tgt_bpe_count):
            if active_matrix[src_bpe_index, tgt_bpe_index] > 0:
                aligned_word_pairs.add(
                    (src_bpe_to_word[src_bpe_index], tgt_bpe_to_word[tgt_bpe_index])
                )

    word_score_matrix = np.zeros((len(sent_src), len(sent_tgt)), dtype=float)
    for src_word_index, src_bpe_indexes in src_word_to_bpe.items():
        for tgt_word_index, tgt_bpe_indexes in tgt_word_to_bpe.items():
            best_score = 0.0
            for src_bpe_index in src_bpe_indexes:
                for tgt_bpe_index in tgt_bpe_indexes:
                    best_score = max(best_score, float(sim_matrix[src_bpe_index, tgt_bpe_index]))
            word_score_matrix[src_word_index, tgt_word_index] = best_score

    return {
        "word_pairs": sorted(aligned_word_pairs),
        "word_score_matrix": word_score_matrix,
    }


def build_alignment_tensor_from_word_pairs(word_pairs, source_len, target_len):
    matrix = torch.zeros((source_len, target_len), dtype=torch.bool)
    for source_index, target_index in word_pairs:
        matrix[source_index, target_index] = True
    return matrix


def prepare_simalign_sentence_artifacts(sent_src, sent_tgt):
    payload = compute_simalign_word_pairs_and_scores(sent_src, sent_tgt)
    word_pairs = payload["word_pairs"]
    word_score_matrix = payload["word_score_matrix"]
    score_tensor = torch.tensor(word_score_matrix, dtype=torch.float)
    alignment_tensor = build_alignment_tensor_from_word_pairs(
        word_pairs, len(sent_src), len(sent_tgt)
    )
    identity_src_map = list(range(len(sent_src)))
    identity_tgt_map = list(range(len(sent_tgt)))
    merged_pairs = merge_aligned_index_pairs(
        torch.tensor(word_pairs, dtype=torch.long) if word_pairs else torch.empty((0, 2), dtype=torch.long),
        identity_src_map,
        identity_tgt_map,
    )
    candidates = collect_top_target_candidates_from_matrix(
        sent_src,
        [""] * len(sent_src),  # replaced by real pos tags at call site if needed
        sent_tgt,
        [""] * len(sent_tgt),
        {index: [index] for index in range(len(sent_src))},
        {index: [index] for index in range(len(sent_tgt))},
        word_score_matrix,
    )
    return {
        "word_pairs": word_pairs,
        "word_score_matrix": word_score_matrix,
        "score_tensor": score_tensor,
        "alignment_tensor": alignment_tensor,
        "identity_src_map": identity_src_map,
        "identity_tgt_map": identity_tgt_map,
        "merged_pairs": merged_pairs,
        "candidates": candidates,
    }


def awesome_alignment_postprocessing(
    softmax_inter,
    sub2word_map_src,
    sub2word_map_tgt,
    pos_src,
    pos_trg,
    sent_src,
    sent_tgt,
    softmax_srctrg=None,
    softmax_trgsrc=None,
):
    align_subwords = torch.nonzero(softmax_inter, as_tuple=False)
    index_pair_list = merge_aligned_index_pairs(
        align_subwords, sub2word_map_src, sub2word_map_tgt
    )
    index_src_ignore = collect_src_ignore_indexes(sent_src, pos_src)
    index_trg_ignore = collect_trg_ignore_indexes(sent_tgt)
    trim_ignored_groups = current_japanese_text_backend_name() != "jumanpp"
    alignmented_l = []
    alignmented_l_append = alignmented_l.append
    for index_pair in index_pair_list:
        if trim_ignored_groups:
            src_index_set = index_pair[0].difference(index_src_ignore)
            trg_index_set = index_pair[1].difference(index_trg_ignore)
        else:
            if not index_pair[0].isdisjoint(index_src_ignore) or not index_pair[1].isdisjoint(
                index_trg_ignore
            ):
                continue
            src_index_set = index_pair[0]
            trg_index_set = index_pair[1]
        src_indexes_sorted = trim_indexes_to_content(sorted(src_index_set), pos_src)
        trg_indexes_sorted = trim_indexes_to_content(sorted(trg_index_set), pos_trg)
        src_indexes_sorted = maybe_expand_source_noun_compound(
            src_indexes_sorted,
            trg_indexes_sorted,
            sent_src,
            pos_src,
            sub2word_map_src,
            sub2word_map_tgt,
            softmax_srctrg,
        )
        src_indexes_sorted = maybe_expand_source_lexicalized_noun_compound(
            src_indexes_sorted,
            trg_indexes_sorted,
            sent_src,
            pos_src,
            sent_tgt,
        )
        trg_indexes_sorted = collapse_honorific_target_variants(
            trg_indexes_sorted, sent_tgt, pos_trg
        )
        if not src_indexes_sorted or not trg_indexes_sorted:
            continue
        if (
            len(src_indexes_sorted) > 1
            and not indexes_are_consecutive(src_indexes_sorted)
        ) or (
            len(trg_indexes_sorted) > 1
            and not indexes_are_consecutive(trg_indexes_sorted)
        ):
            continue
        alignment_scores = collect_alignment_scores(
            src_indexes_sorted,
            trg_indexes_sorted,
            align_subwords,
            sub2word_map_src,
            sub2word_map_tgt,
            softmax_srctrg,
            softmax_trgsrc,
        )
        if alignment_scores and max(alignment_scores) < minimum_alignment_confidence:
            continue
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
            src_words_list = [sent_src[src_index] for src_index in src_indexes_sorted]
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
            trg_words_list = [sent_tgt[trg_index] for trg_index in trg_indexes_sorted]
            trg_pos_list = [pos_trg[trg_index] for trg_index in trg_indexes_sorted]
        src_content_pos_tags = collect_content_pos_tags(src_pos_list)
        trg_content_pos_tags = collect_content_pos_tags(trg_pos_list)
        if not src_content_pos_tags or not trg_content_pos_tags:
            continue
        if not content_pos_sets_are_compatible(
            src_content_pos_tags,
            trg_content_pos_tags,
            trg_words_list,
        ):
            continue
        alignmented_l_append(
            (
                src_pos_list,
                src_words_list,
                trg_pos_list,
                trg_words_list,
                {
                    "source_indices": src_indexes_sorted,
                    "target_indices": trg_indexes_sorted,
                    "best_alignment_score": (
                        max(alignment_scores) if alignment_scores else None
                    ),
                    "average_alignment_score": (
                        sum(alignment_scores) / len(alignment_scores)
                        if alignment_scores
                        else None
                    ),
                    "alignment_evidence_count": len(alignment_scores),
                },
            )
        )
    return alignmented_l


def awesome_alignment_batch(
    sentence_srcs, sentence_trgs, src_morphological_batch, trg_morphological_batch
):
    model, tokenizer = get_model_and_tokenizer()

    # morphological analysis
    sent_srcs, pos_srcs = src_morphological_batch(sentence_srcs)
    sent_trgs, pos_trgs = trg_morphological_batch(sentence_trgs)

    # pre-processing
    ids_srcs, ids_trgs, sub2word_map_srcs, sub2word_map_trgs = zip(
        *[
            awesome_alignment_preprocessing(sent_src, sent_trg, tokenizer)
            for sent_src, sent_trg in zip(sent_srcs, sent_trgs)
        ]
    )

    # alignment
    def padding(ids_list):
        pad_token_id = tokenizer.pad_token_id

        max_size = max([ids.size(0) for ids in ids_list])
        padded_ids_list = []
        attention_mask_list = []
        for ids in ids_list:
            pad_size = max_size - ids.size(0)
            padded_ids_list.append(
                torch.cat(
                    [
                        ids,
                        torch.tensor(
                            [pad_token_id] * pad_size,
                            dtype=torch.long,
                            device=ids.device,
                        ),
                    ]
                )
            )
            attention_mask_list.append(
                torch.cat(
                    [
                        torch.ones(ids.size(0), dtype=torch.long, device=ids.device),
                        torch.zeros(pad_size, dtype=torch.long, device=ids.device),
                    ]
                )
            )
        return torch.stack(padded_ids_list), torch.stack(attention_mask_list)

    padded_ids_src_tensor, attention_mask_src_tensor = padding(ids_srcs)
    padded_ids_trg_tensor, attention_mask_trg_tensor = padding(ids_trgs)

    model.eval()

    with torch.no_grad():
        padded_out_src_tensor = model(
            padded_ids_src_tensor.to(device),
            attention_mask=attention_mask_src_tensor.to(device),
            output_hidden_states=True,
        )[2][align_layer].to("cpu")
        padded_out_trg_tensor = model(
            padded_ids_trg_tensor.to(device),
            attention_mask=attention_mask_trg_tensor.to(device),
            output_hidden_states=True,
        )[2][align_layer].to("cpu")

    softmax_inter_list = []
    softmax_srctrg_list = []
    softmax_trgsrc_list = []

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
        softmax_srctrg_list.append(softmax_srctrg)
        softmax_trgsrc_list.append(softmax_trgsrc)

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
            softmax_srctrg=softmax_srctrg,
            softmax_trgsrc=softmax_trgsrc,
        )
        for softmax_inter, softmax_srctrg, softmax_trgsrc, sub2word_map_src, sub2word_map_trg, pos_src, pos_trg, sent_src, sent_trg in zip(
            softmax_inter_list,
            softmax_srctrg_list,
            softmax_trgsrc_list,
            sub2word_map_srcs,
            sub2word_map_trgs,
            pos_srcs,
            pos_trgs,
            sent_srcs,
            sent_trgs,
        )
    ]

    return alignmented_ls


def simalign_alignment_batch(
    sentence_srcs, sentence_trgs, src_morphological_batch, trg_morphological_batch
):
    sent_srcs, pos_srcs = src_morphological_batch(sentence_srcs)
    sent_trgs, pos_trgs = trg_morphological_batch(sentence_trgs)

    alignmented_ls = []
    for sent_src, sent_trg, pos_src, pos_trg in zip(
        sent_srcs, sent_trgs, pos_srcs, pos_trgs
    ):
        artifacts = prepare_simalign_sentence_artifacts(sent_src, sent_trg)
        alignmented_ls.append(
            awesome_alignment_postprocessing(
                artifacts["alignment_tensor"],
                artifacts["identity_src_map"],
                artifacts["identity_tgt_map"],
                pos_src,
                pos_trg,
                sent_src,
                sent_trg,
                softmax_srctrg=artifacts["score_tensor"],
                softmax_trgsrc=artifacts["score_tensor"],
            )
        )
    return alignmented_ls


def inspect_sentence_pair(sentence_src, sentence_tgt, wordlist="", test=True):
    sent_src, pos_src = en_morphological(sentence_src)
    sent_tgt, pos_tgt = ja_morphological(sentence_tgt)
    index_src_ignore = collect_src_ignore_indexes(sent_src, pos_src)
    index_tgt_ignore = collect_trg_ignore_indexes(sent_tgt)

    if alignment_backend_name == "awesome":
        model, tokenizer = get_model_and_tokenizer()
        ids_src, ids_tgt, sub2word_map_src, sub2word_map_tgt = (
            awesome_alignment_preprocessing(sent_src, sent_tgt, tokenizer)
        )

        model.eval()
        with torch.no_grad():
            attention_mask_src = torch.ones_like(ids_src, dtype=torch.long)
            attention_mask_tgt = torch.ones_like(ids_tgt, dtype=torch.long)
            out_src = model(
                ids_src.unsqueeze(0).to(device),
                attention_mask=attention_mask_src.unsqueeze(0).to(device),
                output_hidden_states=True,
            )[2][align_layer][0].to("cpu")
            out_tgt = model(
                ids_tgt.unsqueeze(0).to(device),
                attention_mask=attention_mask_tgt.unsqueeze(0).to(device),
                output_hidden_states=True,
            )[2][align_layer][0].to("cpu")

        out_src = out_src[1 : ids_src.size(0) - 1]
        out_tgt = out_tgt[1 : ids_tgt.size(0) - 1]
        dot_prod = torch.matmul(out_src, out_tgt.transpose(-1, -2))
        softmax_srctrg = torch.nn.Softmax(dim=-1)(dot_prod)
        softmax_trgsrc = torch.nn.Softmax(dim=-2)(dot_prod)
        softmax_inter = (softmax_srctrg > threshold) * (softmax_trgsrc > threshold)
        merged_pairs = merge_aligned_index_pairs(
            torch.nonzero(softmax_inter, as_tuple=False),
            sub2word_map_src,
            sub2word_map_tgt,
        )
        merged_pair_descriptions = [
            describe_merged_index_pair(
                index_pair,
                sent_src,
                pos_src,
                sent_tgt,
                pos_tgt,
                index_src_ignore,
                index_tgt_ignore,
            )
            for index_pair in merged_pairs
        ]
        alignmented = awesome_alignment_postprocessing(
            softmax_inter,
            sub2word_map_src,
            sub2word_map_tgt,
            pos_src,
            pos_tgt,
            sent_src,
            sent_tgt,
            softmax_srctrg=softmax_srctrg,
            softmax_trgsrc=softmax_trgsrc,
        )
        source_target_candidates = collect_top_target_candidates(
            sent_src,
            pos_src,
            sent_tgt,
            pos_tgt,
            sub2word_map_src,
            sub2word_map_tgt,
            softmax_srctrg,
        )
    elif alignment_backend_name == "simalign":
        artifacts = prepare_simalign_sentence_artifacts(sent_src, sent_tgt)
        merged_pair_descriptions = [
            describe_merged_index_pair(
                index_pair,
                sent_src,
                pos_src,
                sent_tgt,
                pos_tgt,
                index_src_ignore,
                index_tgt_ignore,
            )
            for index_pair in artifacts["merged_pairs"]
        ]
        alignmented = awesome_alignment_postprocessing(
            artifacts["alignment_tensor"],
            artifacts["identity_src_map"],
            artifacts["identity_tgt_map"],
            pos_src,
            pos_tgt,
            sent_src,
            sent_tgt,
            softmax_srctrg=artifacts["score_tensor"],
            softmax_trgsrc=artifacts["score_tensor"],
        )
        source_target_candidates = collect_top_target_candidates_from_matrix(
            sent_src,
            pos_src,
            sent_tgt,
            pos_tgt,
            {index: [index] for index in range(len(sent_src))},
            {index: [index] for index in range(len(sent_tgt))},
            artifacts["word_score_matrix"],
        )
    else:
        raise RuntimeError(
            f"unsupported en_ja alignment backend: {alignment_backend_name}"
        )
    output_l = alignment_postprocessing(alignmented, wordlist, test=test)

    return {
        "runtime": runtime_metadata(),
        "source": {
            "text": sentence_src,
            "tokens": describe_token_sequence(sent_src, pos_src),
        },
        "target": {
            "text": sentence_tgt,
            "tokens": describe_token_sequence(sent_tgt, pos_tgt),
        },
        "ignored_source_indices": sorted(index_src_ignore),
        "ignored_target_indices": sorted(index_tgt_ignore),
        "merged_groups": merged_pair_descriptions,
        "postprocessed_groups": [
            describe_postprocessed_alignment_group(word_pair)
            for word_pair in alignmented
        ],
        "source_target_candidates": source_target_candidates,
        "final_pairs": [
            describe_final_alignment_item(item, test=test) for item in output_l
        ],
    }


def alignment_preprocessing(corpus_row):
    corpus_row = list(corpus_row)
    corpus_row[1] = corpus_row[1].replace("@", "")
    corpus_row[2] = corpus_row[2].replace("@", "")
    return corpus_row


def alignment_postprocessing(alignmented, wordlist, test=False):
    candidate_rows = []
    src_normalized_dict = {}
    trg_normalized_dict = {}
    for word_pair in alignmented:
        src_pos_l = word_pair[0]
        src_word_l = word_pair[1]
        trg_pos_l = word_pair[2]
        trg_word_l = word_pair[3]
        metadata = word_pair[4] if len(word_pair) > 4 else {}
        independent_index_src = -1
        for src_index, pos_tag in enumerate(src_pos_l):
            if pos_tag != "":
                independent_index_src = src_index
        independent_index_trg = -1
        for trg_index, pos_tag in enumerate(trg_pos_l):
            if pos_tag != "":
                independent_index_trg = trg_index
        independent_pos_tag = resolve_independent_output_pos_tags(
            src_pos_l,
            trg_pos_l,
            trg_word_l,
        )
        find_flag_src = False
        find_flag_trg = False
        src_pos_tag_s = set()
        trg_pos_tag_s = set()
        for src_len in range(len(src_word_l), 0, -1):
            for src_con in itertools.combinations(range(len(src_word_l)), src_len):
                if count_content_tokens(src_con, src_pos_l) > max_word_len:
                    continue
                if independent_index_src in src_con:
                    src_surface = join_english_tokens_for_surface(
                        [src_word_l[src_index] for src_index in src_con]
                    )
                    src_lookup = build_alignment_lookup_text(
                        [src_word_l[src_index] for src_index in src_con],
                        [src_pos_l[src_index] for src_index in src_con],
                        src_word_sep,
                    )
                    for pos_tag in independent_pos_tag:
                        if test:
                            src_normalized = en_normalizer(
                                src_lookup, pos_tag, wordlist, test
                            )
                            src_id = -1
                        else:
                            src_id, src_normalized = en_normalizer(
                                src_lookup, pos_tag, wordlist, test
                            )
                        if src_id is not None:
                            if src_surface not in src_normalized_dict:
                                src_normalized_dict[src_surface] = {}
                            src_normalized_dict[src_surface][pos_tag] = {
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

        for trg_len in range(len(trg_word_l), 0, -1):
            for trg_con in itertools.combinations(range(len(trg_word_l)), trg_len):
                if count_content_tokens(trg_con, trg_pos_l) > max_word_len:
                    continue
                if independent_index_trg in trg_con:
                    trg_word = trg_word_sep.join(
                        [trg_word_l[trg_index] for trg_index in trg_con]
                    )
                    for pos_tag in independent_pos_tag:
                        if test:
                            trg_normalized = ja_normalizer(
                                trg_word, pos_tag, wordlist, test
                            )
                            trg_id = -1
                        else:
                            trg_id, trg_normalized = ja_normalizer(
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
                source_normalized = src_normalized_dict[src_surface][pos_tag]["word_normalized"]
                target_normalized = trg_normalized_dict[trg_word][pos_tag]["word_normalized"]
                if pos_tag == "v" and should_suppress_precision_verb_pair(
                    source_normalized,
                    target_normalized,
                    trg_word,
                ):
                    continue
                if should_suppress_low_value_pair(
                    pos_tag,
                    source_normalized,
                    target_normalized,
                ):
                    continue
                if [
                    source_normalized,
                    target_normalized,
                ] not in exceptions:
                    candidate_rows.append(
                        {
                            "pos_tag": pos_tag,
                            "source_id": str(
                                src_normalized_dict[src_surface][pos_tag]["id"]
                            ),
                            "source_surface": src_surface,
                            "source_normalized": source_normalized,
                            "target_id": str(
                                trg_normalized_dict[trg_word][pos_tag]["id"]
                            ),
                            "target_surface": trg_word,
                            "target_normalized": target_normalized,
                            "metadata": metadata,
                            "average_alignment_score": metadata.get(
                                "average_alignment_score"
                            ),
                        }
                    )

    grouped_candidates = {}
    for candidate in candidate_rows:
        key = (candidate["pos_tag"], candidate["source_normalized"])
        grouped_candidates.setdefault(key, []).append(candidate)

    output_l = []
    output_l_append = output_l.append
    for candidate in candidate_rows:
        if should_suppress_competing_duplicate_source_pair(
            candidate, grouped_candidates
        ):
            continue
        output_row = [
            candidate["pos_tag"],
            candidate["source_id"],
            candidate["source_surface"],
            candidate["target_id"],
            candidate["target_surface"],
        ]
        if test:
            metadata = dict(candidate["metadata"])
            metadata["source_normalized"] = candidate["source_normalized"]
            metadata["target_normalized"] = candidate["target_normalized"]
            output_row.append(metadata)
        output_l_append(output_row)
    return output_l


def alignment_batch(corpus_rows, wordlist, test=False):
    # pre-processing
    corpus_rows = [alignment_preprocessing(corpus_row) for corpus_row in corpus_rows]

    # morphological analysis and alignment
    if alignment_backend_name == "awesome":
        alignmented_ls = awesome_alignment_batch(
            [corpus_row[1] for corpus_row in corpus_rows],
            [corpus_row[2] for corpus_row in corpus_rows],
            en_morphological_batch,
            ja_morphological_batch,
        )
    elif alignment_backend_name == "simalign":
        alignmented_ls = simalign_alignment_batch(
            [corpus_row[1] for corpus_row in corpus_rows],
            [corpus_row[2] for corpus_row in corpus_rows],
            en_morphological_batch,
            ja_morphological_batch,
        )
    else:
        raise RuntimeError(
            f"unsupported en_ja alignment backend: {alignment_backend_name}"
        )

    # post-processing
    assert len(alignmented_ls) == len(corpus_rows)

    output_ls = [
        alignment_postprocessing(alignmented, wordlist, test)
        for alignmented in alignmented_ls
    ]

    return output_ls


def alignment(corpus_row, wordlist, test=False):
    corpus_rows = [corpus_row]
    return alignment_batch(corpus_rows, wordlist, test)[0]
