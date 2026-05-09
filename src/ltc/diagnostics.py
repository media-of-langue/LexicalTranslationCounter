"""Environment and backend diagnostics for LTC."""

from __future__ import annotations

import importlib
from dataclasses import asdict, dataclass


MODULE_GROUPS = {
    "normalizer": [
        "normalizer.de_normalizer",
        "normalizer.en_normalizer",
        "normalizer.es_normalizer",
        "normalizer.fr_normalizer",
        "normalizer.it_normalizer",
        "normalizer.ja_normalizer",
        "normalizer.ko_normalizer",
        "normalizer.zh_normalizer",
    ],
    "morphological": [
        "morphological.de_morphological",
        "morphological.en_morphological",
        "morphological.es_morphological",
        "morphological.fr_morphological",
        "morphological.it_morphological",
        "morphological.ja_morphological",
        "morphological.ko_morphological",
        "morphological.zh_morphological",
    ],
    "alignment": [
        "alignment.de_en",
        "alignment.en_es",
        "alignment.en_fr",
        "alignment.en_it",
        "alignment.en_ja",
        "alignment.en_ko",
        "alignment.en_zh",
        "alignment.fr_ja",
    ],
}


@dataclass(frozen=True)
class DiagnosticResult:
    name: str
    ok: bool
    error_type: str | None = None
    error_message: str | None = None
    note: str | None = None

    def as_dict(self):
        return asdict(self)


def probe_module(module_name):
    try:
        module = importlib.import_module(module_name)
        runtime_check = getattr(module, "runtime_check", None)
        if callable(runtime_check):
            runtime_check()
        note = None
        runtime_metadata = getattr(module, "runtime_metadata", None)
        if callable(runtime_metadata):
            metadata = runtime_metadata()
            if isinstance(metadata, dict):
                note = metadata.get("note")
            elif metadata is not None:
                note = str(metadata)
    except Exception as exc:  # pragma: no cover - broad by design for diagnostics
        return DiagnosticResult(
            name=module_name,
            ok=False,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
    return DiagnosticResult(name=module_name, ok=True, note=note)


def run_module_diagnostics(groups=None):
    if groups is None:
        groups = tuple(MODULE_GROUPS.keys())

    results = {}
    for group in groups:
        module_names = MODULE_GROUPS[group]
        results[group] = [probe_module(module_name) for module_name in module_names]
    return results


def count_failures(results):
    return sum(1 for group in results.values() for result in group if not result.ok)


def count_successes(results):
    return sum(1 for group in results.values() for result in group if result.ok)
