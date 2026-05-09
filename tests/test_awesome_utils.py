import os
import sys
import tempfile
import types
import unittest
import warnings
from pathlib import Path
from unittest import mock


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from ltc.backends.alignment.awesome_utils import (
    build_awesome_input_ids_and_subword_map,
    build_model_selection,
    canonical_awesome_model_registry_dir_from_root,
    check_awesome_model_runtime,
    default_root_for_alignment_module,
    inspect_awesome_model_spec,
    ensure_production_model,
    load_awesome_model_and_tokenizer,
    missing_awesome_model_files,
    MODEL_INFO_FILENAME,
    MODEL_SPEC_FILENAME,
    resolve_awesome_model_selection,
    resolve_awesome_model_spec,
    warn_on_smoke_model,
)
from ltc.errors import ProductionModelRequiredError


class AwesomeUtilsTest(unittest.TestCase):
    def _fake_transformers_module(
        self,
        *,
        model_side_effect=None,
        tokenizer_side_effect=None,
        config_side_effect=None,
        model_return="model",
        tokenizer_return="tokenizer",
        config_return="config",
    ):
        fake_module = types.SimpleNamespace()
        fake_module.BertModel = types.SimpleNamespace(
            from_pretrained=mock.Mock(
                side_effect=model_side_effect, return_value=model_return
            )
        )
        fake_module.BertTokenizer = types.SimpleNamespace(
            from_pretrained=mock.Mock(
                side_effect=tokenizer_side_effect, return_value=tokenizer_return
            )
        )
        fake_module.BertConfig = types.SimpleNamespace(
            from_pretrained=mock.Mock(
                side_effect=config_side_effect, return_value=config_return
            )
        )
        return fake_module

    def test_default_root_prefers_repo_root_when_env_missing(self):
        file_path = "/tmp/example/src/alignment/en_ja/__init__.py"
        with unittest.mock.patch.dict(os.environ, {}, clear=False):
            root = default_root_for_alignment_module(file_path)
        self.assertEqual(root, str(Path("/tmp/example").resolve()))

    def test_resolve_model_spec_prefers_pair_specific_env(self):
        file_path = "/tmp/example/src/alignment/en_ja/__init__.py"
        with unittest.mock.patch.dict(
            os.environ,
            {"LTC_AWESOME_ALIGN_MODEL_EN_JA": "custom-model"},
            clear=False,
        ):
            spec = resolve_awesome_model_spec(
                file_path, "awesome_model_without_co", pair_name="en_ja"
            )
        self.assertEqual(spec, "custom-model")

    def test_resolve_model_spec_falls_back_to_local_dir(self):
        with tempfile.TemporaryDirectory(prefix="awesome-utils-") as tmp:
            repo_root = Path(tmp)
            model_dir = repo_root / "src" / "model" / "awesome_model_without_co"
            model_dir.mkdir(parents=True)
            file_path = str(repo_root / "src" / "alignment" / "en_ja" / "__init__.py")
            with unittest.mock.patch.dict(os.environ, {}, clear=False):
                spec = resolve_awesome_model_spec(
                    file_path, "awesome_model_without_co", pair_name="en_ja"
                )
            self.assertEqual(spec, str(model_dir.resolve()))

    def test_resolve_model_selection_prefers_canonical_registry_files(self):
        with tempfile.TemporaryDirectory(prefix="awesome-utils-") as tmp:
            repo_root = Path(tmp)
            registry_dir = canonical_awesome_model_registry_dir_from_root(
                repo_root, "en_ja"
            )
            registry_dir.mkdir(parents=True)
            for file_name in (
                "config.json",
                "pytorch_model.bin",
                "special_tokens_map.json",
                "tokenizer_config.json",
                "vocab.txt",
            ):
                (registry_dir / file_name).write_text("stub")
            (registry_dir / MODEL_INFO_FILENAME).write_text('{"label": "prod"}')

            selection = resolve_awesome_model_selection(
                repo_root / "src" / "alignment" / "en_ja" / "__init__.py",
                "awesome_model_without_co",
                pair_name="en_ja",
            )

        self.assertEqual(selection.resolution_source, "repo_registry_files")
        self.assertEqual(selection.registry_dir, str(registry_dir.resolve()))
        self.assertEqual(selection.metadata, {"label": "prod"})
        self.assertTrue(selection.production_ready)

    def test_resolve_model_selection_uses_registry_model_spec(self):
        with tempfile.TemporaryDirectory(prefix="awesome-utils-") as tmp:
            repo_root = Path(tmp)
            registry_dir = canonical_awesome_model_registry_dir_from_root(
                repo_root, "en_ja"
            )
            registry_dir.mkdir(parents=True)
            (registry_dir / MODEL_SPEC_FILENAME).write_text("my-prod-model\n")
            (registry_dir / MODEL_INFO_FILENAME).write_text('{"label": "prod"}')

            selection = resolve_awesome_model_selection(
                repo_root / "src" / "alignment" / "en_ja" / "__init__.py",
                "awesome_model_without_co",
                pair_name="en_ja",
            )

        self.assertEqual(selection.model_spec, "my-prod-model")
        self.assertEqual(selection.resolution_source, "repo_registry_spec")
        self.assertEqual(selection.metadata, {"label": "prod"})

    def test_resolve_model_spec_uses_fallback_model_name(self):
        file_path = "/tmp/example/src/alignment/en_ja/__init__.py"
        with unittest.mock.patch.dict(os.environ, {}, clear=False):
            spec = resolve_awesome_model_spec(
                file_path, "awesome_model_without_co", pair_name="en_ja"
            )
        self.assertEqual(spec, "bert-base-multilingual-cased")

    def test_resolve_model_selection_marks_fallback_as_smoke_profile(self):
        file_path = "/tmp/example/src/alignment/en_ja/__init__.py"
        with unittest.mock.patch.dict(os.environ, {}, clear=False):
            selection = resolve_awesome_model_selection(
                file_path, "awesome_model_without_co", pair_name="en_ja"
            )
        self.assertEqual(selection.profile, "smoke/dev")
        self.assertFalse(selection.production_ready)
        self.assertEqual(selection.resolution_source, "fallback_default")

    def test_resolve_model_selection_marks_explicit_env_as_production_candidate(self):
        file_path = "/tmp/example/src/alignment/en_ja/__init__.py"
        with unittest.mock.patch.dict(
            os.environ,
            {"LTC_AWESOME_ALIGN_MODEL_EN_JA": "my-fine-tuned-model"},
            clear=False,
        ):
            selection = resolve_awesome_model_selection(
                file_path, "awesome_model_without_co", pair_name="en_ja"
            )
        self.assertEqual(selection.profile, "production-candidate")
        self.assertTrue(selection.production_ready)
        self.assertEqual(selection.resolution_source, "env:LTC_AWESOME_ALIGN_MODEL_EN_JA")

    def test_load_model_prefers_cached_model_name_without_network(self):
        fake_transformers = self._fake_transformers_module()
        with mock.patch.dict(sys.modules, {"transformers": fake_transformers}):
            model, tokenizer = load_awesome_model_and_tokenizer(
                "bert-base-multilingual-cased"
            )
        self.assertEqual(model, "model")
        self.assertEqual(tokenizer, "tokenizer")
        fake_transformers.BertModel.from_pretrained.assert_called_once_with(
            "bert-base-multilingual-cased", local_files_only=True
        )
        fake_transformers.BertTokenizer.from_pretrained.assert_called_once_with(
            "bert-base-multilingual-cased", local_files_only=True
        )

    def test_build_awesome_input_ids_and_subword_map_adds_special_tokens(self):
        class FakeTokenizer:
            cls_token_id = 101
            sep_token_id = 102
            model_max_length = 16

            def tokenize(self, word):
                return [word.lower(), f"{word.lower()}_x"]

            def convert_tokens_to_ids(self, tokens):
                if isinstance(tokens, str):
                    return len(tokens)
                return [len(token) for token in tokens]

        input_ids, sub2word_map = build_awesome_input_ids_and_subword_map(
            FakeTokenizer(), ["Alpha", "Beta"]
        )

        self.assertEqual(input_ids.tolist(), [101, 5, 7, 4, 6, 102])
        self.assertEqual(sub2word_map, [0, 0, 1, 1])

    def test_build_awesome_input_ids_and_subword_map_truncates_to_model_max_length(self):
        class FakeTokenizer:
            cls_token_id = 101
            sep_token_id = 102
            model_max_length = 5

            def tokenize(self, word):
                return [word, f"{word}_x"]

            def convert_tokens_to_ids(self, tokens):
                if isinstance(tokens, str):
                    return len(tokens)
                return [len(token) for token in tokens]

        input_ids, sub2word_map = build_awesome_input_ids_and_subword_map(
            FakeTokenizer(), ["a", "bb", "ccc"]
        )

        self.assertEqual(input_ids.tolist(), [101, 1, 3, 2, 102])
        self.assertEqual(sub2word_map, [0, 0, 1])

    def test_load_model_falls_back_to_online_load_when_cache_missing(self):
        model_calls = []
        tokenizer_calls = []

        def fake_model_loader(spec, local_files_only=False):
            model_calls.append((spec, local_files_only))
            if local_files_only:
                raise OSError("cache miss")
            return "model"

        def fake_tokenizer_loader(spec, local_files_only=False):
            tokenizer_calls.append((spec, local_files_only))
            if local_files_only:
                raise OSError("cache miss")
            return "tokenizer"

        fake_transformers = self._fake_transformers_module(
            model_side_effect=fake_model_loader,
            tokenizer_side_effect=fake_tokenizer_loader,
        )
        with mock.patch.dict(sys.modules, {"transformers": fake_transformers}):
            model, tokenizer = load_awesome_model_and_tokenizer(
                "bert-base-multilingual-cased"
            )

        self.assertEqual(model, "model")
        self.assertEqual(tokenizer, "tokenizer")
        self.assertEqual(
            model_calls,
            [
                ("bert-base-multilingual-cased", True),
                ("bert-base-multilingual-cased", False),
            ],
        )

    def test_missing_awesome_model_files_lists_required_files(self):
        with tempfile.TemporaryDirectory(prefix="awesome-model-") as tmp:
            model_dir = Path(tmp)
            (model_dir / "config.json").write_text("{}")
            missing = missing_awesome_model_files(model_dir)
        self.assertTrue(missing)
        self.assertTrue(any(path.name == "pytorch_model.bin" for path in missing))

    def test_runtime_check_rejects_incomplete_local_model_dir(self):
        with tempfile.TemporaryDirectory(prefix="awesome-model-") as tmp:
            model_dir = Path(tmp)
            (model_dir / "config.json").write_text("{}")
            with self.assertRaises(RuntimeError) as ctx:
                check_awesome_model_runtime(model_dir, backend_name="alignment.en_ja")
        self.assertIn("alignment.en_ja", str(ctx.exception))
        self.assertIn("pytorch_model.bin", str(ctx.exception))

    def test_runtime_check_accepts_cached_remote_model(self):
        fake_transformers = self._fake_transformers_module()
        with mock.patch.dict(sys.modules, {"transformers": fake_transformers}):
            check_awesome_model_runtime("bert-base-multilingual-cased")
        fake_transformers.BertConfig.from_pretrained.assert_called_once_with(
            "bert-base-multilingual-cased", local_files_only=True
        )

    def test_runtime_check_rejects_missing_explicit_local_path(self):
        with self.assertRaises(RuntimeError) as ctx:
            check_awesome_model_runtime(
                "/tmp/does-not-exist", backend_name="alignment.en_ja"
            )
        self.assertIn("missing local model path", str(ctx.exception))

    def test_inspect_model_spec_reports_cached_remote_model(self):
        fake_transformers = self._fake_transformers_module()
        with mock.patch.dict(sys.modules, {"transformers": fake_transformers}):
            inspection = inspect_awesome_model_spec("bert-base-multilingual-cased")
        self.assertEqual(inspection["kind"], "model_name")
        self.assertTrue(inspection["cached_locally"])

    def test_warn_on_smoke_model_emits_runtime_warning(self):
        selection = build_model_selection(
            "bert-base-multilingual-cased",
            resolution_source="fallback_default",
            fallback_model_name="bert-base-multilingual-cased",
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            warn_on_smoke_model(selection, "alignment.en_ja")
        self.assertEqual(len(caught), 1)
        self.assertIn("smoke/dev model", str(caught[0].message))

    def test_ensure_production_model_respects_guard(self):
        selection = build_model_selection(
            "bert-base-multilingual-cased",
            resolution_source="fallback_default",
            fallback_model_name="bert-base-multilingual-cased",
        )
        with mock.patch.dict(
            os.environ, {"LTC_REQUIRE_PRODUCTION_MODEL_EN_JA": "1"}, clear=False
        ):
            with self.assertRaises(ProductionModelRequiredError) as ctx:
                ensure_production_model(
                    selection, backend_name="alignment.en_ja", pair_name="en_ja"
                )
        self.assertIn("fallback smoke/dev model", str(ctx.exception))
