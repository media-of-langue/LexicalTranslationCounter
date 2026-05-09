import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from ltc.cli import inspect_en_ja
from ltc.inspection.en_ja import EnJaInspectionRequest, resolve_inspection_request


class EnJaInspectionRequestTest(unittest.TestCase):
    def test_resolve_request_from_source_and_target(self):
        request = resolve_inspection_request(source="I am happy.", target="私は嬉しい。")
        self.assertEqual(request.source, "I am happy.")
        self.assertEqual(request.target, "私は嬉しい。")

    def test_resolve_request_requires_case_or_sentences(self):
        with self.assertRaises(ValueError):
            resolve_inspection_request()


class InspectEnJaCliTest(unittest.TestCase):
    def test_format_text_includes_key_sections(self):
        payload = {
            "runtime": {"note": "smoke/dev model"},
            "request": {
                "name": "copula_adjective",
                "notes": "demo",
                "source": "I am happy.",
                "target": "私は嬉しい。",
            },
            "source": {"tokens": [{"index": 0, "text": "happy", "pos_tag": "a"}]},
            "target": {"tokens": [{"index": 0, "text": "嬉しい", "pos_tag": "a"}]},
            "ignored_source_indices": [],
            "ignored_target_indices": [],
            "merged_groups": [
                {
                    "source_indices": [0],
                    "source_tokens": ["happy"],
                    "source_pos_tags": ["a"],
                    "target_indices": [0],
                    "target_tokens": ["嬉しい"],
                    "target_pos_tags": ["a"],
                    "ignored_by_source_rule": False,
                    "ignored_by_target_rule": False,
                }
            ],
            "postprocessed_groups": [
                {
                    "source_tokens": ["happy"],
                    "source_pos_tags": ["a"],
                    "target_tokens": ["嬉しい"],
                    "target_pos_tags": ["a"],
                    "best_alignment_score": 0.91,
                    "average_alignment_score": 0.91,
                }
            ],
            "source_target_candidates": [
                {
                    "source_index": 0,
                    "source_token": "happy",
                    "source_pos_tag": "a",
                    "candidates": [
                        {
                            "target_index": 0,
                            "target_token": "嬉しい",
                            "target_pos_tag": "a",
                            "score": 0.91,
                        }
                    ],
                }
            ],
            "final_pairs": [
                {
                    "pos_tag": "a",
                    "source_surface": "happy",
                    "source_normalized": "happy",
                    "target_surface": "嬉しい",
                    "target_normalized": "嬉しい",
                    "best_alignment_score": 0.91,
                    "average_alignment_score": 0.91,
                }
            ],
        }
        text = inspect_en_ja.format_text(payload)
        self.assertIn("[runtime]", text)
        self.assertIn("[merged groups]", text)
        self.assertIn("[source target candidates]", text)
        self.assertIn("normalized: happy -> 嬉しい", text)
        self.assertIn("best=0.9100", text)

    def test_main_supports_case_mode(self):
        fake_request = EnJaInspectionRequest(
            source="I am happy.",
            target="私は嬉しい。",
            name="copula_adjective",
        )
        fake_payload = {
            "runtime": {"note": "smoke/dev model"},
            "request": {
                "name": "copula_adjective",
                "notes": None,
                "source": "I am happy.",
                "target": "私は嬉しい。",
            },
            "source": {"tokens": []},
            "target": {"tokens": []},
            "ignored_source_indices": [],
            "ignored_target_indices": [],
            "merged_groups": [],
            "postprocessed_groups": [],
            "source_target_candidates": [],
            "final_pairs": [],
        }
        with mock.patch.object(
            inspect_en_ja, "resolve_inspection_request", return_value=fake_request
        ) as resolve_mock, mock.patch.object(
            inspect_en_ja, "inspect_request", return_value=fake_payload
        ):
            with redirect_stdout(io.StringIO()) as stdout:
                inspect_en_ja.main(
                    ["ltc-inspect-en-ja", "--case", "copula_adjective"]
                )
        resolve_mock.assert_called_once()
        self.assertIn("copula_adjective", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
