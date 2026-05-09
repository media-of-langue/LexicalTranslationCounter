# en-ja Fine-tuning Data Preparation

This project prepares public `en_ja` parallel corpora into a source-aware
manifest plus Awesome Align training files.

## Goal

Produce:

- `manifest.tsv`
- `awesome_train.txt`
- `awesome_dev.txt`
- `awesome_test.txt`
- `summary.json`

from local copies of public corpora such as:

- JParaCrawl
- ASPEC-JE
- JESC

The repository does **not** ship these corpora. You download them yourself
under the terms of each dataset, then point the config at your local files.

## Recommended sources

See [documents/en-ja/Fine_tuning_Data_Strategy.md](../../../documents/en-ja/Fine_tuning_Data_Strategy.md).

## Canonical local shape

The repository wants each public source in a simple local TSV with:

```text
english<TAB>japanese
```

One sentence pair per line.

The easiest contributor workflow is:

1. download a public source yourself under its official terms
2. convert it into the canonical TSV with `ltc-convert-en-ja-public-source`
3. copy the emitted config fragment into your `public_sources.json`
4. run `ltc-prepare-en-ja-finetune-data`

The current preparer also supports:

- `awesome_plaintext`: `english ||| japanese`
- `jsonl`: configurable source/target keys

## Config

Start from:

`projects/training/en_ja/public_sources.example.json`

Copy it and replace the placeholder `raw/...` paths with your local files.

## Convert raw public sources

### Parallel text files

If a source is already split into aligned English and Japanese text files, use:

```bash
PYTHONPATH=src python3 -m ltc.cli.convert_en_ja_public_source \
  parallel-files \
  --source-name jesc \
  --source-file raw/jesc/train.en \
  --target-file raw/jesc/train.ja \
  --output-path raw/jesc.tsv
```

### Paired TSV or CSV

If a source already comes as a paired table, use:

```bash
PYTHONPATH=src python3 -m ltc.cli.convert_en_ja_public_source \
  paired-tsv \
  --source-name jparacrawl \
  --input-path raw/jparacrawl.tsv \
  --output-path raw/jparacrawl_en_ja.tsv \
  --source-column 0 \
  --target-column 1 \
  --delimiter '\t'
```

If your file is CSV with a header and the columns are reversed, adjust the
column indices and add `--skip-header`.

### Raw ASPEC-JE files

ASPEC-JE is the main source that usually needs a real format-specific
converter because the raw train/dev/test files include metadata fields.

```bash
PYTHONPATH=src python3 -m ltc.cli.convert_en_ja_public_source \
  aspec-je \
  --input-dir raw/aspec_je \
  --output-path raw/aspec_je.tsv
```

Or specify files directly:

```bash
PYTHONPATH=src python3 -m ltc.cli.convert_en_ja_public_source \
  aspec-je \
  --input-path raw/aspec_je/train1.txt \
  --input-path raw/aspec_je/dev.txt \
  --input-path raw/aspec_je/test.txt \
  --output-path raw/aspec_je.tsv
```

Each conversion command prints a `config fragment` you can paste directly into
your `public_sources.json`.

For ASPEC-JE specifically, `--input-dir` collects matching `train*.txt`,
`dev*.txt`, and `test*.txt` files together. If you want tighter control over
which official split files are included, pass explicit `--input-path` values
instead.

## Run

```bash
PYTHONPATH=src python3 -m ltc.cli.prepare_en_ja_finetune_data \
  --config projects/training/en_ja/public_sources.example.json \
  --output-dir src/data/training/en_ja_public_mix
```

Or, with installed entry points:

```bash
ltc-prepare-en-ja-finetune-data \
  --config projects/training/en_ja/public_sources.example.json \
  --output-dir src/data/training/en_ja_public_mix
```

## What the preparer does

- normalizes whitespace
- applies Unicode normalization
- drops empty pairs
- drops exact same-string source/target pairs
- applies simple character-length and length-ratio filters
- deduplicates exact normalized pairs across all sources
- assigns stable train/dev/test splits by hash
- keeps source provenance in `manifest.tsv`

## Output

`manifest.tsv` contains:

```text
source_name<TAB>split<TAB>fingerprint<TAB>source_text<TAB>target_text
```

The `awesome_*.txt` files contain:

```text
source_text ||| target_text
```

which matches the Awesome Align training format.

## Contributor workflow

1. Download public corpora under their official terms.
2. Convert each source into a simple local TSV with `ltc-convert-en-ja-public-source`.
3. Paste the emitted config fragments into your local `public_sources.json`.
4. Run `prepare_en_ja_finetune_data`.
5. Inspect `summary.json`.
6. Train or fine-tune Awesome Align on the resulting `awesome_train.txt`.
7. Evaluate with:
   - `ltc-eval-en-ja-quality`
   - `ltc-audit-en-ja-corpus`
   - `ltc-compare-en-ja-models`
