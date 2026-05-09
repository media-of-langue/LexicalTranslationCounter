import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from ltc.cli.convert_en_ja_public_source import main as convert_cli_main
from ltc.training.en_ja_sources import (
    convert_aspec_je,
    convert_paired_tsv,
    convert_parallel_text_files,
    resolve_aspec_input_paths,
)


class EnJaSourceConversionTest(unittest.TestCase):
    def test_convert_parallel_text_files_streams_and_normalizes(self):
        with tempfile.TemporaryDirectory(prefix="ltc-en-ja-parallel-") as tmp:
            root = Path(tmp)
            source_path = root / "train.en"
            target_path = root / "train.ja"
            output_path = root / "converted.tsv"
            source_path.write_text("It’s  fine.\nvoice input\n")
            target_path.write_text("大丈夫 です。\n音声入力\n")

            summary = convert_parallel_text_files(
                source_name="jesc",
                source_file=source_path,
                target_file=target_path,
                output_path=output_path,
            )

            written = output_path.read_text()

        self.assertEqual(summary.source_name, "jesc")
        self.assertEqual(summary.rows_written, 2)
        self.assertIn("It's fine.\t大丈夫 です。", written)
        self.assertIn("voice input\t音声入力", written)

    def test_convert_parallel_text_files_rejects_line_count_mismatch(self):
        with tempfile.TemporaryDirectory(prefix="ltc-en-ja-parallel-mismatch-") as tmp:
            root = Path(tmp)
            source_path = root / "train.en"
            target_path = root / "train.ja"
            output_path = root / "converted.tsv"
            source_path.write_text("one\ntwo\n")
            target_path.write_text("一つ\n")

            with self.assertRaises(RuntimeError):
                convert_parallel_text_files(
                    source_name="demo",
                    source_file=source_path,
                    target_file=target_path,
                    output_path=output_path,
                )

    def test_convert_paired_tsv_respects_columns_and_header(self):
        with tempfile.TemporaryDirectory(prefix="ltc-en-ja-tsv-") as tmp:
            root = Path(tmp)
            input_path = root / "pairs.csv"
            output_path = root / "converted.tsv"
            input_path.write_text(
                "ja,en,score\n"
                "私は水を飲む。,I drink water.,0.91\n"
                "音声入力,voice input,0.83\n"
            )

            summary = convert_paired_tsv(
                source_name="jparacrawl",
                input_path=input_path,
                output_path=output_path,
                source_column=1,
                target_column=0,
                delimiter=",",
                skip_header=True,
            )

            written = output_path.read_text()

        self.assertEqual(summary.rows_written, 2)
        self.assertIn("I drink water.\t私は水を飲む。", written)
        self.assertIn("voice input\t音声入力", written)

    def test_convert_aspec_je_handles_train_and_dev_shapes(self):
        with tempfile.TemporaryDirectory(prefix="ltc-en-ja-aspec-") as tmp:
            root = Path(tmp)
            train_path = root / "train1.txt"
            dev_path = root / "dev.txt"
            output_path = root / "aspec.tsv"
            train_path.write_text(
                "doc1 ||| 0.91 ||| title ||| 日本語の文。 ||| English sentence.\n"
            )
            dev_path.write_text(
                "doc2 ||| 0.88 ||| 日本語の検証文。 ||| English validation sentence.\n"
            )

            summary = convert_aspec_je(
                input_paths=[str(train_path), str(dev_path)],
                output_path=output_path,
            )
            rows = output_path.read_text().splitlines()

        self.assertEqual(summary.rows_written, 2)
        self.assertEqual(rows[0], "English sentence.\t日本語の文。")
        self.assertEqual(rows[1], "English validation sentence.\t日本語の検証文。")

    def test_resolve_aspec_input_paths_from_directory(self):
        with tempfile.TemporaryDirectory(prefix="ltc-en-ja-aspec-dir-") as tmp:
            root = Path(tmp)
            for file_name in ("train2.txt", "train1.txt", "dev.txt", "test.txt"):
                (root / file_name).write_text("placeholder\n")

            resolved = resolve_aspec_input_paths(input_dir=root)

        self.assertEqual(
            [Path(path).name for path in resolved],
            ["train1.txt", "train2.txt", "dev.txt", "test.txt"],
        )

    def test_convert_cli_prints_config_fragment(self):
        with tempfile.TemporaryDirectory(prefix="ltc-en-ja-cli-") as tmp:
            root = Path(tmp)
            source_path = root / "train.en"
            target_path = root / "train.ja"
            output_path = root / "converted.tsv"
            source_path.write_text("voice input\n")
            target_path.write_text("音声入力\n")

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = convert_cli_main(
                    [
                        "ltc.cli.convert_en_ja_public_source",
                        "parallel-files",
                        "--source-name",
                        "jesc",
                        "--source-file",
                        str(source_path),
                        "--target-file",
                        str(target_path),
                        "--output-path",
                        str(output_path),
                        "--format",
                        "json",
                    ]
                )

            payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["source_name"], "jesc")
        self.assertEqual(payload["config_fragment"]["format"], "paired_tsv")
        self.assertEqual(payload["rows_written"], 1)


if __name__ == "__main__":
    unittest.main()
