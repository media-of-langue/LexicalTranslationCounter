# Model Registry

This directory is the canonical local registry for large alignment model assets
that are not committed to Git.

## Layout

Awesome Align production models should be registered under:

```text
models/<pair>/awesome-align/production/
```

For example:

```text
models/en-ja/awesome-align/production/
```

That directory can contain either:

- the actual model files themselves, or
- a `MODEL_SPEC` file that points to a local directory or a Hugging Face model
  spec

Optional metadata can be stored in `MODEL_INFO.json`.

## Recommended workflow

Register a model with:

```bash
PYTHONPATH=src python3 -m ltc.cli.register_awesome_model \
  --pair en-ja \
  --source /path/to/model \
  --copy-files
```

Check the current resolution state with:

```bash
PYTHONPATH=src python3 -m ltc.cli.awesome_model_status --pair en-ja
```

The contents of `models/` are ignored by Git on purpose.
