import os
import sys
import unittest
from types import SimpleNamespace


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from ltc.cli import compare_en_ja_models


class CompareEnJaModelsTest(unittest.TestCase):
    def test_build_inspect_command_for_case(self):
        args = SimpleNamespace(
            case="copula_adjective",
            source=None,
            target=None,
            cases="/tmp/cases.json",
        )
        command = compare_en_ja_models.build_inspect_command(args)
        self.assertIn("--case", command)
        self.assertIn("copula_adjective", command)
        self.assertIn("--format", command)
        self.assertIn("json", command)

    def test_build_payload_reports_pair_and_candidate_diffs(self):
        args = SimpleNamespace(
            left_label="smoke",
            right_label="prod",
            left_model="bert-base-multilingual-cased",
            right_model="/tmp/awesome",
            left_backend="awesome",
            right_backend="simalign",
            left_simalign_model="bert",
            right_simalign_model="xlmr",
        )
        left_payload = {
            "request": {
                "name": "demo",
                "notes": "demo note",
                "source": "It is important.",
                "target": "重要です。",
            },
            "runtime": {"note": "smoke/dev model"},
            "final_pairs": [
                {
                    "pos_tag": "a",
                    "source_normalized": "important",
                    "target_normalized": "重要",
                }
            ],
            "source_target_candidates": [
                {
                    "source_index": 0,
                    "source_token": "clear",
                    "source_pos_tag": "a",
                    "candidates": [
                        {
                            "target_token": "良い",
                            "target_pos_tag": "a",
                            "score": 0.58,
                        }
                    ],
                }
            ],
        }
        right_payload = {
            "request": left_payload["request"],
            "runtime": {"note": "production model"},
            "final_pairs": [
                {
                    "pos_tag": "a",
                    "source_normalized": "important",
                    "target_normalized": "大切",
                }
            ],
            "source_target_candidates": [
                {
                    "source_index": 0,
                    "source_token": "clear",
                    "source_pos_tag": "a",
                    "candidates": [
                        {
                            "target_token": "はっきりして",
                            "target_pos_tag": "v",
                            "score": 0.72,
                        }
                    ],
                }
            ],
        }

        payload = compare_en_ja_models.build_payload(args, left_payload, right_payload)
        self.assertEqual(payload["only_left_pairs"], [("a", "important", "重要")])
        self.assertEqual(payload["only_right_pairs"], [("a", "important", "大切")])
        self.assertEqual(payload["left"]["model"], "bert-base-multilingual-cased")
        self.assertEqual(payload["right"]["model"], "xlmr")
        self.assertEqual(len(payload["candidate_differences"]), 1)
        self.assertEqual(
            payload["candidate_differences"][0]["left"]["target_token"], "良い"
        )

    def test_format_text_includes_top_candidate_diff(self):
        payload = {
            "request": {
                "name": "demo",
                "notes": None,
                "source": "src",
                "target": "tgt",
            },
            "left": {
                "label": "smoke",
                "model": "bert-base-multilingual-cased",
                "backend": "awesome",
                "runtime": {"note": "smoke/dev"},
                "final_pairs": [("a", "important", "重要")],
            },
            "right": {
                "label": "prod",
                "model": "/tmp/awesome",
                "backend": "simalign",
                "runtime": {"note": "production"},
                "final_pairs": [("a", "important", "大切")],
            },
            "only_left_pairs": [("a", "important", "重要")],
            "only_right_pairs": [("a", "important", "大切")],
            "candidate_differences": [
                {
                    "source_index": 5,
                    "source_token": "clear",
                    "source_pos_tag": "a",
                    "left": {
                        "target_token": "良い",
                        "target_pos_tag": "a",
                        "score": 0.58,
                    },
                    "right": {
                        "target_token": "はっきりして",
                        "target_pos_tag": "v",
                        "score": 0.72,
                    },
                }
            ],
        }
        text = compare_en_ja_models.format_text(payload)
        self.assertIn("[top candidate diff]", text)
        self.assertIn("clear [a]", text)
        self.assertIn("backend: awesome", text)
        self.assertIn("backend: simalign", text)
        self.assertIn("smoke: 良い [a] 0.5800", text)
        self.assertIn("prod: はっきりして [v] 0.7200", text)


if __name__ == "__main__":
    unittest.main()
