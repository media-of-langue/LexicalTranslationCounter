"""Helpers for loading Awesome Align-style transformer assets."""

from __future__ import annotations

import itertools
import json
import os
import warnings
from dataclasses import dataclass
from pathlib import Path

from ltc.errors import ProductionModelRequiredError

REQUIRED_AWESOME_MODEL_FILES = (
    "config.json",
    "pytorch_model.bin",
    "special_tokens_map.json",
    "tokenizer_config.json",
    "vocab.txt",
)
MODEL_SPEC_FILENAME = "MODEL_SPEC"
MODEL_INFO_FILENAME = "MODEL_INFO.json"
DEFAULT_AWESOME_LOCAL_MODEL_DIR_NAMES = {
    "de_en": "awesome_model_with_co",
    "en_fr": "awesome_model_without_co",
    "en_it": "awesome_model_with_co",
    "en_ja": "awesome_model_without_co",
    "en_zh": "awesome_model_without_co",
    "fr_ja": "awesome_model_without_co",
}


@dataclass(frozen=True)
class AwesomeModelSelection:
    model_spec: str
    resolution_source: str
    profile: str
    production_ready: bool
    fallback_model_name: str
    registry_dir: str | None = None
    metadata: dict | None = None

    @property
    def note(self):
        if self.production_ready:
            return f"{self.profile} model via {self.resolution_source}: {self.model_spec}"
        return (
            f"{self.profile} model via {self.resolution_source}: {self.model_spec} "
            f"(use a fine-tuned model before production runs)"
        )


def repo_root_from_alignment_file(file_path):
    return Path(file_path).resolve().parents[3]


def default_root_for_alignment_module(file_path):
    return os.environ.get("ROOT", str(repo_root_from_alignment_file(file_path)))


def normalize_pair_name(pair_name, separator="_"):
    normalized = pair_name.strip().lower().replace("-", "_")
    if separator == "-":
        return normalized.replace("_", "-")
    return normalized


def default_local_dir_name_for_pair(pair_name):
    return DEFAULT_AWESOME_LOCAL_MODEL_DIR_NAMES.get(
        normalize_pair_name(pair_name, separator="_")
    )


def default_alignment_module_path(root, pair_name):
    return (
        Path(root).resolve()
        / "src"
        / "alignment"
        / normalize_pair_name(pair_name, separator="_")
        / "__init__.py"
    )


def canonical_awesome_model_registry_dir_from_root(root, pair_name):
    return (
        Path(root).resolve()
        / "models"
        / normalize_pair_name(pair_name, separator="-")
        / "awesome-align"
        / "production"
    )


def canonical_awesome_model_registry_dir(file_path, pair_name):
    return canonical_awesome_model_registry_dir_from_root(
        default_root_for_alignment_module(file_path), pair_name
    )


def read_model_metadata(path):
    metadata_path = Path(path) / MODEL_INFO_FILENAME
    if not metadata_path.is_file():
        return None
    try:
        return json.loads(metadata_path.read_text())
    except json.JSONDecodeError:
        return None


def read_registered_model_spec(registry_dir):
    registry_dir = Path(registry_dir)
    if not registry_dir.is_dir():
        return None

    missing_files = missing_awesome_model_files(registry_dir)
    if not missing_files:
        return {
            "model_spec": str(registry_dir.resolve()),
            "resolution_source": "repo_registry_files",
            "metadata": read_model_metadata(registry_dir),
            "registry_dir": str(registry_dir.resolve()),
        }

    spec_path = registry_dir / MODEL_SPEC_FILENAME
    if not spec_path.is_file():
        return None
    model_spec = spec_path.read_text().strip()
    if not model_spec:
        return None
    return {
        "model_spec": model_spec,
        "resolution_source": "repo_registry_spec",
        "metadata": read_model_metadata(registry_dir),
        "registry_dir": str(registry_dir.resolve()),
    }


def resolve_awesome_model_spec(
    file_path,
    local_dir_name,
    pair_name=None,
    fallback_model_name="bert-base-multilingual-cased",
):
    return resolve_awesome_model_selection(
        file_path,
        local_dir_name,
        pair_name=pair_name,
        fallback_model_name=fallback_model_name,
    ).model_spec


