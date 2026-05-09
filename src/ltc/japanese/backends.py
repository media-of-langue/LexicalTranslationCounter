"""Backend selection and runtime checks for Japanese text processing."""

from __future__ import annotations

import importlib
import os
import shutil


DEFAULT_JAPANESE_TEXT_BACKEND = "sudachi_a"
BACKEND_ALIASES = {
    "juman": "jumanpp",
    "jumanpp": "jumanpp",
    "fugashi": "fugashi_unidic",
    "fugashi_unidic": "fugashi_unidic",
    "sudachi": "sudachi_a",
    "sudachi_a": "sudachi_a",
    "sudachi_b": "sudachi_b",
    "sudachi_c": "sudachi_c",
}
SUPPORTED_JAPANESE_TEXT_BACKENDS = tuple(dict.fromkeys(BACKEND_ALIASES.values()))


def parse_japanese_text_backend_name(value: str | None = None) -> str:
    raw_value = (
        value
        if value is not None
        else os.environ.get("LTC_JA_TEXT_BACKEND", DEFAULT_JAPANESE_TEXT_BACKEND)
    )
    normalized = BACKEND_ALIASES.get((raw_value or "").strip().lower())
    if normalized is None:
        allowed = ", ".join(sorted(SUPPORTED_JAPANESE_TEXT_BACKENDS))
        raise ValueError(f"LTC_JA_TEXT_BACKEND must be one of: {allowed}")
    return normalized


def current_japanese_text_backend_name() -> str:
    return parse_japanese_text_backend_name()


def runtime_check_japanese_text_backend(backend_name: str | None = None) -> str:
    backend_name = parse_japanese_text_backend_name(backend_name)
    if backend_name == "jumanpp":
        importlib.import_module("pyknp")
        if shutil.which("jumanpp") is None:
            raise RuntimeError("jumanpp is not available on PATH")
        return backend_name
    if backend_name == "fugashi_unidic":
        importlib.import_module("fugashi")
        return backend_name
    if backend_name in {"sudachi_a", "sudachi_b", "sudachi_c"}:
        sudachipy = importlib.import_module("sudachipy")
        getattr(sudachipy, "Dictionary")().create()
        return backend_name
    raise RuntimeError(f"unsupported Japanese text backend: {backend_name}")
