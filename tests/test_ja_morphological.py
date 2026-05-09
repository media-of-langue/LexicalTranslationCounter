import os
import sys
import unittest
from importlib import import_module, reload


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from ltc.japanese.morphology import ja_morphological


def run_with_backend(backend_name, sentence):
    original = os.environ.get("LTC_JA_TEXT_BACKEND")
    try:
        os.environ["LTC_JA_TEXT_BACKEND"] = backend_name
        module_name = "ltc.japanese.morphology"
        module = import_module(module_name)
        module = reload(module)
        return module.ja_morphological(sentence)
    finally:
        if original is None:
            os.environ.pop("LTC_JA_TEXT_BACKEND", None)
        else:
            os.environ["LTC_JA_TEXT_BACKEND"] = original


class JaMorphologicalTest(unittest.TestCase):
    def test_keeps_space_boundaries_between_independent_nouns(self):
        tokens, pos_tags = ja_morphological(
            "感想 私は最近ブログの記事を音声入力で書いています。"
        )
        self.assertIn("感想", tokens)
        self.assertIn("私", tokens)
        self.assertNotIn("感想私", tokens)

    def test_does_not_merge_time_noun_with_following_common_noun(self):
        tokens, pos_tags = ja_morphological(
            "私は最近ブログの記事を音声入力で書いています。"
        )
        self.assertIn("最近", tokens)
        self.assertIn("ブログ", tokens)
        self.assertIn("音声入力", tokens)
        self.assertNotIn("最近ブログ", tokens)

    def test_experimental_backends_keep_copula_shape_adjective(self):
        for backend_name in ["fugashi_unidic", "sudachi_a"]:
            with self.subTest(backend=backend_name):
                tokens, pos_tags = run_with_backend(backend_name, "これは重要です。")
                self.assertIn("重要です", tokens)
                self.assertEqual(pos_tags[tokens.index("重要です")], "a")

    def test_experimental_backends_merge_sahen_noun_plus_suru(self):
        sentence = "止める時は、決めた変数をclearIntervalで指定する。"
        for backend_name in ["fugashi_unidic", "sudachi_a"]:
            with self.subTest(backend=backend_name):
                tokens, pos_tags = run_with_backend(backend_name, sentence)
                self.assertIn("指定する", tokens)
                self.assertEqual(pos_tags[tokens.index("指定する")], "v")

    def test_experimental_backends_restore_moshikashitara_as_adverb(self):
        sentence = "もしかしたら私もそちら側の人間になってしまうでしょう。"
        for backend_name in ["fugashi_unidic", "sudachi_a"]:
            with self.subTest(backend=backend_name):
                tokens, pos_tags = run_with_backend(backend_name, sentence)
                self.assertIn("もしかしたら", tokens)
                self.assertEqual(pos_tags[tokens.index("もしかしたら")], "r")

    def test_sudachi_backend_recovers_absolute_perfect_and_generally(self):
        tokens, pos_tags = run_with_backend(
            "sudachi_a",
            "だから絶対完璧とは言えませんが概ね大丈夫だろうという事で。",
        )
        self.assertIn("絶対", tokens)
        self.assertEqual(pos_tags[tokens.index("絶対")], "r")
        self.assertIn("完璧", tokens)
        self.assertEqual(pos_tags[tokens.index("完璧")], "a")
        self.assertIn("概ね", tokens)
        self.assertEqual(pos_tags[tokens.index("概ね")], "r")

    def test_sudachi_backend_keeps_ascii_acronym_and_generic_noun_separate(self):
        tokens, pos_tags = run_with_backend(
            "sudachi_a",
            "PHPのCSRF対策について知っていた。",
        )
        self.assertIn("CSRF", tokens)
        self.assertIn("対策", tokens)
        self.assertNotIn("CSRF対策", tokens)

    def test_sudachi_backend_keeps_noun_like_suffix_compounds_as_nouns(self):
        tokens, pos_tags = run_with_backend(
            "sudachi_a",
            "長年のお客様が戸籍簿等を確認した。",
        )
        self.assertIn("お客様", tokens)
        self.assertEqual(pos_tags[tokens.index("お客様")], "n")
        self.assertIn("戸籍簿等", tokens)
        self.assertEqual(pos_tags[tokens.index("戸籍簿等")], "n")

    def test_sudachi_backend_restores_shape_adjective_suffix_and_prefix_forms(self):
        tokens, pos_tags = run_with_backend(
            "sudachi_a",
            "衛生的にもないほうが小綺麗に感じると思います。",
        )
        self.assertIn("衛生的に", tokens)
        self.assertEqual(pos_tags[tokens.index("衛生的に")], "a")
        self.assertIn("小綺麗に", tokens)
        self.assertEqual(pos_tags[tokens.index("小綺麗に")], "a")


if __name__ == "__main__":
    unittest.main()
