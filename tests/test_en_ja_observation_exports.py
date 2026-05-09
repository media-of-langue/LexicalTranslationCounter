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

from ltc.observation_exports.en_ja import (
    build_candidate_tables,
    build_bundle_from_documents,
    build_staging_tables,
    write_bundle_directory,
)


class EnJaObservationExportsTest(unittest.TestCase):
    def test_build_candidate_tables_separates_auto_and_review_rows(self):
        documents = [
            {
                "request": {"name": "case_one", "source": "A", "target": "B"},
                "word_observations": [],
                "phrase_observations": [],
                "lexicalization_decisions": [
                    {
                        "recommended_action": "register_phrase",
                        "pos_tag": "n",
                        "source_normalized": "game title",
                        "target_normalized": "ゲームタイトル",
                        "source_surface": "game titles",
                        "target_surface": "ゲームタイトル",
                        "reason": "phrase candidate",
                    },
                    {
                        "recommended_action": "project_components_auto",
                        "pos_tag": "n",
                        "source_normalized": "game title",
                        "target_normalized": "ゲームタイトル",
                        "source_surface": "game titles",
                        "target_surface": "ゲームタイトル",
                        "component_projections": [
                            {
                                "pos_tag": "n",
                                "source_normalized": "game",
                                "target_normalized": "ゲーム",
                                "source_surface": "game",
                                "target_surface": "ゲーム",
                                "reason": "aligned_noun_compound_projection",
                                "confidence": 1.0,
                            },
                            {
                                "pos_tag": "n",
                                "source_normalized": "title",
                                "target_normalized": "タイトル",
                                "source_surface": "titles",
                                "target_surface": "タイトル",
                                "reason": "aligned_noun_compound_projection",
                                "confidence": 1.0,
                            },
                        ],
                    },
                ],
            },
            {
                "request": {
                    "name": "case_two",
                    "source": "For example",
                    "target": "施工事例",
                },
                "word_observations": [],
                "phrase_observations": [],
                "lexicalization_decisions": [
                    {
                        "recommended_action": "project_components_needs_review",
                        "pos_tag": "n",
                        "source_normalized": "example construction",
                        "target_normalized": "施工事例",
                        "source_surface": "examples construction",
                        "target_surface": "施工事例",
                        "reason": "needs review",
                        "confidence": 0.88,
                        "component_projections": [
                            {
                                "pos_tag": "n",
                                "source_normalized": "construction",
                                "target_normalized": "施工",
                                "source_surface": "construction",
                                "target_surface": "施工",
                                "reason": "reverse_of_genitive_compound_projection",
                                "confidence": 0.88,
                            }
                        ],
                    }
                ],
            },
            {
                "request": {
                    "name": "case_three",
                    "source": "Again",
                    "target": "ゲームタイトル",
                },
                "word_observations": [],
                "phrase_observations": [],
                "lexicalization_decisions": [
                    {
                        "recommended_action": "project_components_needs_review",
                        "pos_tag": "n",
                        "source_normalized": "game title",
                        "target_normalized": "ゲームタイトル",
                        "source_surface": "game title",
                        "target_surface": "ゲームタイトル",
                        "reason": "duplicate low-confidence sighting",
                        "confidence": 0.7,
                        "component_projections": [
                            {
                                "pos_tag": "n",
                                "source_normalized": "game",
                                "target_normalized": "ゲーム",
                                "source_surface": "game",
                                "target_surface": "ゲーム",
                                "reason": "aligned_noun_compound_projection",
                                "confidence": 0.7,
                            }
                        ],
                    }
                ],
            },
        ]

        tables = build_candidate_tables(documents)
        self.assertEqual(len(tables["phrase_network_candidates"]), 1)
        self.assertEqual(
            tables["phrase_network_candidates"][0]["source_normalized"], "game title"
        )
        self.assertEqual(len(tables["auto_component_word_candidates"]), 2)
        self.assertEqual(
            {
                (row["source_normalized"], row["target_normalized"])
                for row in tables["auto_component_word_candidates"]
            },
            {("game", "ゲーム"), ("title", "タイトル")},
        )
        self.assertEqual(len(tables["review_queue"]), 2)
        self.assertEqual(
            tables["review_queue"][0]["source_normalized"], "example construction"
        )
        staging = build_staging_tables(documents, tables)
        self.assertEqual(len(staging["phrase_network_staging"]), 1)
        self.assertEqual(len(staging["auto_component_word_staging"]), 2)
        self.assertEqual(len(staging["review_queue_staging"]), 1)
        self.assertEqual(
            staging["auto_component_word_staging"][0]["staging_action"],
            "stage_auto_component_candidate",
        )

    def test_write_bundle_directory_writes_candidate_files(self):
        bundle = build_bundle_from_documents(
            [
                {
                    "request": {"name": "case_one", "source": "A", "target": "B"},
                    "word_observations": [],
                    "phrase_observations": [],
                    "lexicalization_decisions": [
                        {
                            "recommended_action": "register_phrase",
                            "pos_tag": "n",
                            "source_normalized": "voice input",
                            "target_normalized": "音声入力",
                            "source_surface": "voice input",
                            "target_surface": "音声入力",
                            "reason": "phrase candidate",
                        }
                    ],
                }
            ],
            suite="core",
            cases_path=None,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            write_bundle_directory(bundle, temp_dir)
            output_dir = Path(temp_dir)
            for name in (
                "bundle.json",
                "documents.jsonl",
                "phrase-network-candidates.jsonl",
                "auto-component-word-candidates.jsonl",
                "review-queue.jsonl",
                "phrase-network-staging.csv",
                "auto-component-word-staging.csv",
                "review-queue.csv",
            ):
                self.assertTrue((output_dir / name).exists(), name)
            bundle_payload = json.loads((output_dir / "bundle.json").read_text())
            self.assertEqual(bundle_payload["suite"], "core")
            self.assertIn("staging_tables", bundle_payload)
            phrase_rows = [
                json.loads(line)
                for line in (output_dir / "phrase-network-candidates.jsonl")
                .read_text()
                .splitlines()
                if line.strip()
            ]
            self.assertEqual(phrase_rows[0]["source_normalized"], "voice input")
            phrase_staging_lines = (
                output_dir / "phrase-network-staging.csv"
            ).read_text().splitlines()
            self.assertGreaterEqual(len(phrase_staging_lines), 2)


if __name__ == "__main__":
    unittest.main()
