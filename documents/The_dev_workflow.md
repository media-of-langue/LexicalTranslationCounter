# The Development Workflow

This repository now supports a local-first workflow. Start small, use Docker
only when you truly need the full corpus images, and keep pair-specific changes
close to pair-specific smoke or quality projects.

## 1. Clone and update

```bash
git clone https://github.com/<<<your-github-account>>>/LexicalTranslationCounter.git
cd LexicalTranslationCounter
```

To sync with upstream:

```bash
git checkout main
git pull https://github.com/media-of-langue/LexicalTranslationCounter.git main
```

## 2. Pick the smallest useful workflow

At the moment, `de_en` and `en_ja` are the most up-to-date examples of the
intended local-first workflow. Some other language pairs still need more manual
or legacy runtime steps.

### Repository-wide refactors

Start here when you are changing package layout, docs, CLI entry points, or
shared helpers:

```bash
python3 -m unittest discover -s tests
```

### Pair smoke checks

Use a smoke project when you want to confirm that a language pair still runs:

- [projects/smoke/README.md](../projects/smoke/README.md)
- [projects/smoke/de_en/README.md](../projects/smoke/de_en/README.md)
- [projects/smoke/en_ja/README.md](../projects/smoke/en_ja/README.md)

### Pair quality work

Use a quality project when you are actively improving alignment output or
lexicalization logic:

- [projects/quality/en_ja/README.md](../projects/quality/en_ja/README.md)

### Pair training / data prep

Use a training project when you are preparing public corpora for fine-tuning:

- [projects/training/en_ja/README.md](../projects/training/en_ja/README.md)

## 3. Set up a local pair runtime

The setup helper is the most predictable path:

```bash
python3 scripts/setup_local_runtime.py --language-pair de-en
python3 scripts/setup_local_runtime.py --language-pair en-ja
```

If you only want to check the environment:

```bash
python3 scripts/setup_local_runtime.py --language-pair de-en --check-only
```

Some pairs also expose package extras in `pyproject.toml`, for example:

```bash
python3 -m pip install -e '.[de-en]'
python3 -m pip install -e '.[en-ja]'
```

## 4. Run the common checks

### Unit tests

```bash
python3 -m unittest discover -s tests
```

### Backend diagnostics

```bash
PYTHONPATH=src python3 -m ltc.cli.doctor --group normalizer
PYTHONPATH=src python3 -m ltc.cli.doctor --group morphological
PYTHONPATH=src python3 -m ltc.cli.doctor --group alignment
```

### Pair-specific smoke

Follow the commands in the pair smoke project README.

## 5. Make the change

When editing a pair:

- keep the smoke path working
- keep the docs for that pair current
- avoid introducing hidden fixed paths or private infrastructure

When editing shared code:

- prefer `src/ltc/` for new shared logic
- keep the legacy wrappers thin
- update root docs and pair docs together when the contributor workflow changes

## 6. Re-run the smallest meaningful verification

Examples:

- repo-wide code move: `python3 -m unittest discover -s tests`
- `de_en` runtime change: run the `de_en` smoke project
- `en_ja` quality change: run `core`, then `extended`, then observation/staging

## 7. Open a focused pull request

Keep pull requests small and scoped:

- one root cause per PR
- include the verification commands you actually ran
- mention pair-specific limitations honestly if a runtime still needs external
  models or tools

## 8. Use Docker only when needed

The Docker path is still available for full-data runs. See
[How to build and run from source](How_to_build_and_run_from_source.md) when you
need the full corpus and wordlist images.
