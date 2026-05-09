# en-ja Quality Checks

This project is the smallest contributor-facing workflow for improving `en_ja`
alignment quality without touching the full corpora.

## Goal

Run a tiny curated set of sentence pairs and verify the normalized content
relations that should appear, plus a few relations that must not appear.

The checks are intentionally small and opinionated. They are not meant to be a
benchmark. They are meant to make local heuristic work safe and repeatable.

The suite now mixes:

- small hand-curated sentence pairs
- a few tracked `src/test/data/corpus_en_ja.csv` rows whose stable relations are
  easy to review

The repository now treats `sudachi_a` as the preferred Japanese text backend.
`jumanpp` remains available as a legacy regression baseline, and
`fugashi_unidic` remains available as a MeCab-family comparison route.

If you want to improve the Japanese side itself, the main code now lives in:

- `src/ltc/japanese/backends.py`
- `src/ltc/japanese/morphology.py`
- `src/ltc/japanese/normalization.py`
- `src/alignment/en_ja/__init__.py`

A short contributor-oriented map is available at
`src/ltc/japanese/README.md`.

## Run

```bash
PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --fail-on-error
```

This runs the fast `core` suite by default.

To run the broader suite:

```bash
PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality \
  --suite extended \
  --fail-on-error
```

To run a second fresh sample pack of unseen tracked-corpus rows:

```bash
PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality \
  --cases projects/quality/en_ja/sample_pack_2.json \
  --suite core \
  --fail-on-error
```

To run a third fresh sample pack built from a different tracked-corpus slice:

```bash
PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality \
  --cases projects/quality/en_ja/sample_pack_3.json \
  --suite core \
  --fail-on-error
```

Or, if the package entry points are installed:

```bash
ltc-eval-en-ja-quality --fail-on-error
```

To compare Japanese text backends on the same suite, set `LTC_JA_TEXT_BACKEND`
before starting Python:

```bash
LTC_JA_TEXT_BACKEND=jumanpp PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --fail-on-error
LTC_JA_TEXT_BACKEND=fugashi_unidic PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --fail-on-error
LTC_JA_TEXT_BACKEND=sudachi_a PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --fail-on-error
```

Current supported values are:

- `sudachi_a`
- `sudachi_b`
- `sudachi_c`
- `fugashi_unidic` (MeCab route)
- `jumanpp` (legacy baseline)

At the moment:

- `core` contains 20 cases
- `extended` contains 48 cases total, including the core cases

## Inspect one case

The `core` suite output also prints the surface-level alignment result for each
case, so you can see not only the normalized pair check but also the actual
`source_surface -> target_surface` relations that survived postprocessing.

When one case fails or you want more detail, inspect it with intermediate alignment details:

```bash
PYTHONPATH=src python3 -m ltc.cli.inspect_en_ja --case copula_adjective
```

Or inspect a free-form pair:

```bash
PYTHONPATH=src python3 -m ltc.cli.inspect_en_ja \
  --source "I am happy." \
  --target "私は嬉しい。"
```

If you want a reusable artifact instead of one interactive inspect, extract
phrase-aware observations and lexicalization review decisions:

```bash
PYTHONPATH=src python3 -m ltc.cli.extract_en_ja_observations \
  --suite core \
  --format json \
  --output /tmp/en-ja-core-observations.json \
  --output-dir /tmp/en-ja-core-observations
```

This keeps three things separate:

- stable word-level relations that can stay in the main lexical network
- phrase candidates such as `game title -> ゲームタイトル`
- phrase observations that suggest component projections, but still need review
  before promotion, such as `examples of construction -> 施工事例`

The current extractor uses four conservative action labels:

- `register_word`: safe word-level relation
- `register_phrase`: stable phrase-level relation that already survived the main path
- `project_components_auto`: clean noun-compound decomposition such as
  `voice input -> 音声入力`
- `project_components_needs_review`: phrase evidence that looks reusable but is
  still semantically ambiguous, such as `examples of construction -> 施工事例`

When `--output-dir` is used, the extractor writes:

- `bundle.json`: the full bundle with all observations and summaries
- `documents.jsonl`: one observation document per case
- `phrase-network-candidates.jsonl`: phrase-level candidates such as
  `game title -> ゲームタイトル`
- `auto-component-word-candidates.jsonl`: auto-promotable component relations
  such as `voice -> 音声`, `input -> 入力`
- `review-queue.jsonl`: the small set of phrase-level cases that still need
  human review
- `phrase-network-staging.csv`: a spreadsheet-friendly staging table for
  multiword phrase candidates
- `auto-component-word-staging.csv`: a spreadsheet-friendly staging table for
  auto-promotable component word candidates
- `review-queue.csv`: a spreadsheet-friendly version of the remaining review
  queue

