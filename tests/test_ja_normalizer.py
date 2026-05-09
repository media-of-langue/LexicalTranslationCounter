import os
import sys
import unittest
from importlib import import_module, reload


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from ltc.japanese.normalization import ja_normalizer


def normalize_with_backend(backend_name, word, pos_tag):
    original = os.environ.get("LTC_JA_TEXT_BACKEND")
    try:
        os.environ["LTC_JA_TEXT_BACKEND"] = backend_name
        module_name = "ltc.japanese.normalization"
        module = import_module(module_name)
        module = reload(module)
        return module.ja_normalizer(word, pos_tag, {}, test=True)
    finally:
        if original is None:
            os.environ.pop("LTC_JA_TEXT_BACKEND", None)
        else:
            os.environ["LTC_JA_TEXT_BACKEND"] = original


class JaNormalizerTest(unittest.TestCase):
    def test_drops_leading_light_suru_before_main_verb(self):
        self.assertEqual(ja_normalizer("して払う", "v", {}, test=True), "払う")

    def test_keeps_sahen_noun_plus_suru_verb_normalization(self):
        self.assertEqual(ja_normalizer("暗示して", "v", {}, test=True), "暗示する")

    def test_keeps_compound_verb_normalization(self):
        self.assertEqual(ja_normalizer("言い切って", "v", {}, test=True), "言い切る")

    def test_experimental_backends_keep_katakana_nouns_without_english_gloss(self):
        for backend_name in ["fugashi_unidic", "sudachi_a"]:
            with self.subTest(backend=backend_name):
                self.assertEqual(
                    normalize_with_backend(backend_name, "コンテンツ", "n"),
                    "コンテンツ",
                )

    def test_experimental_backends_normalize_shape_adjectives(self):
        for backend_name in ["fugashi_unidic", "sudachi_a"]:
            with self.subTest(backend=backend_name):
                self.assertEqual(
                    normalize_with_backend(backend_name, "重要です", "a"),
                    "重要",
                )

    def test_experimental_backends_normalize_moshikashitara_as_adverb(self):
        for backend_name in ["fugashi_unidic", "sudachi_a"]:
            with self.subTest(backend=backend_name):
                self.assertEqual(
                    normalize_with_backend(backend_name, "もしかしたら", "r"),
                    "もしかしたら",
                )

    def test_experimental_backends_recover_contextless_verbal_fragment(self):
        for backend_name in ["fugashi_unidic", "sudachi_a"]:
            with self.subTest(backend=backend_name):
                self.assertEqual(
                    normalize_with_backend(backend_name, "表示さ", "v"),
                    "表示する",
                )

    def test_sudachi_backend_recovers_contextless_kangae_as_verb(self):
        self.assertEqual(normalize_with_backend("sudachi_a", "考え", "v"), "考える")

    def test_sudachi_backend_normalizes_naze_and_noseru_for_alignment(self):
        self.assertEqual(normalize_with_backend("sudachi_a", "なぜ", "r"), "何故")
        self.assertEqual(normalize_with_backend("sudachi_a", "乗せる", "v"), "載せる")

    def test_sudachi_backend_recovers_omoi_as_contextless_verb(self):
        self.assertEqual(normalize_with_backend("sudachi_a", "思い", "v"), "思う")

    def test_sudachi_backend_recovers_hanare_as_contextless_verb(self):
        self.assertEqual(normalize_with_backend("sudachi_a", "離れ", "v"), "離れる")

    def test_sudachi_backend_recovers_common_contextless_verb_fragments(self):
        self.assertEqual(normalize_with_backend("sudachi_a", "作り", "v"), "作る")
        self.assertEqual(normalize_with_backend("sudachi_a", "当て", "v"), "当てる")
        self.assertEqual(normalize_with_backend("sudachi_a", "なっ", "v"), "なる")
        self.assertEqual(normalize_with_backend("sudachi_a", "変え", "v"), "変える")

    def test_sudachi_backend_normalizes_shape_adjective_suffix_and_prefix_forms(self):
        self.assertEqual(normalize_with_backend("sudachi_a", "衛生的に", "a"), "衛生的")
        self.assertEqual(normalize_with_backend("sudachi_a", "小綺麗に", "a"), "小綺麗")

    def test_sudachi_backend_drops_trailing_head_noun_modifier_jitai(self):
        self.assertEqual(normalize_with_backend("sudachi_a", "言葉自体", "n"), "言葉")

    def test_sudachi_backend_drops_trailing_head_noun_modifier_jishin(self):
        self.assertEqual(normalize_with_backend("sudachi_a", "私自身", "n"), "私")

    def test_sudachi_backend_drops_trailing_head_noun_suffixes(self):
        self.assertEqual(normalize_with_backend("sudachi_a", "戸籍簿等", "n"), "戸籍簿")
        self.assertEqual(normalize_with_backend("sudachi_a", "子供たち", "n"), "子供")


if __name__ == "__main__":
    unittest.main()
