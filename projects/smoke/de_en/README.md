# de_en Smoke Project

This is the smallest contributor-friendly path for checking the current `de_en`
alignment path without using Docker.

## What this smoke project is for

Use this when you want to confirm that:

- the German and English runtime dependencies install correctly
- the `de_en` alignment path still runs end to end
- a repository-wide refactor did not break the legacy `count_function.py` flow

This is not a quality benchmark. It is only a real-backend smoke check.

## Runtime notes

Read [documents/de-en/Readme.md](../../../documents/de-en/Readme.md) first for
pair-specific notes.

`de_en` now resolves its Awesome Align model in this order:

1. `LTC_AWESOME_ALIGN_MODEL_DE_EN`
2. `LTC_AWESOME_ALIGN_MODEL`
3. canonical repo registry: `models/de-en/awesome-align/production/`
4. legacy local path: `src/model/awesome_model_with_co/`
5. fallback: `bert-base-multilingual-cased`

The default German spaCy model is `de_dep_news_trf`. If you want to experiment
with a lighter local setup, you can override it with `LTC_DE_SPACY_MODEL`, for
example `de_core_news_sm`, as long as that model is already installed.

## Local setup

The setup helper creates `.venv`, installs the pair runtime, downloads NLTK
data, and checks the local Python environment:

```bash
python3 scripts/setup_local_runtime.py --language-pair de-en
```

If you prefer the package-based path, install the pair extra:

```bash
python3 -m pip install -e '.[de-en]'
python3 -m spacy download de_dep_news_trf
```

## Quick doctor check

```bash
PYTHONPATH=src python3 -m ltc.cli.doctor --group alignment
```

You should see `alignment.de_en` either as `OK` or as a concrete missing-model
error instead of the old fixed `/root/src/model/...` failure mode.

## Small real-backend run

Use the tiny tracked fixture under `projects/smoke/de_en/input/`:

```bash
ROOT=$(pwd) .venv/bin/python src/count_function.py 0 de en \
  --input-dir projects/smoke/de_en/input \
  --output-dir .tmp/de_en_smoke \
  --max-rows 3
```

At the end of the run, check:

- `relations_de_en_*.csv` under `.tmp/de_en_smoke/`
- `corpus_de_en.csv` under `.tmp/de_en_smoke/`
- `timing_de_en.json` under `.tmp/de_en_smoke/`

To start fresh, remove `.tmp/de_en_smoke/`.
