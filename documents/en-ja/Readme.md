## Awesome Align model resolution

The `en_ja` backend resolves its Awesome Align model in the following order:

1. `LTC_AWESOME_ALIGN_MODEL_EN_JA`
2. `LTC_AWESOME_ALIGN_MODEL`
3. `LTC_AWESOME_ALIGN_MODEL_PATH`
4. `models/en-ja/awesome-align/production/`
5. `src/model/awesome_model_without_co/`
6. `bert-base-multilingual-cased`

## Preferred: register a canonical production model

If you want to pin a production Awesome Align model locally, access
https://github.com/neulab/awesome-align and download the
[multilingually fine-tuned w/o --train_co, softmax model](https://drive.google.com/file/d/1IluQED1jb0rjITJtyj4lNMPmaRFyMslg/view?usp=sharing)

Then register it under the canonical local registry:

```bash
PYTHONPATH=src python3 -m ltc.cli.register_awesome_model \
  --pair en-ja \
  --source /path/to/extracted/model \
  --copy-files
```

This creates or replaces:

```text
models/en-ja/awesome-align/production/
```

Check the current resolution state with:

```bash
PYTHONPATH=src python3 -m ltc.cli.awesome_model_status --pair en-ja
```

## Still supported during migration

Legacy local directories are still supported. If needed, create
`src/model/awesome_model_without_co/` in this repository and save the extracted
contents there. If you run local commands with `ROOT=$(pwd)`, that resolves to:

```text
$ROOT/src/model/awesome_model_without_co/
```

In the Docker runtime, the same files must be available at:

```text
/root/src/model/awesome_model_without_co/
```

If you do not set a local model path, the first real `en_ja` run may download
`bert-base-multilingual-cased` from Hugging Face and cache it locally.

This fallback is useful for smoke tests and local checks, but it should not be
treated as the production default.

If you want the runtime to fail fast unless a non-fallback model is configured,
set:

```
LTC_REQUIRE_PRODUCTION_MODEL=1
```

## Install the default Japanese text backend

The current default Japanese text backend is `sudachi_a`, so the common local
setup path is now the Sudachi-based runtime:

```
python3 scripts/setup_local_runtime.py --language-pair en-ja
```

If you also want the legacy Juman++ comparison path, install Juman++ and make
the `jumanpp` command available on `PATH`.

On macOS with Homebrew:

```
brew install jumanpp
```

The main Japanese-processing code is now organized under:

- `src/ltc/japanese/backends.py`
- `src/ltc/japanese/morphology.py`
- `src/ltc/japanese/normalization.py`

The legacy `src/morphological/ja_morphological.py` and
`src/normalizer/ja_normalizer.py` files remain as compatibility wrappers.

## Small local smoke run

For the smallest tracked-data run, see
[projects/smoke/en_ja/README.md](../../projects/smoke/en_ja/README.md).

## Compare smoke and production models

After you pin a non-fallback model locally, compare it against the smoke model
with:

```bash
PYTHONPATH=src python3 -m ltc.cli.compare_en_ja_models \
  --case objective_sentence_core_relations \
  --left-model bert-base-multilingual-cased \
  --right-model models/en-ja/awesome-align/production \
  --left-label smoke \
  --right-label production
```

This is the quickest way to check whether a remaining error is mostly caused by
the alignment model itself or by postprocessing / normalization.

If you registered only a `MODEL_SPEC` instead of copying the files, use the
resolved model spec shown by `ltc.cli.awesome_model_status` as `--right-model`.

## Audit a few tracked corpus rows

If the curated quality cases still feel too small, run the tracked-corpus audit:

```bash
PYTHONPATH=src python3 -m ltc.cli.audit_en_ja_corpus \
  --row-id 2 \
  --row-id 4 \
  --row-id 10
```

This is a lightweight contributor-facing way to look at a few real `en_ja`
rows before deciding whether a relation is stable enough to promote into the
curated suite.

The quality suite now has a fast `core` layer and a broader `extended` layer:

```bash
PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --fail-on-error
PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --suite extended --fail-on-error
```

There is also a second fresh sample pack built from unseen tracked-corpus rows:

```bash
PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality \
  --cases projects/quality/en_ja/sample_pack_2.json \
  --suite core \
  --fail-on-error
```

And a third fresh pack built from another unseen slice:

```bash
PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality \
  --cases projects/quality/en_ja/sample_pack_3.json \
  --suite core \
  --fail-on-error
```

To compare the legacy `jumanpp` path and the Sudachi-first path directly on the
tracked corpus, use:

```bash
PYTHONPATH=src python3 -m ltc.cli.compare_en_ja_corpus_backends \
  --left-backend jumanpp \
  --right-backend sudachi_a \
  --limit 100 \
  --only-different
```

For critical review, prefer a reproducible sample over always taking the first
rows:

```bash
PYTHONPATH=src python3 -m ltc.cli.compare_en_ja_corpus_backends \
  --left-backend jumanpp \
  --right-backend sudachi_a \
  --selection random \
  --seed 17 \
  --limit 40 \
  --only-different

PYTHONPATH=src python3 -m ltc.cli.compare_en_ja_corpus_backends \
  --left-backend jumanpp \
  --right-backend sudachi_a \
  --selection stratified \
  --seed 17 \
  --limit 40 \
  --only-different
```

You can also compare Japanese text backends by setting
`LTC_JA_TEXT_BACKEND` before the run:

```bash
LTC_JA_TEXT_BACKEND=jumanpp PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --fail-on-error
LTC_JA_TEXT_BACKEND=fugashi_unidic PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --fail-on-error
LTC_JA_TEXT_BACKEND=sudachi_a PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --fail-on-error
```

Supported values:

- `sudachi_a`
- `sudachi_b`
- `sudachi_c`
- `fugashi_unidic`
- `jumanpp`

## Fine-tuning data strategy

For the current recommendation on public data sources for `en_ja` fine-tuning,
see [Fine_tuning_Data_Strategy.md](Fine_tuning_Data_Strategy.md).

The first repository workflow for preparing those public corpora lives at
[projects/training/en_ja/README.md](../../projects/training/en_ja/README.md).

If your local public corpus copy is not already in the repository's canonical
TSV shape, convert it first with:

```bash
PYTHONPATH=src python3 -m ltc.cli.convert_en_ja_public_source \
  paired-tsv \
  --source-name jparacrawl \
  --input-path /path/to/input.tsv \
  --output-path /path/to/jparacrawl_en_ja.tsv
```

To compare backend families instead of only model specs, set the backend flags:

```bash
PYTHONPATH=src python3 -m ltc.cli.compare_en_ja_models \
  --case stable_sentence_suppresses_get_noise \
  --left-backend awesome \
  --left-model bert-base-multilingual-cased \
  --right-backend simalign \
  --right-simalign-method inter \
  --right-simalign-model bert \
  --left-label awesome \
  --right-label simalign-inter
```

The current SimAlign route is meant for comparison, not as a drop-in
production default. Its raw alignments are real SimAlign output, but the
downstream relation extraction still uses LTC-specific postprocessing.
