import os
import sys
import unittest
from argparse import Namespace


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from ltc.cli import compare_en_ja_corpus_backends


class CompareEnJaCorpusBackendsTest(unittest.TestCase):
    def test_build_audit_command_passes_selection_and_seed(self):
        args = Namespace(
            input="input.csv",
            limit=9,
            row_id=["4"],
            selection="stratified",
            seed=19,
        )
        command = compare_en_ja_corpus_backends.build_audit_command(args)

        self.assertEqual(command[:4], [sys.executable, "-m", "ltc.cli.audit_en_ja_corpus", "--input"])
        self.assertIn("--selection", command)
        self.assertIn("stratified", command)
        self.assertIn("--seed", command)
        self.assertIn("19", command)
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
                "left_label": "jumanpp",
                "left_backend": "jumanpp",
                "right_label": "sudachi_a",
                "right_backend": "sudachi_a",
            },
        )()
        payload = compare_en_ja_corpus_backends.build_payload(
            args, left_payload, right_payload
        )

        self.assertEqual(payload["summary"]["rows_compared"], 2)
        self.assertEqual(payload["summary"]["same_rows"], 1)
        self.assertEqual(payload["summary"]["different_rows"], 1)
        self.assertEqual(payload["summary"]["rows_with_only_left_pairs"], 1)
        self.assertEqual(payload["summary"]["rows_with_only_right_pairs"], 1)
        differing = [row for row in payload["rows"] if not row["same"]][0]
        self.assertEqual(differing["corpus_id"], "2")
        self.assertEqual(differing["only_left_pairs"], [("v", "drink", "飲む")])
        self.assertEqual(differing["only_right_pairs"], [("n", "tea", "お茶")])

    def test_format_text_omits_same_rows_when_requested(self):
        payload = {
            "left": {"label": "jumanpp", "backend": "jumanpp", "runtime": {"note": "left"}},
            "right": {"label": "sudachi_a", "backend": "sudachi_a", "runtime": {"note": "right"}},
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
        text = compare_en_ja_corpus_backends.format_text(payload, only_different=True)

        self.assertIn("[row 2]", text)
        self.assertNotIn("[row 1]", text)
        self.assertIn("only jumanpp: v:drink->飲む", text)
        self.assertIn("only sudachi_a: n:tea->お茶", text)

    def test_parse_json_payload_tolerates_prefix_logs(self):
        payload = compare_en_ja_corpus_backends.parse_json_payload(
            "warning line\\n{\"rows\": [], \"runtime\": {}}\\n"
        )
        self.assertEqual(payload["rows"], [])


if __name__ == "__main__":
    unittest.main()
