# en-ja Smoke Project

This is the smallest contributor-friendly path for checking the current `en_ja`
pipeline on tracked test data.

## Goal

Run the real `en_ja` alignment backend on a tiny tracked fixture without Docker
and confirm that:

- the Python dependencies are installed
- the default Sudachi-based Japanese path is available
- the alignment path runs end to end

## 1. Prepare the local runtime

Create `.venv` and install the Python dependencies for `en-ja`.

```bash
python3 scripts/setup_local_runtime.py --language-pair en-ja
```

This prepares the Sudachi-based default runtime. If you also want the legacy
Juman++ comparison path, install Juman++ separately:

```bash
brew install jumanpp
```

By default, `en_ja` resolves its Awesome Align model in this order:

1. `LTC_AWESOME_ALIGN_MODEL_EN_JA`
2. `LTC_AWESOME_ALIGN_MODEL`
3. `LTC_AWESOME_ALIGN_MODEL_PATH`
4. `src/model/awesome_model_without_co/`
5. `bert-base-multilingual-cased`

If you do not set a local model path, the first real run may download
`bert-base-multilingual-cased` from Hugging Face and cache it locally.

This fallback is intentionally treated as a smoke/dev model, not as the
production default.

## 2. Check the runtime

```bash
PYTHONPATH=src python3 -m ltc.cli.doctor \
  --group normalizer \
  --group morphological \
  --group alignment
```

## 3. Run the smoke test

```bash
ROOT=$(pwd) .venv/bin/python src/count_function.py 0 en ja \
  --input-dir projects/smoke/en_ja/input \
  --output-dir .tmp/en_ja_smoke \
  --max-rows 3
```

Expected result:

- `relations_en_ja_*.csv` are written under `.tmp/en_ja_smoke/`
- `corpus_en_ja.csv` is written under `.tmp/en_ja_smoke/`
- a timing summary is printed at the end

## Notes

- This fixture is for operation checks, not alignment-quality evaluation.
- The default Japanese backend is `sudachi_a`. Set
  `LTC_JA_TEXT_BACKEND=jumanpp` only when you explicitly want the legacy path.
- The first run is still heavy because the current backend loads a multilingual
  BERT model. The small wordlists keep the rest of the pipeline fast.
- Before production runs, set `LTC_REQUIRE_PRODUCTION_MODEL=1` so the process
  fails fast unless a non-fallback model has been configured.
- To start fresh, remove `.tmp/en_ja_smoke/`.
