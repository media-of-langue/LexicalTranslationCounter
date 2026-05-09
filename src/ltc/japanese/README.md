# Japanese Text Processing Layout

The repository now treats `sudachi_a` as the preferred Japanese text backend.
The Japanese processing code is organized under `src/ltc/japanese/` so
contributors can improve tokenization, normalization, and backend selection in
one place.

## Files

- `backends.py`
  - backend names, aliases, default selection, and runtime checks
- `morphology.py`
  - backend-specific raw morpheme extraction
  - backend compatibility rules
  - token / POS projection used by `en_ja`
- `normalization.py`
  - backend-aware lemma normalization
  - contextless fragment recovery and exception handling

## Default path

By default, the runtime resolves:

- `LTC_JA_TEXT_BACKEND=sudachi_a`

Other supported values are:

- `sudachi_b`
- `sudachi_c`
- `fugashi_unidic`
- `jumanpp`

`src/morphological/ja_morphological.py` and
`src/normalizer/ja_normalizer.py` still exist as compatibility wrappers for the
older repository layout, but new work should usually go into
`src/ltc/japanese/`.

## Suggested workflow

1. Run the curated quality checks:
   `PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --fail-on-error`
2. Inspect one failing case:
   `PYTHONPATH=src python3 -m ltc.cli.inspect_en_ja --case <case-name>`
3. Edit `morphology.py`, `normalization.py`, or `src/alignment/en_ja/__init__.py`
4. Re-run:
   - `python3 -m unittest discover -s tests`
   - `PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --suite extended --fail-on-error`

## Rule-of-thumb

- If the wrong target token already has the best alignment score, start with the
  aligner or postprocessing.
- If the surface pair looks right but the normalized pair is wrong, start with
  `normalization.py`.
- If the token boundaries or POS tags are off, start with `morphology.py`.
