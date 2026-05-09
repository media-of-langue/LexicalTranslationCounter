"""Phrase-aware observation extraction for the en_ja alignment path.

This layer is intentionally additive: it preserves phrase-level evidence and
derives component-level hypotheses, but it does not directly change the legacy
word-count aggregation path.
"""

from __future__ import annotations

from dataclasses import asdict
import re

from normalizer.en_normalizer import en_normalizer
from ltc.japanese.backends import current_japanese_text_backend_name
from ltc.japanese.morphology import get_japanese_raw_morphemes
from ltc.japanese.normalization import ja_normalizer
from ltc.schema import (
    ComponentProjection,
    LexicalizationDecision,
    TranslationObservation,
)


RAW_POS_TO_TAG = {
    "名詞": "n",
    "動詞": "v",
    "形容詞": "a",
    "形状詞": "a",
    "副詞": "r",
}

KATAKANA_RE = re.compile(r"^[ァ-ヶー]+$")
SAFE_JA_COMPOUND_SUFFIX_TARGETS = {"側"}
SAFE_REVERSE_GENITIVE_HEAD_TARGETS = {"事例"}


def observation_to_dict(observation: TranslationObservation):
    return asdict(observation)


def build_observation_payload(inspection_payload):
    word_observations = build_word_observations(inspection_payload)
    phrase_observations = build_phrase_observations(inspection_payload)
    lexicalization_decisions = build_lexicalization_decisions(
        word_observations,
        phrase_observations,
    )
    return {
        "word_observations": [observation_to_dict(item) for item in word_observations],
        "phrase_observations": [observation_to_dict(item) for item in phrase_observations],
        "lexicalization_decisions": [
            observation_to_dict(item) for item in lexicalization_decisions
        ],
    }


def summarize_observation_documents(documents):
    decisions_by_action = {}
    total_word_observations = 0
    total_phrase_observations = 0
    total_component_projections = 0
    for document in documents:
        total_word_observations += len(document.get("word_observations", []))
        total_phrase_observations += len(document.get("phrase_observations", []))
        for observation in document.get("phrase_observations", []):
            total_component_projections += len(
                observation.get("component_projections", [])
            )
        for decision in document.get("lexicalization_decisions", []):
            action = decision["recommended_action"]
            decisions_by_action[action] = decisions_by_action.get(action, 0) + 1
    return {
        "documents": len(documents),
        "word_observations": total_word_observations,
        "phrase_observations": total_phrase_observations,
        "component_projections": total_component_projections,
        "lexicalization_decisions": decisions_by_action,
    }


def build_word_observations(inspection_payload):
    observations = []
    for pair in inspection_payload.get("final_pairs", []):
        observations.append(
            TranslationObservation(
                pos_tag=pair["pos_tag"],
                source_surface=pair["source_surface"],
                source_normalized=pair["source_normalized"],
                target_surface=pair["target_surface"],
                target_normalized=pair["target_normalized"],
                unit_level="word",
                lexicalization_action="register_word",
                lexicalization_reason="legacy_final_pair",
                best_alignment_score=pair.get("best_alignment_score"),
                average_alignment_score=pair.get("average_alignment_score"),
                alignment_evidence_count=pair.get("alignment_evidence_count"),
            )
        )
    return tuple(observations)


def build_lexicalization_decisions(word_observations, phrase_observations):
    decisions = []
    for observation in word_observations:
        decisions.append(
            LexicalizationDecision(
                pos_tag=observation.pos_tag,
                source_surface=observation.source_surface,
                source_normalized=observation.source_normalized,
                target_surface=observation.target_surface,
                target_normalized=observation.target_normalized,
                observation_unit_level=observation.unit_level,
                recommended_action=decide_word_observation_action(observation),
                reason=describe_word_observation_reason(observation),
                confidence=observation.average_alignment_score,
                metadata=dict(observation.metadata),
            )
        )
    for observation in phrase_observations:
        decisions.append(
            LexicalizationDecision(
                pos_tag=observation.pos_tag,
                source_surface=observation.source_surface,
                source_normalized=observation.source_normalized,
                target_surface=observation.target_surface,
                target_normalized=observation.target_normalized,
                observation_unit_level=observation.unit_level,
                recommended_action=decide_phrase_observation_action(observation),
                reason=describe_phrase_observation_reason(observation),
                confidence=observation.average_alignment_score,
                component_projections=tuple(observation.component_projections),
                metadata=dict(observation.metadata),
            )
        )
    return tuple(decisions)


