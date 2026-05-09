# Smoke Projects

Smoke projects are the smallest real-backend checks for supported language
pairs.

## Available smoke projects

- [de_en](de_en/README.md)
- [en_ja](en_ja/README.md)

Use a smoke project when you want to confirm that:

- the pair-specific runtime can be installed locally
- the alignment path runs end to end on tracked data or a small sample
- a refactor did not break the basic `count_function.py` flow

For deeper regression work, move from `smoke/` into `quality/`.
