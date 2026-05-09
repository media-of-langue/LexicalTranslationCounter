import os
import sys
import unittest
import json


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from ltc.cli import audit_en_ja_corpus
from ltc.evaluation import en_ja_corpus_audit


class EnJaCorpusAuditCliTest(unittest.TestCase):
    def test_format_text_includes_row_summary(self):
        payload = {
            "runtime": {"note": "smoke/dev model"},
            "selection": {"strategy": "random", "seed": 7, "row_ids": ["2"]},
            "rows": [
                type(
                    "RowResult",
                    (),
                    {
                        "corpus_id": "2",
                        "source": "Sponsored link...",
                        "target": "スポンサードリンク...",
                        "actual_pairs": [
                            type("Pair", (), {"pos": "n", "src": "advertisement", "tgt": "広告"})()
                        ],
                    },
                )()
            ],
        }
        text = audit_en_ja_corpus.format_text(payload)
        self.assertIn("[row 2]", text)
        self.assertIn("n:advertisement->広告", text)
        self.assertIn("summary: 1 rows", text)
        self.assertIn("selection: random (seed=7, rows=1)", text)

    def test_select_corpus_rows_random_is_reproducible(self):
        rows = en_ja_corpus_audit.select_corpus_rows(
            limit=5,
            selection="random",
            seed=7,
        )
        again = en_ja_corpus_audit.select_corpus_rows(
            limit=5,
            selection="random",
            seed=7,
        )
        self.assertEqual([row.corpus_id for row in rows], [row.corpus_id for row in again])
        self.assertEqual(len(rows), 5)

    def test_select_corpus_rows_stratified_uses_multiple_length_buckets(self):
        rows = en_ja_corpus_audit.select_corpus_rows(
            limit=8,
            selection="stratified",
            seed=11,
        )
        buckets = {en_ja_corpus_audit.source_length_bucket(row) for row in rows}
        self.assertGreaterEqual(len(rows), 4)
        self.assertGreaterEqual(len(buckets), 2)

    def test_format_json_keeps_selection_metadata(self):
        payload = {
            "runtime": {"note": "smoke/dev model"},
            "selection": {"strategy": "random", "seed": 17, "row_ids": ["1", "9"]},
            "rows": [],
        }
        serialized = json.loads(audit_en_ja_corpus.format_json(payload))
        self.assertEqual(serialized["selection"]["strategy"], "random")
        self.assertEqual(serialized["selection"]["row_ids"], ["1", "9"])


if __name__ == "__main__":
    unittest.main()