def decide_word_observation_action(observation):
    if observation_looks_phrase_like(observation):
        return "register_phrase"
    return "register_word"


def describe_word_observation_reason(observation):
    if observation_looks_phrase_like(observation):
        return (
            "legacy final pair survived as a stable multiword lexical unit; "
            "register as a phrase candidate"
        )
    return "legacy final pair is already stable at the word level"


def decide_phrase_observation_action(observation):
    if phrase_observation_allows_auto_component_projection(observation):
        return "project_components_auto"
    if observation.component_projections:
        return "project_components_needs_review"
    return "hold_phrase_only"


def describe_phrase_observation_reason(observation):
    if phrase_observation_allows_auto_component_projection(observation):
        return (
            "phrase-level evidence cleanly decomposes into aligned noun components; "
            "safe to treat as an automatic component candidate"
        )
    if observation.component_projections:
        return (
            "phrase-level evidence suggests reusable component relations, "
            "but they should be reviewed before promotion"
        )
    return observation.lexicalization_reason


def phrase_observation_allows_auto_component_projection(observation):
    if not observation.component_projections:
        return False
    if all(
        projection.reason == "aligned_noun_compound_projection"
        for projection in observation.component_projections
    ):
        confidence = observation.average_alignment_score
        if confidence is not None and confidence >= 0.98:
            return True
        return aligned_compound_projection_is_safe_even_at_lower_confidence(observation)
    if all(
        projection.reason == "reverse_of_genitive_compound_projection"
        for projection in observation.component_projections
    ):
        return reverse_of_genitive_projection_is_safe(observation)
    return False


def aligned_compound_projection_is_safe_even_at_lower_confidence(observation):
    projections = observation.component_projections
    if len(projections) < 2:
        return False
    return all(
        target_component_looks_like_safe_loanword_or_suffix(
            projection.target_normalized
        )
        for projection in projections
    )


def reverse_of_genitive_projection_is_safe(observation):
    projections = observation.component_projections
    if len(projections) != 2:
        return False
    head_target = projections[-1].target_normalized
    if head_target not in SAFE_REVERSE_GENITIVE_HEAD_TARGETS:
        return False
    return all(
        projection.source_normalized and projection.target_normalized
        for projection in projections
    )


def target_component_looks_like_safe_loanword_or_suffix(target_normalized):
    if target_normalized in SAFE_JA_COMPOUND_SUFFIX_TARGETS:
        return True
    return bool(KATAKANA_RE.fullmatch(target_normalized))


def observation_looks_phrase_like(observation):
    return (
        " " in observation.source_surface.strip()
        or " " in observation.source_normalized.strip()
    )