The raw `review-queue.jsonl` keeps every `project_components_needs_review`
decision. The staged `review-queue.csv` is smaller: it drops cases that are
already supported by the same auto-promotable phrase elsewhere in the suite.

## Review Procedure

The intended order is:

1. Run the quality suite first.

```bash
PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --suite extended --fail-on-error
```

2. Extract observation artifacts.

```bash
PYTHONPATH=src python3 -m ltc.cli.extract_en_ja_observations \
  --suite extended \
  --format json \
  --output /tmp/en-ja-extended-observations.json \
  --output-dir /tmp/en-ja-extended-observations
```

Use `core` for the fast daily loop. Use `extended` when you want the full
phrase/review picture, including cases like `examples of construction ->
施工事例`.

If you want the same observation/staging process on the fresh sample pack:

```bash
PYTHONPATH=src python3 -m ltc.cli.extract_en_ja_observations \
  --cases projects/quality/en_ja/sample_pack_2.json \
  --suite core \
  --format json \
  --output /tmp/en-ja-sample-pack-2.json \
  --output-dir /tmp/en-ja-sample-pack-2
```

3. Look at `auto-component-word-candidates.jsonl` first.
   These are the low-friction candidates. In the current design, this file is
   the place for automatic accumulation into a staging table that is still kept
   separate from the main count output.

   If you want the same information in a spreadsheet-friendly shape, open
   `auto-component-word-staging.csv`.

4. Look at `phrase-network-candidates.jsonl` next.
   These are stable phrase relations that already survived the main path, such
   as `voice input -> 音声入力` or `game title -> ゲームタイトル`.

   If you want a phrase staging view that is easier to sort and diff, open
   `phrase-network-staging.csv`.

5. Only then look at `review-queue.jsonl`.
   This should stay small. These are the semantically ambiguous cases like
   `examples of construction -> 施工事例`, where the repository can derive
   plausible components such as `construction -> 施工` and `example -> 事例`,
   but still prefers not to auto-promote them.

   If you need a shorter CSV-oriented checklist, use `review-queue.csv`.

In short:

- main lexical network: current `register_word`
- phrase staging table: `register_phrase`
- automatic component staging table: `project_components_auto`
- human review queue: `project_components_needs_review`

## Aggregate Staging Tables

If you want a separate relation-style artifact instead of raw extraction files,
aggregate one or more extracted bundles:

```bash
PYTHONPATH=src python3 -m ltc.cli.aggregate_en_ja_staging \
  --input-dir /tmp/en-ja-extended-observations \
  --output-dir /tmp/en-ja-staging-relations
```

This writes:

- `phrase-network-relations.csv`
- `auto-component-word-relations.csv`
- `ready-auto-component-word-relations.csv`
- `candidate-auto-component-word-relations.csv`
- `existing-word-network.csv`
- `promotion-ready-word-network.csv`
- `promotion-ready-diff.csv`
- `promotion-ready-proposals.csv`
- `promotion-followup.csv`
- `lexical-network-staging.csv`
- `review-queue.csv`
- `summary.json`

The intended reading order is:

1. `promotion-ready-word-network.csv`
2. `promotion-ready-diff.csv`
3. `promotion-ready-proposals.csv`
4. `promotion-followup.csv`
5. `ready-auto-component-word-relations.csv`
6. `candidate-auto-component-word-relations.csv`
7. `phrase-network-relations.csv`
8. `review-queue.csv`

This keeps phrase/component growth separate from the legacy word count output.
The auto-component table now also includes a lightweight `promotion_bucket`:

- `ready`: repeated or very high-confidence candidates
- `candidate`: useful staging candidates that are still low-support

This means the review queue can stay empty while the repository still avoids
blindly treating every auto component as ready for the main lexical network.

If you do not want to open the CSV files directly, inspect either an extracted
bundle directory or an aggregated staging directory from the terminal:

```bash
PYTHONPATH=src python3 -m ltc.cli.inspect_en_ja_staging \
  --input-dir /tmp/en-ja-staging-relations \
  --kind auto
```

Useful variants:

```bash
PYTHONPATH=src python3 -m ltc.cli.inspect_en_ja_staging \
  --input-dir /tmp/en-ja-extended-observations \
  --kind review

PYTHONPATH=src python3 -m ltc.cli.inspect_en_ja_staging \
  --input-dir /tmp/en-ja-staging-relations \
  --kind phrase \
  --query game \
  --min-occurrences 1

PYTHONPATH=src python3 -m ltc.cli.inspect_en_ja_staging \
  --input-dir /tmp/en-ja-staging-relations \
  --kind auto \
  --promotion-bucket ready

PYTHONPATH=src python3 -m ltc.cli.inspect_en_ja_staging \
  --input-dir /tmp/en-ja-staging-relations \
  --kind promotion

PYTHONPATH=src python3 -m ltc.cli.inspect_en_ja_staging \
  --input-dir /tmp/en-ja-staging-relations \
  --kind promotion-diff

PYTHONPATH=src python3 -m ltc.cli.inspect_en_ja_staging \
  --input-dir /tmp/en-ja-staging-relations \
  --kind promotion-proposal

PYTHONPATH=src python3 -m ltc.cli.inspect_en_ja_staging \
  --input-dir /tmp/en-ja-staging-relations \
  --kind promotion-followup
```

