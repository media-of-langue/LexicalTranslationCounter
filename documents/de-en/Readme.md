## de_en Notes

`de_en` currently uses:

- Awesome Align for sentence-level alignment
- spaCy for German tokenization/POS
- NLTK for English tokenization/POS
- GermaLemma for German normalization

## Preferred local workflow

Start with the smoke project:

- [projects/smoke/de_en/README.md](../../projects/smoke/de_en/README.md)

Then use the repository-wide guides when you need more context:

- [documents/How_to_build_and_run_from_source.md](../How_to_build_and_run_from_source.md)
- [documents/How_to_test.md](../How_to_test.md)
- [documents/The_dev_workflow.md](../The_dev_workflow.md)

## Awesome Align model resolution

`de_en` no longer requires a hard-coded `/root/src/model/...` path.

It now resolves its model in this order:

1. `LTC_AWESOME_ALIGN_MODEL_DE_EN`
2. `LTC_AWESOME_ALIGN_MODEL`
3. canonical repo registry: `models/de-en/awesome-align/production/`
4. legacy local path: `src/model/awesome_model_with_co/`
5. fallback: `bert-base-multilingual-cased`

If you want to pin a production model, register it with:

```bash
PYTHONPATH=src python3 -m ltc.cli.register_awesome_model \
  --pair de-en \
  --source /path/to/awesome_model_with_co \
  --copy-files
```

Then confirm the resolved state:

```bash
PYTHONPATH=src python3 -m ltc.cli.awesome_model_status --pair de-en
```

## German spaCy model

The default German morphological path uses `de_dep_news_trf`.

If you want a lighter local experiment, you can override the model name with
`LTC_DE_SPACY_MODEL`, for example:

```bash
LTC_DE_SPACY_MODEL=de_core_news_sm PYTHONPATH=src python3 -m ltc.cli.doctor --group morphological
```

This is a contributor convenience setting. It is not a guarantee that the
lighter model will match the quality of the default transformer-backed path.
