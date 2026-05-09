# Projects

This directory contains contributor-facing workflows that are lighter-weight than
the full Docker path.

## Current project types

- `smoke/`
  Small real-backend checks for specific language pairs.
- `quality/`
  Curated regression suites and inspection workflows.
- `training/`
  Data-preparation flows for model fine-tuning experiments.

## Recommended entry points

- Start with [smoke/README.md](smoke/README.md) if you want a pair-specific
  runtime check.
- Use [quality/en_ja/README.md](quality/en_ja/README.md) when you want to work
  on `en_ja` alignment quality, observation extraction, or lexicalization
  staging.
- Use [training/en_ja/README.md](training/en_ja/README.md) when you want to
  prepare public `en_ja` corpora for fine-tuning.

These projects do not replace the language-pair notes under `documents/`.
Instead, they provide the shortest practical path for contributors who want to
clone the repository, run something real, and make a focused change.

## Current refactor status

- `de_en`
  Local-first smoke project available and verified end to end.
- `en_ja`
  Local-first smoke, quality, observation, and staging workflows available.
- Other pairs
  Still partly legacy. Prefer reading the pair note under `documents/` before
  assuming the same local-first flow is already available.
