import os
import sys
import unittest


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from ltc.japanese.backends import (
    DEFAULT_JAPANESE_TEXT_BACKEND,
    current_japanese_text_backend_name,
    parse_japanese_text_backend_name,
)


class JapaneseBackendsTest(unittest.TestCase):
    def test_default_backend_is_sudachi_a(self):
        original = os.environ.get("LTC_JA_TEXT_BACKEND")
        try:
            os.environ.pop("LTC_JA_TEXT_BACKEND", None)
            self.assertEqual(DEFAULT_JAPANESE_TEXT_BACKEND, "sudachi_a")
            self.assertEqual(current_japanese_text_backend_name(), "sudachi_a")
        finally:
            if original is None:
                os.environ.pop("LTC_JA_TEXT_BACKEND", None)
            else:
                os.environ["LTC_JA_TEXT_BACKEND"] = original

    def test_aliases_resolve_to_canonical_backend_names(self):
        self.assertEqual(parse_japanese_text_backend_name("sudachi"), "sudachi_a")
        self.assertEqual(
            parse_japanese_text_backend_name("fugashi"), "fugashi_unidic"
        )
        self.assertEqual(parse_japanese_text_backend_name("juman"), "jumanpp")


if __name__ == "__main__":
    unittest.main()
