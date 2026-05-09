import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from ltc.staging.en_ja import (
    aggregate_bundle_payloads,
    format_inspection_text,
    inspect_staging_snapshot,
    load_staging_snapshot,
    write_aggregated_tables,
)


class EnJaStagingAggregationTest(unittest.TestCase):
    def test_aggregate_bundle_payloads_merges_counts_and_support(self):
        bundle_a = {
            "staging_tables": {
                "phrase_network_staging": [
                    {
                        "staging_action": "stage_phrase_candidate",
                        "pos_tag": "n",
                        "source_normalized": "voice input",
                        "target_normalized": "音声入力",
                        "occurrences": 2,
                        "case_count": 1,
                        "source_surfaces": "voice input",
                        "target_surfaces": "音声入力",
                        "case_names": "case_a",
                        "reasons": "phrase",
                    }
                ],
                "auto_component_word_staging": [
                    {
                        "staging_action": "stage_auto_component_candidate",
                        "pos_tag": "n",
                        "source_normalized": "voice",
                        "target_normalized": "音声",
                        "occurrences": 2,
                        "average_confidence": 0.9,
                        "case_count": 1,
                        "parent_phrase_count": 1,
                        "source_surfaces": "voice",
                        "target_surfaces": "音声",
                        "parent_phrases": "voice input -> 音声入力",
                        "case_names": "case_a",
                        "reasons": "aligned",
                    }
                ],
                "review_queue_staging": [
                    {
                        "staging_action": "needs_human_review",
                        "case_name": "case_r",
                        "pos_tag": "n",
                        "source_normalized": "example construction",
                        "target_normalized": "施工事例",
                        "confidence": 0.8,
                        "reason": "needs review",
                        "component_projection_pairs": "construction->施工 | example->事例",
                        "source_text": "A",
                        "target_text": "B",
                    }
                ],
            }
        }
        bundle_b = {
            "staging_tables": {
                "phrase_network_staging": [
                    {
                        "staging_action": "stage_phrase_candidate",
                        "pos_tag": "n",
                        "source_normalized": "voice input",
                        "target_normalized": "音声入力",
                        "occurrences": 1,
                        "case_count": 1,
                        "source_surfaces": "voice inputs",
                        "target_surfaces": "音声入力",
                        "case_names": "case_b",
                        "reasons": "phrase",
                    }
                ],
                "auto_component_word_staging": [
                    {
                        "staging_action": "stage_auto_component_candidate",
                        "pos_tag": "n",
                        "source_normalized": "voice",
                        "target_normalized": "音声",
                        "occurrences": 1,
                        "average_confidence": 1.0,
                        "case_count": 1,
                        "parent_phrase_count": 1,
                        "source_surfaces": "voice",
                        "target_surfaces": "音声",
                        "parent_phrases": "voice input -> 音声入力",
                        "case_names": "case_b",
                        "reasons": "aligned",
                    },
                    {
                        "staging_action": "stage_auto_component_candidate",
                        "pos_tag": "n",
                        "source_normalized": "input",
                        "target_normalized": "入力",
                        "occurrences": 1,
                        "average_confidence": 0.95,
                        "case_count": 1,
                        "parent_phrase_count": 1,
                        "source_surfaces": "input",
                        "target_surfaces": "入力",
                        "parent_phrases": "voice input -> 音声入力",
                        "case_names": "case_b",
                        "reasons": "aligned",
                    },
                ],
                "review_queue_staging": [
                    {
                        "staging_action": "needs_human_review",
                        "case_name": "case_r",
                        "pos_tag": "n",
                        "source_normalized": "example construction",
                        "target_normalized": "施工事例",
                        "confidence": 0.8,
                        "reason": "needs review",
                        "component_projection_pairs": "construction->施工 | example->事例",
                        "source_text": "A",
                        "target_text": "B",
                    }
                ],
            }
        }

        aggregated = aggregate_bundle_payloads([bundle_a, bundle_b])
        self.assertEqual(aggregated["summary"]["bundles"], 2)
        self.assertEqual(aggregated["summary"]["phrase_network_rows"], 1)
        self.assertEqual(aggregated["summary"]["auto_component_rows"], 2)
        self.assertEqual(aggregated["summary"]["ready_auto_component_rows"], 1)
        self.assertEqual(aggregated["summary"]["candidate_auto_component_rows"], 1)
        self.assertEqual(aggregated["summary"]["existing_word_network_rows"], 0)
        self.assertEqual(aggregated["summary"]["promotion_ready_word_network_rows"], 1)
        self.assertEqual(aggregated["summary"]["promotion_exact_match_rows"], 0)
        self.assertEqual(aggregated["summary"]["promotion_novel_rows"], 1)
        self.assertEqual(aggregated["summary"]["promotion_proposal_rows"], 1)
        self.assertEqual(aggregated["summary"]["promotion_followup_rows"], 0)
        self.assertEqual(aggregated["summary"]["review_rows"], 1)
        phrase_row = aggregated["phrase_network_rows"][0]
        self.assertEqual(phrase_row["occurrences"], 3)
        self.assertEqual(phrase_row["case_count"], 2)
        auto_voice = next(
            row
            for row in aggregated["auto_component_rows"]
            if row["source_normalized"] == "voice"
        )
        self.assertAlmostEqual(auto_voice["average_confidence"], (0.9 * 2 + 1.0) / 3)
        self.assertEqual(auto_voice["promotion_bucket"], "ready")

    def test_write_aggregated_tables_writes_expected_files(self):
        aggregated = {
            "summary": {
                "bundles": 1,
                "phrase_network_rows": 1,
                "auto_component_rows": 1,
                "ready_auto_component_rows": 1,
                "candidate_auto_component_rows": 0,
                "existing_word_network_rows": 1,
                "promotion_ready_word_network_rows": 1,
                "promotion_exact_match_rows": 1,
                "promotion_source_overlap_rows": 0,
                "promotion_target_overlap_rows": 0,
                "promotion_source_and_target_overlap_rows": 0,
                "promotion_novel_rows": 0,
                "promotion_proposal_rows": 0,
                "promotion_followup_rows": 0,
                "combined_network_rows": 2,
                "review_rows": 1,
            },
            "phrase_network_rows": [
                {
                    "staging_id": 0,
                    "candidate_kind": "phrase",
                    "pos_tag": "n",
                    "source_normalized": "voice input",
                    "target_normalized": "音声入力",
                    "occurrences": 1,
                    "case_count": 1,
                    "source_surfaces": "voice input",
                    "target_surfaces": "音声入力",
                    "case_names": "case_a",
                    "reasons": "phrase",
                }
            ],
            "auto_component_rows": [
                {
                    "staging_id": 0,
                    "candidate_kind": "auto_component_word",
                    "pos_tag": "n",
                    "source_normalized": "voice",
                    "target_normalized": "音声",
                    "occurrences": 1,
                    "average_confidence": 1.0,
                    "promotion_bucket": "ready",
                    "case_count": 1,
                    "parent_phrase_count": 1,
                    "source_surfaces": "voice",
                    "target_surfaces": "音声",
                    "parent_phrases": "voice input -> 音声入力",
                    "case_names": "case_a",
                    "reasons": "aligned",
                }
            ],
            "combined_network_rows": [
                {
                    "staging_id": 0,
                    "candidate_kind": "phrase",
                    "pos_tag": "n",
                    "source_normalized": "voice input",
                    "target_normalized": "音声入力",
                    "occurrences": 1,
                    "average_confidence": "",
                    "support": 1,
                    "notes": "phrase",
                }
            ],
            "ready_auto_component_rows": [
                {
                    "staging_id": 0,
                    "candidate_kind": "auto_component_word",
                    "pos_tag": "n",
                    "source_normalized": "voice",
                    "target_normalized": "音声",
                    "occurrences": 1,
                    "average_confidence": 1.0,
                    "promotion_bucket": "ready",
                    "case_count": 1,
                    "parent_phrase_count": 1,
                    "source_surfaces": "voice",
                    "target_surfaces": "音声",
                    "parent_phrases": "voice input -> 音声入力",
                    "case_names": "case_a",
                    "reasons": "aligned",
                }
            ],
            "candidate_auto_component_rows": [],
            "existing_word_network_rows": [
                {
                    "existing_id": 0,
                    "candidate_kind": "existing_word",
                    "pos_tag": "n",
                    "source_normalized": "voice",
                    "target_normalized": "音声",
                    "occurrences": 1,
                    "average_confidence": 1.0,
                    "case_count": 1,
                    "source_surfaces": "voice",
                    "target_surfaces": "音声",
                    "case_names": "case_a",
                    "reasons": "legacy",
                }
            ],
            "promotion_ready_word_network_rows": [
                {
                    "promotion_id": 0,
                    "promotion_source": "ready_auto_component",
                    "pos_tag": "n",
                    "source_normalized": "voice",
                    "target_normalized": "音声",
                    "occurrences": 1,
                    "average_confidence": 1.0,
                    "support": 1,
                    "parent_phrase_count": 1,
                    "source_surfaces": "voice",
                    "target_surfaces": "音声",
                    "parent_phrases": "voice input -> 音声入力",
                    "case_names": "case_a",
                    "notes": "aligned",
                }
            ],
            "promotion_diff_rows": [
                {
                    "diff_id": 0,
                    "status": "exact_match",
                    "pos_tag": "n",
                    "source_normalized": "voice",
                    "target_normalized": "音声",
                    "occurrences": 1,
                    "average_confidence": 1.0,
                    "support": 1,
                    "source_surfaces": "voice",
                    "target_surfaces": "音声",
                    "parent_phrases": "voice input -> 音声入力",
                    "case_names": "case_a",
                    "existing_targets_for_source": "",
                    "existing_sources_for_target": "",
                }
            ],
            "promotion_proposal_rows": [],
            "promotion_followup_rows": [],
            "review_rows": [
                {
                    "review_id": 0,
                    "staging_action": "needs_human_review",
                    "case_name": "case_r",
                    "pos_tag": "n",
                    "source_normalized": "example construction",
                    "target_normalized": "施工事例",
                    "confidence": 0.8,
                    "reason": "needs review",
                    "component_projection_pairs": "construction->施工 | example->事例",
                    "source_text": "A",
                    "target_text": "B",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            write_aggregated_tables(temp_dir, aggregated)
            output_dir = Path(temp_dir)
            for name in (
                "summary.json",
                "phrase-network-relations.csv",
                "auto-component-word-relations.csv",
                "ready-auto-component-word-relations.csv",
                "candidate-auto-component-word-relations.csv",
                "existing-word-network.csv",
                "promotion-ready-word-network.csv",
                "promotion-ready-diff.csv",
                "promotion-ready-proposals.csv",
                "promotion-followup.csv",
                "lexical-network-staging.csv",
                "review-queue.csv",
            ):
                self.assertTrue((output_dir / name).exists(), name)
            summary = json.loads((output_dir / "summary.json").read_text())
            self.assertEqual(summary["bundles"], 1)

    def test_load_staging_snapshot_supports_bundle_and_aggregated_dirs(self):
        bundle = {
            "staging_tables": {
                "phrase_network_staging": [
                    {
                        "staging_action": "stage_phrase_candidate",
                        "pos_tag": "n",
                        "source_normalized": "voice input",
                        "target_normalized": "音声入力",
                        "occurrences": 1,
                        "case_count": 1,
                        "source_surfaces": "voice input",
                        "target_surfaces": "音声入力",
                        "case_names": "case_a",
                        "reasons": "phrase",
                    }
                ],
                "auto_component_word_staging": [],
                "review_queue_staging": [],
            }
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_dir = Path(temp_dir) / "bundle"
            bundle_dir.mkdir()
            (bundle_dir / "bundle.json").write_text(json.dumps(bundle, ensure_ascii=False))
            snapshot = load_staging_snapshot(bundle_dir)
            self.assertEqual(snapshot["source_kind"], "bundle_dir")
            self.assertEqual(snapshot["summary"]["bundles"], 1)

            aggregate_dir = Path(temp_dir) / "aggregated"
            write_aggregated_tables(aggregate_dir, aggregate_bundle_payloads([bundle]))
            snapshot = load_staging_snapshot(aggregate_dir)
            self.assertEqual(snapshot["source_kind"], "aggregated_dir")
            self.assertEqual(len(snapshot["phrase_network_rows"]), 1)
            self.assertIn("ready_auto_component_rows", snapshot)
            self.assertIn("promotion_ready_word_network_rows", snapshot)
            self.assertIn("existing_word_network_rows", snapshot)
            self.assertIn("promotion_diff_rows", snapshot)

    def test_inspect_staging_snapshot_filters_query_and_formats_text(self):
        snapshot = {
            "source_kind": "aggregated_dir",
            "input_dir": "/tmp/staging",
            "summary": {
                "phrase_network_rows": 1,
                "auto_component_rows": 1,
                "ready_auto_component_rows": 0,
                "candidate_auto_component_rows": 1,
                "existing_word_network_rows": 1,
                "promotion_ready_word_network_rows": 0,
                "promotion_exact_match_rows": 0,
                "promotion_source_overlap_rows": 0,
                "promotion_target_overlap_rows": 0,
                "promotion_source_and_target_overlap_rows": 0,
                "promotion_novel_rows": 0,
                "promotion_proposal_rows": 0,
                "promotion_followup_rows": 0,
                "combined_network_rows": 2,
                "review_rows": 1,
            },
            "phrase_network_rows": [
                {
                    "candidate_kind": "phrase",
                    "pos_tag": "n",
                    "source_normalized": "game title",
                    "target_normalized": "ゲームタイトル",
                    "occurrences": 2,
                    "case_count": 1,
                    "source_surfaces": "game titles",
                    "target_surfaces": "ゲームタイトル",
                    "case_names": "case_a",
                    "reasons": "phrase",
                }
            ],
            "auto_component_rows": [
                {
                    "candidate_kind": "auto_component_word",
                    "pos_tag": "n",
                    "source_normalized": "voice",
                    "target_normalized": "音声",
                    "occurrences": 3,
                    "average_confidence": 0.95,
                    "promotion_bucket": "candidate",
                    "case_count": 2,
                    "source_surfaces": "voice",
                    "target_surfaces": "音声",
                    "parent_phrases": "voice input -> 音声入力",
                    "case_names": "case_b | case_c",
                    "reasons": "aligned",
                }
            ],
            "combined_network_rows": [],
            "ready_auto_component_rows": [],
            "candidate_auto_component_rows": [],
            "existing_word_network_rows": [],
            "promotion_ready_word_network_rows": [],
            "promotion_diff_rows": [],
            "promotion_proposal_rows": [],
            "promotion_followup_rows": [],
            "review_rows": [
                {
                    "case_name": "construction_case",
                    "source_normalized": "example construction",
                    "target_normalized": "施工事例",
                    "confidence": 0.8,
                    "reason": "needs review",
                    "component_projection_pairs": "construction->施工 | example->事例",
                }
            ],
        }
        report = inspect_staging_snapshot(
            snapshot,
            kind="all",
            query="voice",
            min_occurrences=2,
            min_support=1,
            promotion_bucket="candidate",
            limit=5,
        )
        self.assertEqual(report["sections"]["auto_component_rows"]["matching_count"], 1)
        self.assertEqual(report["sections"]["phrase_network_rows"]["matching_count"], 0)
        self.assertEqual(report["sections"]["review_rows"]["matching_count"], 0)
        text = format_inspection_text(report)
        self.assertIn("[auto component rows]", text)
        self.assertIn("voice -> 音声", text)
        self.assertIn("promotion=candidate", text)
        self.assertIn("promotion bucket: candidate", text)
        self.assertIn("[review rows] matching=0 displayed=0", text)

    def test_inspect_staging_snapshot_can_show_promotion_ready_rows(self):
        snapshot = {
            "source_kind": "aggregated_dir",
            "input_dir": "/tmp/staging",
            "summary": {
                "phrase_network_rows": 0,
                "auto_component_rows": 1,
                "ready_auto_component_rows": 1,
                "candidate_auto_component_rows": 0,
                "existing_word_network_rows": 1,
                "promotion_ready_word_network_rows": 1,
                "promotion_exact_match_rows": 0,
                "promotion_source_overlap_rows": 0,
                "promotion_target_overlap_rows": 0,
                "promotion_source_and_target_overlap_rows": 0,
                "promotion_novel_rows": 1,
                "promotion_proposal_rows": 1,
                "promotion_followup_rows": 0,
                "combined_network_rows": 1,
                "review_rows": 0,
            },
            "phrase_network_rows": [],
            "auto_component_rows": [],
            "ready_auto_component_rows": [],
            "candidate_auto_component_rows": [],
            "combined_network_rows": [],
            "existing_word_network_rows": [],
            "promotion_ready_word_network_rows": [
                {
                    "promotion_id": 0,
                    "promotion_source": "ready_auto_component",
                    "pos_tag": "n",
                    "source_normalized": "voice",
                    "target_normalized": "音声",
                    "occurrences": 1,
                    "average_confidence": 0.99,
                    "support": 1,
                    "parent_phrase_count": 1,
                    "source_surfaces": "voice",
                    "target_surfaces": "音声",
                    "parent_phrases": "voice input -> 音声入力",
                    "case_names": "case_a",
                    "notes": "aligned",
                }
            ],
            "promotion_diff_rows": [],
            "promotion_proposal_rows": [
                {
                    "proposal_id": 0,
                    "candidate_kind": "promotion_proposal",
                    "proposal_action": "propose_promote_to_word_network",
                    "pos_tag": "n",
                    "source_normalized": "voice",
                    "target_normalized": "音声",
                    "occurrences": 1,
                    "average_confidence": 0.99,
                    "support": 1,
                    "source_surfaces": "voice",
                    "target_surfaces": "音声",
                    "parent_phrases": "voice input -> 音声入力",
                    "case_names": "case_a",
                    "notes": "novel_ready_component_projection",
                }
            ],
            "promotion_followup_rows": [],
            "review_rows": [],
        }
        report = inspect_staging_snapshot(snapshot, kind="promotion", limit=5)
        self.assertEqual(
            report["sections"]["promotion_ready_word_network_rows"]["matching_count"], 1
        )
        text = format_inspection_text(report)
        self.assertIn("[promotion-ready word rows]", text)
        self.assertIn("voice -> 音声", text)

    def test_inspect_staging_snapshot_can_show_promotion_diff_rows(self):
        snapshot = {
            "source_kind": "aggregated_dir",
            "input_dir": "/tmp/staging",
            "summary": {
                "phrase_network_rows": 0,
                "auto_component_rows": 0,
                "ready_auto_component_rows": 0,
                "candidate_auto_component_rows": 0,
                "existing_word_network_rows": 1,
                "promotion_ready_word_network_rows": 1,
                "promotion_exact_match_rows": 0,
                "promotion_source_overlap_rows": 1,
                "promotion_target_overlap_rows": 0,
                "promotion_source_and_target_overlap_rows": 0,
                "promotion_novel_rows": 0,
                "promotion_proposal_rows": 0,
                "promotion_followup_rows": 1,
                "combined_network_rows": 0,
                "review_rows": 0,
            },
            "phrase_network_rows": [],
            "auto_component_rows": [],
            "ready_auto_component_rows": [],
            "candidate_auto_component_rows": [],
            "existing_word_network_rows": [],
            "promotion_ready_word_network_rows": [],
            "promotion_diff_rows": [
                {
                    "diff_id": 0,
                    "status": "source_overlap_different_target",
                    "pos_tag": "n",
                    "source_normalized": "voice",
                    "target_normalized": "音",
                    "occurrences": 1,
                    "average_confidence": 1.0,
                    "support": 1,
                    "source_surfaces": "voice",
                    "target_surfaces": "音",
                    "parent_phrases": "voice input -> 音声入力",
                    "case_names": "case_a",
                    "existing_targets_for_source": "音声",
                    "existing_sources_for_target": "",
                }
            ],
            "promotion_proposal_rows": [],
            "promotion_followup_rows": [
                {
                    "followup_id": 0,
                    "candidate_kind": "promotion_followup",
                    "followup_action": "requires_existing_network_decision",
                    "status": "source_overlap_different_target",
                    "pos_tag": "n",
                    "source_normalized": "voice",
                    "target_normalized": "音",
                    "occurrences": 1,
                    "average_confidence": 1.0,
                    "support": 1,
                    "source_surfaces": "voice",
                    "target_surfaces": "音",
                    "parent_phrases": "voice input -> 音声入力",
                    "case_names": "case_a",
                    "existing_targets_for_source": "音声",
                    "existing_sources_for_target": "",
                    "notes": "source_overlap_different_target",
                }
            ],
            "combined_network_rows": [],
            "review_rows": [],
        }
        report = inspect_staging_snapshot(snapshot, kind="promotion-diff", limit=5)
        self.assertEqual(report["sections"]["promotion_diff_rows"]["matching_count"], 1)
        text = format_inspection_text(report)
        self.assertIn("[promotion diff rows]", text)
        self.assertIn("source_overlap_different_target", text)

    def test_inspect_staging_snapshot_can_show_promotion_proposal_rows(self):
        snapshot = {
            "source_kind": "aggregated_dir",
            "input_dir": "/tmp/staging",
            "summary": {
                "phrase_network_rows": 0,
                "auto_component_rows": 0,
                "ready_auto_component_rows": 0,
                "candidate_auto_component_rows": 0,
                "existing_word_network_rows": 0,
                "promotion_ready_word_network_rows": 1,
                "promotion_exact_match_rows": 0,
                "promotion_source_overlap_rows": 0,
                "promotion_target_overlap_rows": 0,
                "promotion_source_and_target_overlap_rows": 0,
                "promotion_novel_rows": 1,
                "promotion_proposal_rows": 1,
                "promotion_followup_rows": 0,
                "combined_network_rows": 0,
                "review_rows": 0,
            },
            "phrase_network_rows": [],
            "auto_component_rows": [],
            "ready_auto_component_rows": [],
            "candidate_auto_component_rows": [],
            "existing_word_network_rows": [],
            "promotion_ready_word_network_rows": [],
            "promotion_diff_rows": [],
            "promotion_proposal_rows": [
                {
                    "proposal_id": 0,
                    "candidate_kind": "promotion_proposal",
                    "proposal_action": "propose_promote_to_word_network",
                    "pos_tag": "n",
                    "source_normalized": "input",
                    "target_normalized": "入力",
                    "occurrences": 1,
                    "average_confidence": 1.0,
                    "support": 1,
                    "source_surfaces": "input",
                    "target_surfaces": "入力",
                    "parent_phrases": "voice input -> 音声入力",
                    "case_names": "case_a",
                    "notes": "novel_ready_component_projection",
                }
            ],
            "promotion_followup_rows": [],
            "combined_network_rows": [],
            "review_rows": [],
        }
        report = inspect_staging_snapshot(snapshot, kind="promotion-proposal", limit=5)
        self.assertEqual(report["sections"]["promotion_proposal_rows"]["matching_count"], 1)
        text = format_inspection_text(report)
        self.assertIn("[promotion proposal rows]", text)
        self.assertIn("input -> 入力", text)

    def test_inspect_staging_snapshot_can_show_promotion_followup_rows(self):
        snapshot = {
            "source_kind": "aggregated_dir",
            "input_dir": "/tmp/staging",
            "summary": {
                "phrase_network_rows": 0,
                "auto_component_rows": 0,
                "ready_auto_component_rows": 0,
                "candidate_auto_component_rows": 0,
                "existing_word_network_rows": 1,
                "promotion_ready_word_network_rows": 1,
                "promotion_exact_match_rows": 0,
                "promotion_source_overlap_rows": 0,
                "promotion_target_overlap_rows": 1,
                "promotion_source_and_target_overlap_rows": 0,
                "promotion_novel_rows": 0,
                "promotion_proposal_rows": 0,
                "promotion_followup_rows": 1,
                "combined_network_rows": 0,
                "review_rows": 0,
            },
            "phrase_network_rows": [],
            "auto_component_rows": [],
            "ready_auto_component_rows": [],
            "candidate_auto_component_rows": [],
            "existing_word_network_rows": [],
            "promotion_ready_word_network_rows": [],
            "promotion_diff_rows": [],
            "promotion_proposal_rows": [],
            "promotion_followup_rows": [
                {
                    "followup_id": 0,
                    "candidate_kind": "promotion_followup",
                    "followup_action": "requires_existing_network_decision",
                    "status": "target_overlap_different_source",
                    "pos_tag": "n",
                    "source_normalized": "post",
                    "target_normalized": "記事",
                    "occurrences": 1,
                    "average_confidence": 1.0,
                    "support": 1,
                    "source_surfaces": "post",
                    "target_surfaces": "記事",
                    "parent_phrases": "blog post -> ブログ記事",
                    "case_names": "case_b",
                    "existing_targets_for_source": "",
                    "existing_sources_for_target": "article",
                    "notes": "target_overlap_different_source",
                }
            ],
            "combined_network_rows": [],
            "review_rows": [],
        }
        report = inspect_staging_snapshot(snapshot, kind="promotion-followup", limit=5)
        self.assertEqual(report["sections"]["promotion_followup_rows"]["matching_count"], 1)
        text = format_inspection_text(report)
        self.assertIn("[promotion followup rows]", text)
        self.assertIn("existing sources for target: article", text)


if __name__ == "__main__":
    unittest.main()
