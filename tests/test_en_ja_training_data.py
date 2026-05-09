import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from ltc.training.en_ja_data import (
    FilterConfig,
    SourceSpec,
    SplitConfig,
    TrainingConfig,
    build_pair_fingerprint,
    load_training_config,
    prepare_training_examples,
    write_training_outputs,
)


class EnJaTrainingDataTest(unittest.TestCase):
    def test_load_training_config_resolves_relative_paths(self):
        with tempfile.TemporaryDirectory(prefix="ltc-train-config-") as tmp:
            root = Path(tmp)
            (root / "raw").mkdir()
            config_path = root / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "name": "demo",
                        "seed": "demo",
                        "sources": [
                            {
                                "name": "jparacrawl",
                                "path": "raw/input.tsv",
                                "format": "paired_tsv",
                            }
                        ],
                    }
                )
            )
            config = load_training_config(config_path)

        self.assertEqual(config.sources[0].path, str((root / "raw" / "input.tsv").resolve()))

    def test_prepare_training_examples_deduplicates_and_filters(self):
        with tempfile.TemporaryDirectory(prefix="ltc-train-data-") as tmp:
            root = Path(tmp)
            source_path = root / "pairs.tsv"
            source_path.write_text(
                "\n".join(
                    [
                        "I drink water.\t私は水を飲む。",
                        "I drink water.\t私は水を飲む。",
                        "\t",
                        "same\tsame",
                        "voice input\t音声入力",
                    ]
                )
            )
            config = TrainingConfig(
                name="demo",
                seed="demo",
                sources=(
                    SourceSpec(
                        name="demo_source",
                        path=str(source_path),
                        format="paired_tsv",
                    ),
                ),
                filters=FilterConfig(max_source_chars=100, max_target_chars=100),
                splits=SplitConfig(),
            )
            prepared = prepare_training_examples(config)

        self.assertEqual(len(prepared["examples"]), 2)
        self.assertEqual(prepared["drop_stats"]["duplicate_pair"], 1)
        self.assertEqual(prepared["drop_stats"]["empty"], 1)
        self.assertEqual(prepared["drop_stats"]["identical"], 1)

    def test_write_training_outputs_emits_manifest_and_split_files(self):
        with tempfile.TemporaryDirectory(prefix="ltc-train-write-") as tmp:
            root = Path(tmp)
            source_path = root / "pairs.tsv"
            source_path.write_text(
                "\n".join(
                    [
                        "I drink water.\t私は水を飲む。",
                        "voice input\t音声入力",
                    ]
                )
            )
            config = TrainingConfig(
                name="demo",
                seed="demo",
                sources=(
                    SourceSpec(
                        name="demo_source",
                        path=str(source_path),
                        format="paired_tsv",
                    ),
                ),
                filters=FilterConfig(max_source_chars=100, max_target_chars=100),
                splits=SplitConfig(train=0.0, dev=1.0, test=0.0),
            )
            prepared = prepare_training_examples(config)
            payload = write_training_outputs(root / "out", config, prepared)

            manifest_text = (root / "out" / "manifest.tsv").read_text()
            dev_text = (root / "out" / "awesome_dev.txt").read_text()
            summary = json.loads((root / "out" / "summary.json").read_text())

        self.assertIn("source_name\tsplit\tfingerprint\tsource_text\ttarget_text", manifest_text)
        self.assertIn("I drink water. ||| 私は水を飲む。", dev_text)
        self.assertEqual(summary["split_counts"]["dev"], 2)
        self.assertEqual(payload["summary"]["total_examples"], 2)

    def test_build_pair_fingerprint_is_stable(self):
        first = build_pair_fingerprint("I drink water.", "私は水を飲む。")
        second = build_pair_fingerprint("I drink water.", "私は水を飲む。")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
