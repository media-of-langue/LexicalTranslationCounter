import json
import os
import sys
import unittest
from argparse import Namespace


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from ltc.cli import compare_en_ja_corpus_models


class CompareEnJaCorpusModelsTest(unittest.TestCase):
    def test_build_audit_command_passes_selection_and_seed(self):
        args = Namespace(
            input="input.csv",
            limit=12,
            row_id=["3"],
            selection="random",
            seed=23,
        )
        command = compare_en_ja_corpus_models.build_audit_command(args)

        self.assertEqual(command[:4], [sys.executable, "-m", "ltc.cli.audit_en_ja_corpus", "--input"])
        self.assertIn("--selection", command)
        self.assertIn("random", command)
        self.assertIn("--seed", command)
        self.assertIn("23", command)
        self.assertIn("--row-id", command)

    def test_build_payload_counts_same_and_different_rows(self):
        left_payload = {
            "runtime": {"note": "left note"},
            "rows": [
                {
                    "corpus_id": "1",
                    "source": "src1",
                    "target": "tgt1",
                    "actual_pairs": [{"pos": "n", "src": "water", "tgt": "水"}],
                },
                {
                    "corpus_id": "2",
                    "source": "src2",
                    "target": "tgt2",
                    "actual_pairs": [{"pos": "v", "src": "drink", "tgt": "飲む"}],
                },
            ],
        }
        right_payload = {
            "runtime": {"note": "right note"},
            "rows": [
                {
                    "corpus_id": "1",
                    "source": "src1",
                    "target": "tgt1",
                    "actual_pairs": [{"pos": "n", "src": "water", "tgt": "水"}],
                },
                {
                    "corpus_id": "2",
                    "source": "src2",
                    "target": "tgt2",
                    "actual_pairs": [{"pos": "n", "src": "tea", "tgt": "お茶"}],
                },
            ],
        }
        args = type(
            "Args",
            (),
            {
                "left_label": "smoke",
                "left_model": "bert-base-multilingual-cased",
                "right_label": "production",
                "right_model": "models/en-ja/awesome-align/production",
            },
        )()
        payload = compare_en_ja_corpus_models.build_payload(args, left_payload, right_payload)

        self.assertEqual(payload["summary"]["rows_compared"], 2)
        self.assertEqual(payload["summary"]["same_rows"], 1)
        self.assertEqual(payload["summary"]["different_rows"], 1)
        self.assertEqual(payload["summary"]["rows_with_only_left_pairs"], 1)
        self.assertEqual(payload["summary"]["rows_with_only_right_pairs"], 1)
        self.assertEqual(payload["summary"]["total_only_left_pairs"], 1)
        self.assertEqual(payload["summary"]["total_only_right_pairs"], 1)
        differing = [row for row in payload["rows"] if not row["same"]][0]
        self.assertEqual(differing["corpus_id"], "2")
        self.assertEqual(differing["only_left_pairs"], [("v", "drink", "飲む")])
        self.assertEqual(differing["only_right_pairs"], [("n", "tea", "お茶")])

    def test_format_text_omits_same_rows_when_requested(self):
        payload = {
            "left": {"label": "smoke", "model": "smoke-model", "runtime": {"note": "left"}},
            "right": {"label": "production", "model": "prod-model", "runtime": {"note": "right"}},
            "summary": {
                "rows_compared": 2,
                "same_rows": 1,
                "different_rows": 1,
                "rows_with_only_left_pairs": 1,
                "rows_with_only_right_pairs": 1,
                "total_only_left_pairs": 1,
                "total_only_right_pairs": 1,
            },
            "rows": [
                {
                    "corpus_id": "1",
                    "source": "same src",
                    "target": "same tgt",
                    "left_pairs": [("n", "water", "水")],
                    "right_pairs": [("n", "water", "水")],
                    "only_left_pairs": [],
                    "only_right_pairs": [],
                    "same": True,
                },
                {
                    "corpus_id": "2",
                    "source": "diff src",
                    "target": "diff tgt",
                    "left_pairs": [("v", "drink", "飲む")],
                    "right_pairs": [("n", "tea", "お茶")],
                    "only_left_pairs": [("v", "drink", "飲む")],
                    "only_right_pairs": [("n", "tea", "お茶")],
                    "same": False,
                },
            ],
        }
        text = compare_en_ja_corpus_models.format_text(payload, only_different=True)

        self.assertIn("[row 2]", text)
        self.assertNotIn("[row 1]", text)
        self.assertIn("only smoke: v:drink->飲む", text)
        self.assertIn("only production: n:tea->お茶", text)
        self.assertIn("rows with only smoke pairs: 1", text)
        self.assertIn("rows with only production pairs: 1", text)

    def test_parse_json_payload_tolerates_prefix_logs(self):
        payload = compare_en_ja_corpus_models.parse_json_payload(
            "warning line\\n{\"rows\": [], \"runtime\": {}}\\n"
        )
        self.assertEqual(payload["rows"], [])


if __name__ == "__main__":
    unittest.main()
