import os
import sys
import unittest

import torch


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from alignment import en_ja


class EnJaPostprocessingTest(unittest.TestCase):
    def test_merge_aligned_index_pairs_merges_transitive_connections(self):
        align_subwords = torch.tensor([[0, 0], [0, 1], [1, 1]])
        pairs = en_ja.merge_aligned_index_pairs(
            align_subwords,
            sub2word_map_src=[0, 1],
            sub2word_map_tgt=[0, 1],
        )
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][0], {0, 1})
        self.assertEqual(pairs[0][1], {0, 1})

    def test_collect_src_ignore_indexes_handles_capitalized_be_not(self):
        ignore_indexes = en_ja.collect_src_ignore_indexes(
            ["Is", "not", "you"],
            ["v", "r", ""],
        )
        self.assertIn(0, ignore_indexes)

    def test_collect_src_ignore_indexes_handles_copula_before_adjective(self):
        ignore_indexes = en_ja.collect_src_ignore_indexes(
            ["am", "happy"],
            ["v", "a"],
        )
        self.assertIn(0, ignore_indexes)

    def test_postprocessing_drops_false_alignment_for_be_not_pattern(self):
        result = en_ja.awesome_alignment_postprocessing(
            torch.tensor([[True]]),
            sub2word_map_src=[0],
            sub2word_map_tgt=[0],
            pos_src=["v", "r", ""],
            pos_trg=["v"],
            sent_src=["is", "not", "you"],
            sent_tgt=["消さ"],
        )
        self.assertEqual(result, [])

    def test_trim_indexes_to_content_drops_trailing_copula(self):
        trimmed = en_ja.trim_indexes_to_content([0, 1], ["a", ""])
        self.assertEqual(trimmed, [0])

    def test_collapse_honorific_target_variants_prefers_base_noun(self):
        collapsed = en_ja.collapse_honorific_target_variants(
            [0, 1],
            ["会社", "会社さん"],
            ["n", "n"],
        )
        self.assertEqual(collapsed, [0])

    def test_indexes_are_consecutive(self):
        self.assertTrue(en_ja.indexes_are_consecutive([2, 3, 4]))
        self.assertFalse(en_ja.indexes_are_consecutive([2, 9]))

    def test_postprocessing_skips_non_consecutive_multi_content_group(self):
        result = en_ja.awesome_alignment_postprocessing(
            torch.tensor([[True, False], [False, True]]),
            sub2word_map_src=[0, 0],
            sub2word_map_tgt=[0, 2],
            pos_src=["v"],
            pos_trg=["v", "", "v"],
            sent_src=["get"],
            sent_tgt=["得", "が", "はっきりして"],
        )
        self.assertEqual(result, [])

    def test_postprocessing_drops_low_confidence_group(self):
        result = en_ja.awesome_alignment_postprocessing(
            torch.tensor([[True]]),
            sub2word_map_src=[0],
            sub2word_map_tgt=[0],
            pos_src=["v"],
            pos_trg=["v"],
            sent_src=["hidden"],
            sent_tgt=["なり"],
            softmax_srctrg=torch.tensor([[0.0286]]),
            softmax_trgsrc=torch.tensor([[1.0]]),
        )
        self.assertEqual(result, [])

    def test_postprocessing_keeps_high_confidence_group_with_metadata(self):
        result = en_ja.awesome_alignment_postprocessing(
            torch.tensor([[True]]),
            sub2word_map_src=[0],
            sub2word_map_tgt=[0],
            pos_src=["v"],
            pos_trg=["v"],
            sent_src=["drink"],
            sent_tgt=["飲む"],
            softmax_srctrg=torch.tensor([[1.0]]),
            softmax_trgsrc=torch.tensor([[1.0]]),
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], ["drink"])
        self.assertEqual(result[0][3], ["飲む"])
        self.assertEqual(result[0][4]["best_alignment_score"], 1.0)

    def test_postprocessing_expands_adjacent_source_noun_compound(self):
        result = en_ja.awesome_alignment_postprocessing(
            torch.tensor([[True], [False]]),
            sub2word_map_src=[0, 1],
            sub2word_map_tgt=[0],
            pos_src=["n", "n"],
            pos_trg=["n"],
            sent_src=["game", "titles"],
            sent_tgt=["ゲームタイトル"],
            softmax_srctrg=torch.tensor([[1.0], [1.0]]),
            softmax_trgsrc=torch.tensor([[1.0], [1.0]]),
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], ["game titles"])
        self.assertEqual(result[0][3], ["ゲームタイトル"])

    def test_postprocessing_expands_lexicalized_living_room_compound(self):
        result = en_ja.awesome_alignment_postprocessing(
            torch.tensor([[True], [False]]),
            sub2word_map_src=[0, 1],
            sub2word_map_tgt=[0],
            pos_src=["n", "n"],
            pos_trg=["n"],
            sent_src=["living", "rooms"],
            sent_tgt=["リビング"],
            softmax_srctrg=torch.tensor([[0.8540], [0.0]]),
            softmax_trgsrc=torch.tensor([[1.0], [0.0]]),
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], ["living rooms"])
        self.assertEqual(result[0][3], ["リビング"])

    def test_collect_top_target_candidates_summarizes_best_targets(self):
        candidates = en_ja.collect_top_target_candidates(
            sent_src=["clear"],
            pos_src=["a"],
            sent_tgt=["良い", "大切です"],
            pos_tgt=["a", "a"],
            sub2word_map_src=[0],
            sub2word_map_tgt=[0, 1],
            softmax_srctrg=torch.tensor([[0.5864, 0.3992]]),
            top_k=2,
        )
        self.assertEqual(candidates[0]["source_token"], "clear")
        self.assertEqual(candidates[0]["candidates"][0]["target_token"], "良い")
        self.assertAlmostEqual(candidates[0]["candidates"][0]["score"], 0.5864, places=4)

    def test_postprocessing_drops_group_without_content_on_target_side(self):
        result = en_ja.awesome_alignment_postprocessing(
            torch.tensor([[True]]),
            sub2word_map_src=[0],
            sub2word_map_tgt=[0],
            pos_src=["r"],
            pos_trg=[""],
            sent_src=["when"],
            sent_tgt=["と"],
            softmax_srctrg=torch.tensor([[1.0]]),
            softmax_trgsrc=torch.tensor([[1.0]]),
        )
        self.assertEqual(result, [])

    def test_postprocessing_drops_group_with_cross_pos_only_alignment(self):
        result = en_ja.awesome_alignment_postprocessing(
            torch.tensor([[True]]),
            sub2word_map_src=[0],
            sub2word_map_tgt=[0],
            pos_src=["v"],
            pos_trg=["n"],
            sent_src=["hidden"],
            sent_tgt=["非表示"],
            softmax_srctrg=torch.tensor([[0.1188]]),
            softmax_trgsrc=torch.tensor([[1.0]]),
        )
        self.assertEqual(result, [])

    def test_target_tokens_look_like_abstract_adjective_nominalization(self):
        self.assertTrue(
            en_ja.target_tokens_look_like_abstract_adjective_nominalization(
                ["厳密性"]
            )
        )
        self.assertFalse(
            en_ja.target_tokens_look_like_abstract_adjective_nominalization(
                ["方法"]
            )
        )

    def test_postprocessing_keeps_adjective_to_abstract_noun_alignment(self):
        result = en_ja.awesome_alignment_postprocessing(
            torch.tensor([[True]]),
            sub2word_map_src=[0],
            sub2word_map_tgt=[0],
            pos_src=["a"],
            pos_trg=["n"],
            sent_src=["rigorous"],
            sent_tgt=["厳密性"],
            softmax_srctrg=torch.tensor([[1.0]]),
            softmax_trgsrc=torch.tensor([[1.0]]),
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], ["rigorous"])
        self.assertEqual(result[0][3], ["厳密性"])

    def test_alignment_postprocessing_keeps_abstract_noun_as_adjective_relation(self):
        result = en_ja.alignment_postprocessing(
            [
                (
                    ["a"],
                    ["rigorous"],
                    ["n"],
                    ["厳密性"],
                    {},
                )
            ],
            {},
            test=True,
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "a")
        self.assertEqual(result[0][2], "rigorous")
        self.assertEqual(result[0][4], "厳密性")

    def test_should_suppress_precision_verb_pair_for_copula_noise(self):
        self.assertTrue(
            en_ja.should_suppress_precision_verb_pair("be", "鳴る", "なって")
        )

    def test_should_suppress_precision_verb_pair_for_contracted_copula_noise(self):
        self.assertTrue(
            en_ja.should_suppress_precision_verb_pair("'re", "有る", "あって")
        )

    def test_should_suppress_precision_verb_pair_for_get_eru_noise(self):
        self.assertTrue(
            en_ja.should_suppress_precision_verb_pair("get", "得る", "得")
        )

    def test_should_suppress_precision_verb_pair_for_get_keika_noise(self):
        self.assertTrue(
            en_ja.should_suppress_precision_verb_pair(
                "get", "程度経過する", "程度経過してくる"
            )
        )

    def test_should_suppress_low_value_noun_pair_for_generic_placeholder(self):
        self.assertTrue(
            en_ja.should_suppress_low_value_pair("n", "one", "もの")
        )

    def test_should_suppress_low_value_direct_pair_for_company_sha_noise(self):
        self.assertTrue(
            en_ja.should_suppress_low_value_pair("n", "company", "社")
        )

    def test_should_suppress_low_value_direct_pair_for_case_wake_noise(self):
        self.assertTrue(
            en_ja.should_suppress_low_value_pair("n", "case", "わけ")
        )

    def test_should_suppress_low_value_direct_pair_for_real_fan_noise(self):
        self.assertTrue(
            en_ja.should_suppress_low_value_pair("n", "real fan", "プチ芸能人")
        )

    def test_should_suppress_low_value_direct_pair_for_stop_naru_noise(self):
        self.assertTrue(
            en_ja.should_suppress_low_value_pair("v", "stop", "なる")
        )

    def test_should_suppress_low_value_direct_pair_for_duplicate_naru_noise(self):
        self.assertTrue(
            en_ja.should_suppress_low_value_pair("v", "duplicate", "なる")
        )

    def test_should_suppress_low_value_direct_pair_for_least_sukunai_noise(self):
        self.assertTrue(
            en_ja.should_suppress_low_value_pair("a", "least", "少ない")
        )

    def test_should_suppress_low_value_direct_pair_for_stream_use_noise(self):
        self.assertTrue(
            en_ja.should_suppress_low_value_pair("v", "stream", "使う")
        )

    def test_should_suppress_low_value_adverb_pair_for_personally_actual_noise(self):
        self.assertTrue(
            en_ja.should_suppress_low_value_pair("r", "personally", "実際")
        )

    def test_should_suppress_low_value_direct_pair_for_say_assertion_noise(self):
        self.assertTrue(
            en_ja.should_suppress_low_value_pair("v", "say", "言い切る")
        )

    def test_should_suppress_low_value_direct_pair_for_feel_nominalized_noise(self):
        self.assertTrue(
            en_ja.should_suppress_low_value_pair("v", "feel", "感じた事")
        )

    def test_should_suppress_competing_duplicate_source_pair(self):
        weak_candidate = {
            "pos_tag": "n",
            "source_surface": "outgoing",
            "source_normalized": "outgoing",
            "target_normalized": "送信受信",
            "average_alignment_score": 0.5091,
        }
        strong_candidate = {
            "pos_tag": "n",
            "source_surface": "outgoing",
            "source_normalized": "outgoing",
            "target_normalized": "送信メール",
            "average_alignment_score": 1.0,
        }
        grouped_candidates = {
            ("n", "outgoing"): [weak_candidate, strong_candidate]
        }
        self.assertTrue(
            en_ja.should_suppress_competing_duplicate_source_pair(
                weak_candidate, grouped_candidates
            )
        )
        self.assertFalse(
            en_ja.should_suppress_competing_duplicate_source_pair(
                strong_candidate, grouped_candidates
            )
        )

    def test_alignment_postprocessing_drops_weaker_competing_duplicate_source_pair(self):
        result = en_ja.alignment_postprocessing(
            [
                (
                    ["n"],
                    ["outgoing"],
                    ["n"],
                    ["送信受信"],
                    {"average_alignment_score": 0.5091},
                ),
                (
                    ["n"],
                    ["outgoing"],
                    ["n"],
                    ["送信メール"],
                    {"average_alignment_score": 1.0},
                ),
            ],
            {},
            test=True,
        )
        normalized_pairs = {(row[0], row[2], row[4]) for row in result}
        self.assertNotIn(("n", "outgoing", "送信受信"), normalized_pairs)
        self.assertIn(("n", "outgoing", "送信メール"), normalized_pairs)

    def test_alignment_postprocessing_normalizes_parenthesized_noun_phrase_lookup(self):
        result = en_ja.alignment_postprocessing(
            [
                (
                    ["n", "", "n", ""],
                    ["specifications", "(", "size", ")"],
                    ["n"],
                    ["仕様(サイズ)"],
                    {"average_alignment_score": 0.9999},
                )
            ],
            {},
            test=True,
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][2], "specifications (size)")
        self.assertEqual(
            en_ja.describe_final_alignment_item(result[0], test=True)["source_normalized"],
            "specification size",
        )

    def test_should_not_suppress_content_verb_pair(self):
        self.assertFalse(
            en_ja.should_suppress_precision_verb_pair("write", "書く", "書いて")
        )


if __name__ == "__main__":
    unittest.main()
