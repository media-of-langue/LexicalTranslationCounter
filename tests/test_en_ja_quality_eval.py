import os
import sys
import unittest
from pathlib import Path
from unittest import mock


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from ltc.evaluation.en_ja_quality import (
    CaseResult,
    NormalizedPair,
    ObservedAlignment,
    QualityCase,
    load_quality_cases,
    select_cases_for_suite,
    run_quality_case,
)


class EnJaQualityEvalTest(unittest.TestCase):
    def test_run_quality_case_reports_missing_and_forbidden_pairs(self):
        case = QualityCase(
            name="demo",
            source="src",
            target="tgt",
            required_pairs=(NormalizedPair("a", "happy", "嬉しい"),),
            forbidden_pairs=(NormalizedPair("v", "be", "嬉しい"),),
            tier="core",
            notes="demo case",
        )
        with mock.patch(
            "ltc.evaluation.en_ja_quality.alignment",
            return_value=[["v", "-1", "am", "-1", "嬉しい"]],
        ), mock.patch(
            "ltc.evaluation.en_ja_quality.en_normalizer",
            side_effect=lambda word, pos, wordlist, test=True: "be"
            if word == "am"
            else word,
        ), mock.patch(
            "ltc.evaluation.en_ja_quality.ja_normalizer",
            side_effect=lambda word, pos, wordlist, test=True: word,
        ):
            result = run_quality_case(case)

        self.assertFalse(result.passed)
        self.assertEqual(result.tier, "core")
        self.assertEqual(result.missing_pairs, case.required_pairs)
        self.assertEqual(result.forbidden_hits, case.forbidden_pairs)
        self.assertEqual(result.unexpected_pairs, ())

    def test_case_result_as_dict_contains_pairs(self):
        result = CaseResult(
            name="demo",
            tier="core",
            passed=True,
            required_pairs=(NormalizedPair("a", "happy", "嬉しい"),),
            forbidden_pairs=(),
            actual_alignments=(
                ObservedAlignment(
                    pos="a",
                    src_surface="happy",
                    src_normalized="happy",
                    tgt_surface="嬉しい",
                    tgt_normalized="嬉しい",
                ),
            ),
            actual_pairs=(NormalizedPair("a", "happy", "嬉しい"),),
            missing_pairs=(),
            forbidden_hits=(),
            unexpected_pairs=(),
            allow_extra_pairs=True,
            notes=None,
        )
        payload = result.as_dict()
        self.assertEqual(payload["name"], "demo")
        self.assertEqual(payload["tier"], "core")
        self.assertEqual(payload["actual_pairs"][0]["src"], "happy")
        self.assertEqual(payload["actual_alignments"][0]["src_surface"], "happy")

    def test_run_quality_case_reports_unexpected_pairs_when_disabled(self):
        case = QualityCase(
            name="strict",
            source="src",
            target="tgt",
            required_pairs=(NormalizedPair("a", "happy", "嬉しい"),),
            forbidden_pairs=(),
            tier="extended",
            allow_extra_pairs=False,
        )
        with mock.patch(
            "ltc.evaluation.en_ja_quality.alignment",
            return_value=[
                ["a", "-1", "happy", "-1", "嬉しい"],
                ["v", "-1", "get", "-1", "得る"],
            ],
        ), mock.patch(
            "ltc.evaluation.en_ja_quality.en_normalizer",
            side_effect=lambda word, pos, wordlist, test=True: word,
        ), mock.patch(
            "ltc.evaluation.en_ja_quality.ja_normalizer",
            side_effect=lambda word, pos, wordlist, test=True: word,
        ):
            result = run_quality_case(case)

        self.assertFalse(result.passed)
        self.assertEqual(
            result.unexpected_pairs,
            (NormalizedPair("v", "get", "得る"),),
        )

    def test_select_cases_for_suite_keeps_core_only_or_all(self):
        cases = (
            QualityCase(
                name="core_case",
                source="a",
                target="b",
                required_pairs=(),
                forbidden_pairs=(),
                tier="core",
            ),
            QualityCase(
                name="extended_case",
                source="c",
                target="d",
                required_pairs=(),
                forbidden_pairs=(),
                tier="extended",
            ),
        )
        self.assertEqual(
            [case.name for case in select_cases_for_suite(cases, "core")],
            ["core_case"],
        )
        self.assertEqual(
            [case.name for case in select_cases_for_suite(cases, "extended")],
            ["core_case", "extended_case"],
        )

    def test_sample_packs_load(self):
        base_path = Path(TEST_ROOT).parent / "projects" / "quality" / "en_ja"
        expected = {
            "sample_pack_2.json": (11, "sample2_outgoing_incoming_email_process_probe"),
            "sample_pack_3.json": (12, "sample3_airing_commercial_cost"),
        }
        for filename, (expected_len, expected_case_name) in expected.items():
            with self.subTest(filename=filename):
                cases = load_quality_cases(base_path / filename)
                self.assertEqual(len(cases), expected_len)
                self.assertTrue(all(case.tier == "core" for case in cases))
                self.assertIn(expected_case_name, {case.name for case in cases})


if __name__ == "__main__":
    unittest.main()