def resolve_awesome_model_selection(
    file_path,
    local_dir_name,
    pair_name=None,
    fallback_model_name="bert-base-multilingual-cased",
):
    env_candidates = []
    if pair_name:
        env_candidates.append(f"LTC_AWESOME_ALIGN_MODEL_{pair_name.upper()}")
    env_candidates.extend(
        [
            "LTC_AWESOME_ALIGN_MODEL",
            "LTC_AWESOME_ALIGN_MODEL_PATH",
        ]
    )

    for env_name in env_candidates:
        value = os.environ.get(env_name)
        if value:
            return build_model_selection(
                value,
                resolution_source=f"env:{env_name}",
                fallback_model_name=fallback_model_name,
            )

    if pair_name:
        registry_payload = read_registered_model_spec(
            canonical_awesome_model_registry_dir(file_path, pair_name)
        )
        if registry_payload:
            return build_model_selection(
                registry_payload["model_spec"],
                resolution_source=registry_payload["resolution_source"],
                fallback_model_name=fallback_model_name,
                registry_dir=registry_payload["registry_dir"],
                metadata=registry_payload["metadata"],
            )

    root = default_root_for_alignment_module(file_path)
    local_path = Path(root) / "src" / "model" / local_dir_name
    if local_path.is_dir():
        return build_model_selection(
            str(local_path),
            resolution_source=f"repo_local:{local_dir_name}",
            fallback_model_name=fallback_model_name,
            metadata=read_model_metadata(local_path),
        )

    return build_model_selection(
        fallback_model_name,
        resolution_source="fallback_default",
        fallback_model_name=fallback_model_name,
    )


def build_model_selection(
    model_spec,
    resolution_source,
    fallback_model_name,
    registry_dir=None,
    metadata=None,
):
    production_ready = model_spec != fallback_model_name
    profile = "production-candidate" if production_ready else "smoke/dev"
    return AwesomeModelSelection(
        model_spec=model_spec,
        resolution_source=resolution_source,
        profile=profile,
        production_ready=production_ready,
        fallback_model_name=fallback_model_name,
        registry_dir=registry_dir,
        metadata=metadata,
    )


def load_awesome_model_and_tokenizer(model_spec):
    import transformers

    model_path = Path(model_spec)
    if model_path.exists():
        model = transformers.BertModel.from_pretrained(str(model_path), local_files_only=True)
        tokenizer = transformers.BertTokenizer.from_pretrained(
            str(model_path), local_files_only=True
        )
        return model, tokenizer

    try:
        model = transformers.BertModel.from_pretrained(
            model_spec, local_files_only=True
        )
        tokenizer = transformers.BertTokenizer.from_pretrained(
            model_spec, local_files_only=True
        )
        return model, tokenizer
    except OSError:
        pass

    model = transformers.BertModel.from_pretrained(model_spec)
    tokenizer = transformers.BertTokenizer.from_pretrained(model_spec)
    return model, tokenizer


def build_awesome_input_ids_and_subword_map(tokenizer, words):
    import torch

    word_tokens = [tokenizer.tokenize(word) for word in words]
    token_ids_per_word = [
        tokenizer.convert_tokens_to_ids(tokens) for tokens in word_tokens
    ]
    flat_token_ids = list(itertools.chain(*token_ids_per_word))
    sub2word_map = [
        word_index
        for word_index, tokens in enumerate(word_tokens)
        for _ in tokens
    ]

    max_length = getattr(tokenizer, "model_max_length", None)
    if isinstance(max_length, int) and 0 < max_length < 10**8:
        max_body_length = max(max_length - 2, 0)
        flat_token_ids = flat_token_ids[:max_body_length]
        sub2word_map = sub2word_map[:max_body_length]

    cls_token_id = getattr(tokenizer, "cls_token_id", None)
    sep_token_id = getattr(tokenizer, "sep_token_id", None)
    if cls_token_id is None and getattr(tokenizer, "cls_token", None) is not None:
        cls_token_id = tokenizer.convert_tokens_to_ids(tokenizer.cls_token)
    if sep_token_id is None and getattr(tokenizer, "sep_token", None) is not None:
        sep_token_id = tokenizer.convert_tokens_to_ids(tokenizer.sep_token)
    if cls_token_id is None or sep_token_id is None:
        raise RuntimeError(
            f"{type(tokenizer).__name__} is missing cls/sep token ids required "
            "for Awesome Align preprocessing."
        )

    input_ids = torch.tensor(
        [cls_token_id, *flat_token_ids, sep_token_id], dtype=torch.long
    )
    return input_ids, sub2word_map


