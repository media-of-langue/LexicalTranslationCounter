import os
import sys
import unittest


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from ltc.cli.count import resolve_end_id
from ltc.io.relations import parse_example_ids
from ltc.pipeline.counting import (
    RelationState,
    build_corpus_output_row,
    expand_wordlist_with_normalized_forms,
)


class ResolveEndIdTest(unittest.TestCase):
    def test_max_rows_sets_end_id(self):
        self.assertEqual(resolve_end_id(10, 5, None), 15)

    def test_cli_end_id_is_capped_by_max_rows(self):
        self.assertEqual(resolve_end_id(10, 5, 30), 15)

    def test_rejects_non_positive_window(self):
        with self.assertRaises(ValueError):
            resolve_end_id(10, 0, None)


class RelationIoTest(unittest.TestCase):
    def test_parse_example_ids_supports_python_list_strings(self):
        self.assertEqual(parse_example_ids("['1', '2']"), ["1", "2"])

    def test_parse_example_ids_supports_brace_format(self):
        self.assertEqual(parse_example_ids("{1, 2}"), ["1", "2"])


class CountingStateTest(unittest.TestCase):
    def test_relation_state_assigns_and_reuses_relation_id(self):
        state = RelationState.empty()
        corpus_row = ["5", "hello", "bonjour", "{}", False]
        output = [["n", "10", "hello", "20", "bonjour"]]

        enriched = state.apply_alignment_output(corpus_row, output)
        self.assertEqual(enriched[0][1], "0")
        self.assertEqual(state.relation_ids["noun"], 1)
        self.assertEqual(
            state.relations["noun"]["10_20"],
            [0, 1, ["5"], "unknown", False],
        )

        second = [["n", "10", "hello", "20", "bonjour"]]
        enriched_second = state.apply_alignment_output(corpus_row, second)
        self.assertEqual(enriched_second[0][1], "0")
        self.assertEqual(
            state.relations["noun"]["10_20"],
            [0, 2, ["5", "5"], "unknown", False],
        )

    def test_build_corpus_output_row_preserves_legacy_shape(self):
        row = ["7", "hello\n", "bonjour\n", "{}", False]
        output = [["n", "0", "10", "hello", "20", "bonjour"]]
        built = build_corpus_output_row(row, output)
        self.assertEqual(built[0], "7")
        self.assertEqual(built[1], "hello")
        self.assertEqual(built[2], "bonjour")
        self.assertEqual(built[4], False)

    def test_expand_wordlist_with_normalized_forms_uses_normalizer(self):
        def fake_normalizer(word, pos_tag, wordlist, test=False):
            mapping = {"plays": "play", "cats": "cat"}
            return mapping.get(word, word)

        updated, changed = expand_wordlist_with_normalized_forms(
            {"plays": 1, "cat": 2},
            "verb",
            fake_normalizer,
        )
        self.assertTrue(changed)
        self.assertIn("play", updated)


if __name__ == "__main__":
    unittest.main()
