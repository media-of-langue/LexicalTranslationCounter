import csv
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from ltc.cli import count as count_cli
from ltc.errors import FatalRuntimeError


def fake_alignment_runtime(language_pair):
    def alignment(corpus_row, wordlists):
        text = corpus_row[1].lower()
        if "dog" in text:
            return [["n", "1", "dog", "1", "Hund"]]
        return [["a", "1", "good", "1", "gut"]]

    def alignment_batch(corpus_rows, wordlists):
        return [alignment(row, wordlists) for row in corpus_rows]

    return alignment, alignment_batch


def fake_normalizer(language_code):
    def normalize(word, pos_tag, wordlist, test=False):
        normalized = word.strip().lower()
        if test:
            return normalized
        return None, normalized

    return normalize


class CountCliSmokeTest(unittest.TestCase):
    def _write_fixture_input(self, input_dir):
        corpus_rows = [
            ["1", "dog is here", "Hund ist hier", "{}", "False"],
            ["2", "good day", "gut tag", "{}", "False"],
        ]
        with (input_dir / "corpus_de_en.csv").open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(corpus_rows)

        wordlists = {
            "de_noun": [(1, "hund")],
            "de_verb": [(1, "sein")],
            "de_adj": [(1, "gut")],
            "de_adverb": [(1, "sehr")],
            "en_noun": [(1, "dog")],
            "en_verb": [(1, "be")],
            "en_adj": [(1, "good")],
            "en_adverb": [(1, "very")],
        }
        for name, rows in wordlists.items():
            with (input_dir / f"wordlist_{name}.csv").open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerows(rows)

    def test_count_cli_runs_and_resumes_with_fake_backends(self):
        with tempfile.TemporaryDirectory(prefix="ltc-smoke-") as tmp:
            tmp_path = Path(tmp)
            input_dir = tmp_path / "input"
            output_dir = tmp_path / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            self._write_fixture_input(input_dir)

            with mock.patch.object(
                count_cli, "load_alignment_runtime", side_effect=fake_alignment_runtime
            ), mock.patch.object(
                count_cli, "load_normalizer", side_effect=fake_normalizer
            ):
                with redirect_stdout(io.StringIO()):
                    count_cli.main(
                        [
                            "ltc-count",
                            "0",
                            "de",
                            "en",
                            "--input-dir",
                            str(input_dir),
                            "--output-dir",
                            str(output_dir),
                            "--max-rows",
                            "1",
                        ]
                    )
                    count_cli.main(
                        [
                            "ltc-count",
                            "1",
                            "de",
                            "en",
                            "--input-dir",
                            str(input_dir),
                            "--output-dir",
                            str(output_dir),
                            "--max-rows",
                            "1",
                        ]
                    )

            with (output_dir / "relations_de_en_noun.csv").open() as f:
                noun_rows = list(csv.reader(f))
            with (output_dir / "relations_de_en_adj.csv").open() as f:
                adj_rows = list(csv.reader(f))
            with (output_dir / "corpus_de_en.csv").open() as f:
                corpus_out_rows = list(csv.reader(f))
            passed_id = (output_dir / "passed_id.txt").read_text().strip()

            self.assertEqual(len(noun_rows), 1)
            self.assertEqual(noun_rows[0][3], "1")
            self.assertEqual(len(adj_rows), 1)
            self.assertEqual(adj_rows[0][3], "1")
            self.assertEqual(len(corpus_out_rows), 2)
            self.assertEqual(passed_id, "1")

    def test_count_cli_re_raises_fatal_runtime_errors(self):
        def fatal_alignment_runtime(language_pair):
            def alignment(corpus_row, wordlists):
                raise FatalRuntimeError("stop now")

            def alignment_batch(corpus_rows, wordlists):
                raise FatalRuntimeError("stop now")

            return alignment, alignment_batch

        with tempfile.TemporaryDirectory(prefix="ltc-smoke-") as tmp:
            tmp_path = Path(tmp)
            input_dir = tmp_path / "input"
            output_dir = tmp_path / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            self._write_fixture_input(input_dir)

            with mock.patch.object(
                count_cli, "load_alignment_runtime", side_effect=fatal_alignment_runtime
            ), mock.patch.object(
                count_cli, "load_normalizer", side_effect=fake_normalizer
            ):
                with redirect_stdout(io.StringIO()):
                    with self.assertRaises(FatalRuntimeError):
                        count_cli.main(
                            [
                                "ltc-count",
                                "0",
                                "de",
                                "en",
                                "--input-dir",
                                str(input_dir),
                                "--output-dir",
                                str(output_dir),
                                "--max-rows",
                                "1",
                            ]
                        )