Recommended order:

1. `--kind promotion`
2. `--kind promotion-diff`
3. `--kind promotion-proposal`
4. `--kind promotion-followup`
5. `--kind auto --promotion-bucket ready`
6. `--kind auto --promotion-bucket candidate`
7. `--kind phrase`
8. `--kind review`

In practice, contributors can usually work in this order:

1. `promotion-proposal`
   These are `ready` component candidates that are also `novel` relative to the
   current word network, so they are the cleanest promotion suggestions.
2. `promotion-followup`
   These are `ready` candidates that overlap with the existing word network on
   either source or target and need a network-level decision, not a phrase-level
   rescue.
3. `review`
   This is the true leftover queue when the system still cannot even stage the
   candidate confidently.

## Compare two models on the same case

Once you have a pinned production model, compare it against the smoke model on
the same sentence pair:

```bash
PYTHONPATH=src python3 -m ltc.cli.awesome_model_status --pair en-ja

PYTHONPATH=src python3 -m ltc.cli.compare_en_ja_models \
  --case objective_sentence_core_relations \
  --left-model bert-base-multilingual-cased \
  --right-model models/en-ja/awesome-align/production \
  --left-label smoke \
  --right-label production
```

If you have not registered a canonical production model yet, do that first:

```bash
PYTHONPATH=src python3 -m ltc.cli.register_awesome_model \
  --pair en-ja \
  --source /path/to/model \
  --copy-files
```

This uses the same inspect path underneath and highlights:

- final normalized pair differences
- top target candidate differences for each source content token

You can also compare different alignment backends directly:

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

At the moment, the SimAlign path should be treated as experimental. The official
API usage is straightforward, but this repository still evaluates its output
through LTC's shared postprocessing rules, which were tuned around the Awesome
Align path.

The inspect output now includes per-group confidence summaries. In the current
`en_ja` path, very weak groups are filtered before they become final relations.
The default threshold is `0.2`, and you can override it locally with
`LTC_EN_JA_MIN_ALIGNMENT_CONFIDENCE`.

Some cases also disallow unexpected extra pairs. This is useful when a model
still satisfies the old required pairs but starts emitting new noisy relations.

It also shows the top target candidates for each source content token. This is
useful when deciding whether a problem belongs to:

- alignment itself: the wrong target token already has the top score
- postprocessing: the right candidate exists but the final grouping is wrong
- normalization/POS: the final surface pair looks reasonable, but normalization
  or POS projection is the part that distorts the result

## Focus

- The expected pairs are evaluated after normalization.
- This means the checks are closer to the repository's final relation tables
  than a raw surface-form comparison.
- Use this together with [projects/smoke/en_ja/README.md](../../smoke/en_ja/README.md):
  smoke tells you whether the real backend runs, quality tells you whether a
  local change preserved a few important behaviors, and inspect shows where a
  mismatch was introduced.

## Audit tracked corpus rows

If the curated suite still feels too small, audit a few tracked corpus rows
directly:

```bash
PYTHONPATH=src python3 -m ltc.cli.audit_en_ja_corpus \
  --row-id 2 \
  --row-id 4 \
  --row-id 10
```

Or, with installed entry points:

```bash
ltc-audit-en-ja-corpus --row-id 2 --row-id 4 --row-id 10
```

This is intentionally lighter than adding a new gold case. It helps contributors
look at a few real rows before deciding which relations are stable enough to
promote into the curated suite.

If you want to compare a smoke model and a production model across a wider
tracked-corpus slice, use:

```bash
PYTHONPATH=src python3 -m ltc.cli.compare_en_ja_corpus_models \
  --limit 100 \
  --only-different
```

If you want to compare the legacy `jumanpp` path and the new Sudachi-first path
on the same tracked-corpus slice, use:

```bash
PYTHONPATH=src python3 -m ltc.cli.compare_en_ja_corpus_backends \
  --left-backend jumanpp \
  --right-backend sudachi_a \
  --limit 100 \
  --only-different
```

For critical review work, prefer a reproducible sample instead of always taking
the first rows:

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

## Editing the cases

The curated cases live in:

`projects/quality/en_ja/cases.json`

Each case contains:

- `source`
- `target`
- `required_pairs`
- `forbidden_pairs`
- `notes`

Each pair is `[pos, source_normalized, target_normalized]`.
