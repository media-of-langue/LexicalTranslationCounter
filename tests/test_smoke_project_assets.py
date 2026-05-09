from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SmokeProjectAssetTests(unittest.TestCase):
    def test_de_en_smoke_input_has_required_files(self):
        input_dir = ROOT / "projects" / "smoke" / "de_en" / "input"
        self.assertTrue((input_dir / "corpus_de_en.csv").exists())
        for lang in ("de", "en"):
            for pos_name in ("noun", "verb", "adj", "adverb"):
                self.assertTrue((input_dir / f"wordlist_{lang}_{pos_name}.csv").exists())

    def test_en_ja_smoke_input_has_required_files(self):
        input_dir = ROOT / "projects" / "smoke" / "en_ja" / "input"
        self.assertTrue((input_dir / "corpus_en_ja.csv").exists())
        for lang in ("en", "ja"):
            for pos_name in ("noun", "verb", "adj", "adverb"):
                self.assertTrue((input_dir / f"wordlist_{lang}_{pos_name}.csv").exists())
