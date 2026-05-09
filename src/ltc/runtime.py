"""Compatibility loaders for the current language-specific implementations."""

import importlib


def load_alignment_runtime(language_pair):
    module = importlib.import_module(f"alignment.{language_pair}")
    return module.alignment, module.alignment_batch


def load_normalizer(language_code):
    module = importlib.import_module(f"normalizer.{language_code}_normalizer")
    return getattr(module, f"{language_code}_normalizer")
