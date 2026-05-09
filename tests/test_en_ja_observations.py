import os
import sys
import unittest


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from ltc.observations.en_ja import (
    build_observation_payload,
    summarize_observation_documents,
)


class EnJaObservationExtractionTest(unittest.TestCase):
    def test_builds_phrase_observation_with_compound_noun_projections(self):
        payload = {
            "source": {
                "tokens": [
                    {"index": 3, "text": "game", "pos_tag": "n"},
                    {"index": 4, "text": "titles", "pos_tag": "n"},
                ]
            },
            "target": {
                "tokens": [
                    {"index": 2, "text": "ゲームタイトル", "pos_tag": "n"},
                ]
            },
            "final_pairs": [
                {
                    "pos_tag": "n",
                    "source_surface": "game titles",
                    "source_normalized": "game title",
                    "target_surface": "ゲームタイトル",
                    "target_normalized": "ゲームタイトル",
                }
            ],
            "postprocessed_groups": [
                {
                    "source_tokens": ["game titles"],
                    "source_pos_tags": ["n/n"],
                    "target_tokens": ["ゲームタイトル"],
                    "target_pos_tags": ["n"],
                    "source_indices": [3, 4],
                    "target_indices": [2],
                    "average_alignment_score": 1.0,
                }
            ],
        }

        observations = build_observation_payload(payload)
        self.assertEqual(len(observations["word_observations"]), 1)
        self.assertEqual(len(observations["phrase_observations"]), 1)

        phrase = observations["phrase_observations"][0]
        self.assertEqual(phrase["source_surface"], "game titles")
        self.assertEqual(phrase["lexicalization_action"], "hold_phrase_only")
        self.assertEqual(len(phrase["component_projections"]), 2)
        self.assertEqual(
            [
                (
                    projection["source_normalized"],
                    projection["target_normalized"],
                    projection["promotion_status"],
                )
                for projection in phrase["component_projections"]
            ],
            [
                ("game", "ゲーム", "auto_candidate"),
                ("title", "タイトル", "auto_candidate"),
            ],
        )
        self.assertEqual(
            [decision["recommended_action"] for decision in observations["lexicalization_decisions"]],
            ["register_phrase", "project_components_auto"],
        )

    def test_builds_reverse_of_genitive_component_projections_from_merged_group(self):
        payload = {
            "source": {
                "tokens": [
                    {"index": 9, "text": "examples", "pos_tag": "n"},
                    {"index": 10, "text": "of", "pos_tag": ""},
                    {"index": 11, "text": "construction", "pos_tag": "n"},
                ]
            },
            "target": {
                "tokens": [
                    {"index": 2, "text": "施工事例", "pos_tag": "n"},
                ]
            },
            "final_pairs": [],
            "postprocessed_groups": [],
            "merged_groups": [
                {
                    "source_tokens": ["examples", "construction"],
                    "source_pos_tags": ["n", "n"],
                    "target_tokens": ["施工事例"],
                    "target_pos_tags": ["n"],
                    "source_indices": [9, 11],
                    "target_indices": [2],
                    "ignored_by_source_rule": False,
                    "ignored_by_target_rule": False,
                }
            ],
        }

        observations = build_observation_payload(payload)
        phrase = observations["phrase_observations"][0]
        self.assertEqual(len(phrase["component_projections"]), 2)
        self.assertEqual(
            [
                (
                    projection["source_normalized"],
                    projection["target_normalized"],
                    projection["reason"],
                    projection["promotion_status"],
                )
                for projection in phrase["component_projections"]
            ],
            [
                (
                    "construction",
                    "施工",
                    "reverse_of_genitive_compound_projection",
                    "auto_candidate",
                ),
                (
                    "example",
                    "事例",
                    "reverse_of_genitive_compound_projection",
                    "auto_candidate",
                ),
            ],
        )
        self.assertEqual(
            observations["lexicalization_decisions"][0]["recommended_action"],
            "project_components_auto",
        )

    def test_allows_lower_confidence_auto_projection_for_safe_loanword_suffix_compound(self):
        payload = {
            "source": {
                "tokens": [
                    {"index": 4, "text": "text", "pos_tag": "n"},
                    {"index": 5, "text": "editor", "pos_tag": "n"},
                    {"index": 6, "text": "side", "pos_tag": "n"},
                ]
            },
            "target": {
                "tokens": [
                    {"index": 3, "text": "テキストエディタ側", "pos_tag": "n"},
                ]
            },
            "final_pairs": [
                {
                    "pos_tag": "n",
                    "source_surface": "text editor side",
                    "source_normalized": "text editor side",
                    "target_surface": "テキストエディタ側",
                    "target_normalized": "テキストエディタ側",
                }
            ],
            "postprocessed_groups": [
                {
                    "source_tokens": ["text", "editor", "side"],
                    "source_pos_tags": ["n", "n", "n"],
                    "target_tokens": ["テキストエディタ側"],
                    "target_pos_tags": ["n"],
                    "source_indices": [4, 5, 6],
                    "target_indices": [3],
                    "average_alignment_score": 0.74,
                }
            ],
        }

        observations = build_observation_payload(payload)
        decisions = observations["lexicalization_decisions"]
        self.assertEqual(
            [decision["recommended_action"] for decision in decisions],
            ["register_phrase", "project_components_auto"],
        )
        phrase = observations["phrase_observations"][0]
        self.assertEqual(
            [projection["target_normalized"] for projection in phrase["component_projections"]],
            ["テキスト", "エディタ", "側"],
        )

    def test_phrase_observation_without_component_projection_stays_hold_only(self):
        payload = {
            "source": {
                "tokens": [
                    {"index": 5, "text": "that", "pos_tag": ""},
                    {"index": 6, "text": "side", "pos_tag": "n"},
                ]
            },
            "target": {
                "tokens": [
                    {"index": 3, "text": "そちら側", "pos_tag": "n"},
                ]
            },
            "final_pairs": [
                {
                    "pos_tag": "n",
                    "source_surface": "side",
                    "source_normalized": "side",
                    "target_surface": "そちら側",
                    "target_normalized": "そちら側",
                }
            ],
            "postprocessed_groups": [
                {
                    "source_tokens": ["side"],
                    "source_pos_tags": ["n"],
                    "target_tokens": ["そちら側"],
                    "target_pos_tags": ["n"],
                    "source_indices": [5, 6],
                    "target_indices": [3],
                    "average_alignment_score": 1.0,
                }
            ],
        }

        observations = build_observation_payload(payload)
        self.assertEqual(observations["phrase_observations"], [])
        self.assertEqual(
            [decision["recommended_action"] for decision in observations["lexicalization_decisions"]],
            ["register_word"],
        )

    def test_component_projection_skips_source_span_with_function_word_gap(self):
        payload = {
            "source": {
                "tokens": [
                    {"index": 13, "text": "hand", "pos_tag": "n"},
                    {"index": 14, "text": "every", "pos_tag": ""},
                    {"index": 15, "text": "time", "pos_tag": "n"},
                ]
            },
            "target": {
                "tokens": [
                    {"index": 6, "text": "毎回手", "pos_tag": "n"},
                ]
            },
            "final_pairs": [],
            "postprocessed_groups": [
                {
                    "source_tokens": ["hand", "every", "time"],
                    "source_pos_tags": ["n", "", "n"],
                    "target_tokens": ["毎回手"],
                    "target_pos_tags": ["n"],
                    "source_indices": [13, 14, 15],
                    "target_indices": [6],
                    "average_alignment_score": 1.0,
                }
            ],
        }

        observations = build_observation_payload(payload)
        self.assertEqual(observations["phrase_observations"], [])
        self.assertEqual(observations["lexicalization_decisions"], [])

    def test_summarize_observation_documents_counts_actions(self):
        documents = [
            {
                "word_observations": [{}],
                "phrase_observations": [{"component_projections": [{}, {}]}],
                "lexicalization_decisions": [
                    {"recommended_action": "register_word"},
                    {"recommended_action": "project_components_auto"},
                ],
            },
            {
                "word_observations": [{}, {}],
                "phrase_observations": [{"component_projections": []}],
                "lexicalization_decisions": [
                    {"recommended_action": "register_phrase"},
                    {"recommended_action": "hold_phrase_only"},
                ],
            },
        ]

        summary = summarize_observation_documents(documents)
        self.assertEqual(summary["documents"], 2)
        self.assertEqual(summary["word_observations"], 3)
        self.assertEqual(summary["phrase_observations"], 2)
        self.assertEqual(summary["component_projections"], 2)
        self.assertEqual(
            summary["lexicalization_decisions"],
            {
                "register_word": 1,
                "project_components_auto": 1,
                "register_phrase": 1,
                "hold_phrase_only": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()
