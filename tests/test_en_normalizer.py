import os
import sys
import unittest


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from normalizer.en_normalizer import en_normalizer
from ltc.text import normalize_english_text


class EnNormalizerTest(unittest.TestCase):
    def test_sentence_initial_word_is_normalized_to_lowercase(self):
        self.assertEqual(en_normalizer("Perhaps", "r", {}, test=True), "perhaps")

    def test_inflected_verb_is_lemmatized_in_lowercase(self):
        self.assertEqual(en_normalizer("Running", "v", {}, test=True), "run")

    def test_curly_apostrophe_is_normalized_for_english_text(self):
        self.assertEqual(normalize_english_text("It’s"), "It's")


if __name__ == "__main__":
    unittest.main()