def missing_awesome_model_files(model_dir):
    model_path = Path(model_dir)
    return [
        model_path / file_name
        for file_name in REQUIRED_AWESOME_MODEL_FILES
        if not (model_path / file_name).exists()
    ]


def has_cached_awesome_model(model_spec):
    import transformers

    try:
        transformers.BertConfig.from_pretrained(model_spec, local_files_only=True)
    except OSError:
        return False
    return True


def looks_like_explicit_local_path(model_spec):
    expanded = os.path.expanduser(model_spec)
    return (
        os.path.isabs(expanded)
        or expanded.startswith(".")
        or expanded.startswith("~")
    )


def inspect_awesome_model_spec(model_spec):
    model_path = Path(model_spec).expanduser()
    if model_path.exists():
        resolved = str(model_path.resolve())
        if not model_path.is_dir():
            return {
                "kind": "local_path_not_directory",
                "path": resolved,
                "exists": True,
                "cached_locally": False,
                "missing_files": [],
            }
        missing_files = missing_awesome_model_files(model_path)
        return {
            "kind": "local_dir",
            "path": resolved,
            "exists": True,
            "cached_locally": False,
            "missing_files": [str(path) for path in missing_files],
        }

    if looks_like_explicit_local_path(model_spec):
        return {
            "kind": "local_path_missing",
            "path": str(model_path),
            "exists": False,
            "cached_locally": False,
            "missing_files": [],
        }

    return {
        "kind": "model_name",
        "path": None,
        "exists": False,
        "cached_locally": has_cached_awesome_model(model_spec),
        "missing_files": [],
    }


def check_awesome_model_runtime(model_spec, backend_name=None):
    label = backend_name or "awesome-align backend"
    inspection = inspect_awesome_model_spec(model_spec)

    if inspection["kind"] == "local_dir":
        missing_files = inspection["missing_files"]
        if missing_files:
            missing_names = ", ".join(Path(path).name for path in missing_files)
            raise RuntimeError(
                f"{label} is missing model files under {inspection['path']}: "
                f"{missing_names}"
            )
        return

    if inspection["kind"] == "local_path_not_directory":
        raise RuntimeError(
            f"{label} points to {inspection['path']}, but Awesome Align expects "
            "a model directory."
        )

    if inspection["kind"] == "local_path_missing":
        raise RuntimeError(
            f"{label} points to a missing local model path: {inspection['path']}"
        )

    if inspection["cached_locally"]:
        return


def production_guard_enabled(pair_name=None):
    env_candidates = []
    if pair_name:
        env_candidates.append(f"LTC_REQUIRE_PRODUCTION_MODEL_{pair_name.upper()}")
    env_candidates.append("LTC_REQUIRE_PRODUCTION_MODEL")
    for env_name in env_candidates:
        value = os.environ.get(env_name)
        if value and value.lower() in ("1", "true", "yes", "on"):
            return True
    return False


def ensure_production_model(selection, backend_name, pair_name=None):
    if selection.production_ready:
        return
    if production_guard_enabled(pair_name=pair_name):
        raise ProductionModelRequiredError(
            f"{backend_name} is using the fallback smoke/dev model "
            f"{selection.model_spec!r}. Configure a fine-tuned model before "
            "running with LTC_REQUIRE_PRODUCTION_MODEL enabled."
        )


def warn_on_smoke_model(selection, backend_name):
    if selection.production_ready:
        return
    warnings.warn(
        (
            f"{backend_name} is using the fallback smoke/dev model "
            f"{selection.model_spec!r}. This is fine for local checks, but pin "
            "a fine-tuned model before production runs."
        ),
        RuntimeWarning,
        stacklevel=2,
    )