def build_phrase_observations(inspection_payload):
    observations = []
    phrase_like_final_pair_keys = build_phrase_like_final_pair_keys(inspection_payload)
    for group in iter_phrase_candidate_groups(inspection_payload):
        source_components = extract_source_components(inspection_payload, group)
        target_components = extract_target_components(inspection_payload, group)
        component_projections = build_component_projections(
            inspection_payload,
            group,
            source_components,
            target_components,
        )
        source_surface = " ".join(group["source_tokens"])
        target_surface = "".join(group["target_tokens"])
        source_normalized = " ".join(
            component["normalized"] for component in source_components
        ) or source_surface
        target_normalized = "".join(
            component["normalized"] for component in target_components
        ) or target_surface
        if not should_keep_phrase_observation(
            group,
            source_components,
            target_components,
            component_projections,
            phrase_like_final_pair_keys,
            source_normalized,
            target_normalized,
        ):
            continue
        if component_projections:
            lexicalization_reason = (
                "phrase evidence preserved with component projections; "
                "review before promoting to the word network"
            )
        elif group.get("_observation_origin") == "merged_groups":
            lexicalization_reason = (
                "phrase evidence preserved from a merged alignment span; "
                "the legacy word-level path dropped it, so review is required"
            )
        else:
            lexicalization_reason = (
                "phrase evidence preserved; lexicalization decision requires review"
            )
        observations.append(
            TranslationObservation(
                pos_tag=resolve_observation_pos_tag(group),
                source_surface=source_surface,
                source_normalized=source_normalized,
                target_surface=target_surface,
                target_normalized=target_normalized,
                source_indices=tuple(group.get("source_indices", [])),
                target_indices=tuple(group.get("target_indices", [])),
                source_pos_tags=tuple(group.get("source_pos_tags", [])),
                target_pos_tags=tuple(group.get("target_pos_tags", [])),
                unit_level="phrase",
                lexicalization_action="hold_phrase_only",
                lexicalization_reason=lexicalization_reason,
                best_alignment_score=group.get("best_alignment_score"),
                average_alignment_score=group.get("average_alignment_score"),
                alignment_evidence_count=group.get("alignment_evidence_count"),
                component_projections=tuple(component_projections),
                metadata={
                    "japanese_text_backend": current_japanese_text_backend_name(),
                },
            )
        )
    return tuple(observations)


def build_phrase_like_final_pair_keys(inspection_payload):
    keys = set()
    for pair in inspection_payload.get("final_pairs", []):
        if " " in pair.get("source_surface", "").strip() or " " in pair.get(
            "source_normalized", ""
        ).strip():
            keys.add(
                (
                    pair.get("pos_tag", ""),
                    pair.get("source_normalized", ""),
                    pair.get("target_normalized", ""),
                )
            )
    return keys


def should_keep_phrase_observation(
    group,
    source_components,
    target_components,
    component_projections,
    phrase_like_final_pair_keys,
    source_normalized,
    target_normalized,
):
    if component_projections:
        return True
    pos_tag = resolve_observation_pos_tag(group)
    if pos_tag != "n":
        return False
    key = (pos_tag, source_normalized, target_normalized)
    if key in phrase_like_final_pair_keys:
        return True
    if group.get("_observation_origin") != "merged_groups":
        return False
    source_noun_count = sum(1 for component in source_components if component["pos_tag"] == "n")
    target_noun_count = sum(1 for component in target_components if component["pos_tag"] == "n")
    if source_noun_count < 2:
        return False
    if target_noun_count < 1:
        return False
    if group.get("average_alignment_score") is not None and group["average_alignment_score"] < 0.75:
        return False
    return True


def iter_phrase_candidate_groups(inspection_payload):
    seen = set()
    for source_name in ("postprocessed_groups", "merged_groups"):
        for group in inspection_payload.get(source_name, []):
            if source_name == "merged_groups" and (
                group.get("ignored_by_source_rule") or group.get("ignored_by_target_rule")
            ):
                continue
            if not group_is_phrase_like(group):
                continue
            key = (
                tuple(group.get("source_indices", [])),
                tuple(group.get("target_indices", [])),
            )
            if key in seen:
                continue
            seen.add(key)
            payload = dict(group)
            payload["_observation_origin"] = source_name
            yield payload


def resolve_observation_pos_tag(group):
    source_pos_tags = [
        part
        for pos_tag in group.get("source_pos_tags", [])
        for part in pos_tag.split("/")
        if part
    ]
    return source_pos_tags[-1] if source_pos_tags else ""


def group_is_phrase_like(group):
    source_indices = group.get("source_indices", [])
    target_indices = group.get("target_indices", [])
    source_content_count = count_group_content_parts(group.get("source_pos_tags", []))
    target_content_count = count_group_content_parts(group.get("target_pos_tags", []))
    if source_content_count >= 2 or target_content_count >= 2:
        return True
    if source_content_count > 0 and len(source_indices) > source_content_count:
        return True
    if target_content_count > 0 and len(target_indices) > target_content_count:
        return True
    if any("/" in pos_tag for pos_tag in group.get("source_pos_tags", [])):
        return True
    if any("/" in pos_tag for pos_tag in group.get("target_pos_tags", [])):
        return True
    if any(" " in token for token in group.get("source_tokens", [])):
        return True
    return False


