---
name: "en-ja-quality-improvement"
description: "Use when continuing en_ja alignment, Japanese normalization, lexicalization staging, or phrase/word observation quality work in this repository. Focus on preserving current regression scores while improving pair quality and contributor workflows."
---

# en_ja Quality Improvement

This skill is a handoff guide for continuing `en_ja` quality work after the
repo-wide refactor PR is split out.

## Current baseline

- Default Japanese backend: `sudachi_a`
- Main quality suite:
  `PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --suite extended --fail-on-error`
- Recent validated state before handoff:
  - extended suite passing
  - sample pack 2 passing
  - sample pack 3 passing
- Observation/staging flow exists and should keep working:
  - `extract_en_ja_observations`
  - `aggregate_en_ja_staging`
  - `inspect_en_ja_staging`

## What to optimize for

- Do not regress the current curated `en_ja` suite just to improve one new
  example.
- Prefer changes that improve both quality and contributor visibility.
- Keep phrase-level evidence and word-level registration decisions separate.
- Minimize human review. Favor `ready`, `candidate`, and explicit `needs_review`
  buckets over ad hoc judgment.

## First commands to run

From the repository root:

```bash
python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --suite extended --fail-on-error
PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --cases projects/quality/en_ja/sample_pack_2.json --suite core --fail-on-error
PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --cases projects/quality/en_ja/sample_pack_3.json --suite core --fail-on-error
```

If you are changing a specific sentence or regression:

```bash
PYTHONPATH=src python3 -m ltc.cli.inspect_en_ja --case <case_name>
```

If you are changing phrase/component promotion logic:

```bash
PYTHONPATH=src python3 -m ltc.cli.extract_en_ja_observations --suite extended --output-dir /tmp/en-ja-observations
PYTHONPATH=src python3 -m ltc.cli.aggregate_en_ja_staging --input-dir /tmp/en-ja-observations --output-dir /tmp/en-ja-staging
PYTHONPATH=src python3 -m ltc.cli.inspect_en_ja_staging --input-dir /tmp/en-ja-staging --kind promotion-proposal
PYTHONPATH=src python3 -m ltc.cli.inspect_en_ja_staging --input-dir /tmp/en-ja-staging --kind promotion-followup
```

## Main code areas

- Alignment and postprocessing:
  `src/alignment/en_ja/__init__.py`
- Japanese backend selection:
  `src/ltc/japanese/backends.py`
- Japanese tokenization/POS shaping:
  `src/ltc/japanese/morphology.py`
- Japanese normalization:
  `src/ltc/japanese/normalization.py`
- Quality evaluation:
  `src/ltc/evaluation/en_ja_quality.py`
- Phrase/word observation and lexicalization staging:
  `src/ltc/observations/en_ja.py`
  `src/ltc/staging/en_ja.py`

## Preferred workflow

1. Reproduce the current failure or weak example with `evaluate` or `inspect`.
2. Decide whether the problem is mostly:
   - tokenizer / POS
   - normalization
   - alignment backend output
   - postprocessing / suppression
   - lexicalization / staging
3. Make the smallest change that fixes the root cause.
4. Re-run:
   - unit tests
   - extended suite
   - relevant sample pack
5. If phrase/component behavior changed, re-run observation extraction and
   staging inspection.

## Things to be careful about

- `that side -> そちら側` and `examples of construction -> 施工事例` are good
  examples of phrase-level evidence that should not be treated as naive
  word-level gold.
- A clean-looking new pair is not enough. Check whether it creates collateral
  noise elsewhere.
- Avoid pushing more generic verb noise such as `be/get/become/... -> なる`
  back into the final network.
- Keep contributor workflows updated when commands or paths change.

## Good next targets

- phrase-granularity improvements where the current word relation is too coarse
- better automatic handling for `candidate` promotion rows without inflating
  false positives
- backend/model comparisons when a quality problem clearly looks alignment-led

## Non-goals for this track

- Do not mix this work with repo-wide structural refactors unless necessary.
- Do not treat the local smoke fallback model as the production-quality target.
