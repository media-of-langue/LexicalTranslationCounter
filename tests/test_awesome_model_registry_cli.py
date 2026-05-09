import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from ltc.cli.awesome_model_status import build_status
from ltc.cli.register_awesome_model import register_model


REQUIRED_FILES = (
    "config.json",
    "pytorch_model.bin",
    "special_tokens_map.json",
    "tokenizer_config.json",
    "vocab.txt",
)


class AwesomeModelRegistryCliTest(unittest.TestCase):
    def make_model_dir(self, root):
        model_dir = Path(root) / "source-model"
        model_dir.mkdir(parents=True)
        for file_name in REQUIRED_FILES:
            (model_dir / file_name).write_text("stub")
        return model_dir

    def test_register_model_copy_files_populates_canonical_registry(self):
        with tempfile.TemporaryDirectory(prefix="awesome-registry-") as tmp:
            model_dir = self.make_model_dir(tmp)
            payload = register_model(
                tmp,
                "en-ja",
                str(model_dir),
                copy_files=True,
                label="prod",
                notes="local copy",
            )
            registry_dir = Path(payload["registry_dir"])
            self.assertTrue((registry_dir / "config.json").is_file())
            self.assertEqual(payload["registration_mode"], "copied_files")
            metadata = json.loads((registry_dir / "MODEL_INFO.json").read_text())
            self.assertEqual(metadata["label"], "prod")
            self.assertEqual(metadata["notes"], "local copy")

            status = build_status(tmp, "en-ja")
            self.assertEqual(status["selection"]["resolution_source"], "repo_registry_files")
            self.assertTrue(status["selection"]["production_ready"])
            self.assertEqual(status["selection"]["metadata"]["label"], "prod")

    def test_register_model_writes_model_spec_when_copy_disabled(self):
        with tempfile.TemporaryDirectory(prefix="awesome-registry-") as tmp:
            payload = register_model(
                tmp,
                "en-ja",
                "media-of-langue/awesome-en-ja-prod",
                label="remote",
            )
            registry_dir = Path(payload["registry_dir"])
            self.assertEqual(
                (registry_dir / "MODEL_SPEC").read_text().strip(),
                "media-of-langue/awesome-en-ja-prod",
            )
            status = build_status(
                tmp,
                "en-ja",
                local_dir_name="awesome_model_without_co",
            )
            self.assertEqual(status["selection"]["model_spec"], "media-of-langue/awesome-en-ja-prod")
            self.assertEqual(status["selection"]["resolution_source"], "repo_registry_spec")

    def test_build_status_reports_runtime_failure_for_missing_explicit_local_path(self):
        with tempfile.TemporaryDirectory(prefix="awesome-registry-") as tmp:
            missing_path = str(Path(tmp) / "missing-model")
            registry_dir = Path(tmp) / "models" / "en-ja" / "awesome-align" / "production"
            registry_dir.mkdir(parents=True)
            (registry_dir / "MODEL_SPEC").write_text(missing_path + "\n")
            status = build_status(tmp, "en-ja")
            self.assertFalse(status["runtime_check"]["ok"])
            self.assertIn("missing local model path", status["runtime_check"]["error_message"])

    def test_build_status_reports_cached_remote_model(self):
        with tempfile.TemporaryDirectory(prefix="awesome-registry-") as tmp:
            register_model(
                tmp,
                "en-ja",
                "bert-base-multilingual-cased",
                force=True,
            )
            fake_transformers = type(
                "FakeTransformers",
                (),
                {
                    "BertConfig": type(
                        "FakeBertConfig",
                        (),
                        {
                            "from_pretrained": mock.Mock(return_value="config"),
                        },
                    )(),
                },
            )()
            with mock.patch.dict(sys.modules, {"transformers": fake_transformers}):
                status = build_status(tmp, "en-ja")
            self.assertTrue(status["model_spec_inspection"]["cached_locally"])


if __name__ == "__main__":
    unittest.main()