def count_group_content_parts(pos_tags):
    return sum(
        1
        for pos_tag in pos_tags
        for part in pos_tag.split("/")
        if part
    )


def extract_source_components(inspection_payload, group):
    tokens_by_index = {
        token["index"]: token
        for token in inspection_payload.get("source", {}).get("tokens", [])
    }
    components = []
    for source_index in group.get("source_indices", []):
        token = tokens_by_index.get(source_index)
        if token is None or not token["pos_tag"]:
            continue
        components.append(
            {
                "index": source_index,
                "surface": token["text"],
                "pos_tag": token["pos_tag"],
                "normalized": en_normalizer(token["text"], token["pos_tag"], {}, test=True),
            }
        )
    return tuple(components)


def extract_target_components(inspection_payload, group):
    target_surface = "".join(group.get("target_tokens", []))
    if not target_surface:
        return ()

    raw_components = []
    for raw_morph in get_japanese_raw_morphemes(target_surface):
        pos_tag = RAW_POS_TO_TAG.get(raw_morph.hinsi)
        if not pos_tag:
            continue
        raw_components.append(
            {
                "surface": raw_morph.midasi,
                "pos_tag": pos_tag,
                "normalized": ja_normalizer(raw_morph.midasi, pos_tag, {}, test=True),
            }
        )
    if len(raw_components) > 1:
        return tuple(raw_components)

    tokens_by_index = {
        token["index"]: token
        for token in inspection_payload.get("target", {}).get("tokens", [])
    }
    components = []
    for target_index in group.get("target_indices", []):
        token = tokens_by_index.get(target_index)
        if token is None or not token["pos_tag"]:
            continue
        components.append(
            {
                "index": target_index,
                "surface": token["text"],
                "pos_tag": token["pos_tag"],
                "normalized": ja_normalizer(token["text"], token["pos_tag"], {}, test=True),
            }
        )
    return tuple(components)


def build_component_projections(
    inspection_payload,
    group,
    source_components,
    target_components,
):
    if not source_components or not target_components:
        return ()
    if len(source_components) != len(group.get("source_indices", [])):
        return ()
    if max(len(source_components), len(target_components)) < 2:
        return ()
    if len(source_components) != len(target_components):
        return ()
    if {component["pos_tag"] for component in source_components} != {"n"}:
        return ()
    if {component["pos_tag"] for component in target_components} != {"n"}:
        return ()

    if source_span_looks_like_of_genitive(inspection_payload, group):
        source_components_for_projection = tuple(reversed(source_components))
        reason = "reverse_of_genitive_compound_projection"
        if target_components_support_auto_reverse_genitive_projection(target_components):
            promotion_status = "auto_candidate"
        else:
            promotion_status = "needs_review"
    else:
        source_components_for_projection = source_components
        reason = "aligned_noun_compound_projection"
        promotion_status = "auto_candidate"

    confidence = group.get("average_alignment_score")
    return tuple(
        ComponentProjection(
            pos_tag="n",
            source_surface=source_component["surface"],
            source_normalized=source_component["normalized"],
            target_surface=target_component["surface"],
            target_normalized=target_component["normalized"],
            confidence=confidence,
            reason=reason,
            promotion_status=promotion_status,
        )
        for source_component, target_component in zip(
            source_components_for_projection, target_components
        )
    )


def target_components_support_auto_reverse_genitive_projection(target_components):
    if len(target_components) != 2:
        return False
    return target_components[-1]["normalized"] in SAFE_REVERSE_GENITIVE_HEAD_TARGETS


def source_span_looks_like_of_genitive(inspection_payload, group):
    tokens_by_index = {
        token["index"]: token
        for token in inspection_payload.get("source", {}).get("tokens", [])
    }
    source_indices = list(group.get("source_indices", []))
    if len(source_indices) < 2:
        return False
    for left_index, right_index in zip(source_indices, source_indices[1:]):
        if right_index <= left_index + 1:
            continue
        between_tokens = [
            tokens_by_index[index]["text"].lower()
            for index in range(left_index + 1, right_index)
            if index in tokens_by_index
        ]
        if "of" in between_tokens:
            return True
    return False
