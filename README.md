# Lexical Translation Counter

## The Repository

**Lexical Translation Counter** is a function that counts and writes down the facts **_"That word was translated into this word._**"

In other words, this function has the following inputs and outputs:

- **Input**：bilingual corpus and wordlist
- **Output**：Table that stores the number of times a word (language 1) is translated into a word (language 2)

This function was prepared to produce the material for "[Media of Langue](http://www.media-of-langue.org)," but this universal task is assumed to be used for various applications.

## Construction

”Lexical Translation Counter” works by calling the following three functions.

- **Alignment function**：Function to figure out which words correspond to which words in a translated sentence pair
- **Normalize function**：Functions to link multiple expressions and conjugations of a word to a single representative word
- **Morphological function(Option)**：Functions to split sentences into words and determine word class. This function is sometimes included in Alignment function.

The Alignment function exists for interlanguage (e.p. English-French), while the Normalize function and Morphological function exist for a single language (e.p. Japanese).
There is room for improvement in these functions at present, and we welcome contributors who can improve them together.

You can also easily create the data abot new languages or new pairs of languages that have not yet been introduced to ”Lexical Translation Counter” by duplicating and modifying these functions.
This means that you can introduce new languages or new pairs of languages to "Media of Langue."

## Media of Langue

![MoL_meaning_2d](https://github.com/media-of-langue/LexicalTranslationCounter/assets/44542920/92a7e06c-0ced-44c3-923b-e3149aa4f827)

Media of Langue is a new dictionary that draws about “meaning" at the interface of multiple languages, from the accumulation of "this word was translated into that word" only.
To view Media of Langue, go to http://www.media-of-langue.org.

## Contributing

- Update or launch "alignment function"

  - This function can be created for two languages for which "Normalize function" and "Morphological function" have already been created. Counting up the output of this function completes the material that make up the Media of Langue diagram. We hope that in the future this function will be created for all languages for which there are enough corpora in the world.

- Update or launch "Normalize function" or "Morphological function"

  - These functions exist for each language, so improving them involves improving the behavior across all the language-pair the language involves. We are willing to use existing tools.

- Review PullRequest

  - We would appreciate a review of the accuracy of the proposed improvements to "Lexical Translation Counter". Since the managers are familiar to few languages, this help would be a great contribution to the evaluation of their accuracy.

- Suggestions for databases

  - You can suggest a more appropriate bilingual corpus for a given language pair, or a more appropriate word list for a given language or part of speech.

- Criticism, critique, and advice on projects
  - Each part of Media of Langue contains multiple non-trivial judgments about language, translation, meaning, and perception. We believe that all of them should be open to ongoing criticism.

If you are interested in fixing issues and contributing directly to the code base, please see the following:

- [How to build and run from source](documents/How_to_build_and_run_from_source.md)
- [The development workflow](documents/The_dev_workflow.md)
- [Add language pair](documents/Add_language_pair.md)
- [Add language](documents/Add_language.md)
- [Update or Add Functions](documents/Update_or_Add_functions.md)
- [Update or Add Database](documents/Update_or_Add_data.md)
- [How to test](documents/How_to_test.md)
- [File reference](documents/File_reference.md)
- [Architecture and Refactor Plan](documents/Architecture_and_Refactor_Plan.md)
- [Architecture and Refactor Plan (Japanese)](documents/Architecture_and_Refactor_Plan_ja.md)
- [Projects overview](projects/README.md)
- [Smoke projects](projects/smoke/README.md)
- [de-en smoke project](projects/smoke/de_en/README.md)
- [en-ja smoke project](projects/smoke/en_ja/README.md)
- [en-ja quality checks](projects/quality/en_ja/README.md)

## Feedback

Please feel free to contact us if you have any inquiries.

media.of.langue@gmail.com

## Development Container

You can easily prepare an environment for development using Docker.
Of course, it can be executed in any environment, including local, by following the appropriate procedures.

See ”How to build and run from source” in the documents directory for details.

## Development And Testing Notes

This repository now supports a local-first workflow. Start with unit tests,
pair-specific smoke projects, and the `documents/` guides. Use Docker only when
you need the full corpus images.

Current reference pairs for the ongoing refactor are `de_en` and `en_ja`.
Treat those two as the best examples of the intended contributor workflow. Some
other language pairs still use more legacy runtime assumptions.

This repository does not use Poetry, mise, or the Media of Langue DB toolchain.
Start with the local Python runtime for small checks, and use Docker only when
you need the full corpus data images.

- Build/run: [How to build and run from source](documents/How_to_build_and_run_from_source.md)
- Contributor workflow: [The development workflow](documents/The_dev_workflow.md)
- Tests: [How to test](documents/How_to_test.md)
- Projects overview: [projects/README.md](projects/README.md)
- Lightweight tests: `python3 -m unittest discover -s tests`
- Environment check: `PYTHONPATH=src python3 -m ltc.cli.doctor --group normalizer`
- de-en smoke run: [projects/smoke/de_en/README.md](projects/smoke/de_en/README.md)
- en-ja smoke run: [projects/smoke/en_ja/README.md](projects/smoke/en_ja/README.md)
- Curated en-ja quality checks: [projects/quality/en_ja/README.md](projects/quality/en_ja/README.md)
- Pair extras for local installs: `python3 -m pip install -e '.[de-en]'` or `python3 -m pip install -e '.[en-ja]'`
- Broader en-ja regression suite: `PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --suite extended --fail-on-error`
- Fresh en-ja sample packs on unseen tracked-corpus rows:
  `PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --cases projects/quality/en_ja/sample_pack_2.json --suite core --fail-on-error`
  `PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --cases projects/quality/en_ja/sample_pack_3.json --suite core --fail-on-error`
- Default Japanese text backend: `sudachi_a` via `LTC_JA_TEXT_BACKEND`
- Japanese text processing code now lives in `src/ltc/japanese/` and the legacy `src/morphological/ja_morphological.py` / `src/normalizer/ja_normalizer.py` files are compatibility wrappers
- en-ja fine-tuning data strategy: [documents/en-ja/Fine_tuning_Data_Strategy.md](documents/en-ja/Fine_tuning_Data_Strategy.md)
- en-ja fine-tuning data prep workflow: [projects/training/en_ja/README.md](projects/training/en_ja/README.md)
- Convert a raw public en-ja source into canonical TSV: `PYTHONPATH=src python3 -m ltc.cli.convert_en_ja_public_source paired-tsv --source-name jparacrawl --input-path /path/to/input.tsv --output-path /path/to/jparacrawl.tsv`
- Inspect one en-ja pair: `PYTHONPATH=src python3 -m ltc.cli.inspect_en_ja --case copula_adjective`
- Extract en-ja observation/review artifacts and staging tables: `PYTHONPATH=src python3 -m ltc.cli.extract_en_ja_observations --suite core --format json --output /tmp/en-ja-core-observations.json --output-dir /tmp/en-ja-core-observations`
- Aggregate extracted en-ja staging bundles into separate relation tables: `PYTHONPATH=src python3 -m ltc.cli.aggregate_en_ja_staging --input-dir /tmp/en-ja-core-observations --output-dir /tmp/en-ja-staging-relations`
- Inspect en-ja promotion-ready candidates without opening the CSV files directly: `PYTHONPATH=src python3 -m ltc.cli.inspect_en_ja_staging --input-dir /tmp/en-ja-staging-relations --kind promotion`
- Inspect how promotion-ready candidates differ from the current word network: `PYTHONPATH=src python3 -m ltc.cli.inspect_en_ja_staging --input-dir /tmp/en-ja-staging-relations --kind promotion-diff`
- Inspect only the clean novel promotion suggestions: `PYTHONPATH=src python3 -m ltc.cli.inspect_en_ja_staging --input-dir /tmp/en-ja-staging-relations --kind promotion-proposal`
- Audit a few tracked en-ja corpus rows: `PYTHONPATH=src python3 -m ltc.cli.audit_en_ja_corpus --row-id 2 --row-id 4 --row-id 10`
- Compare smoke vs production on tracked en-ja rows: `PYTHONPATH=src python3 -m ltc.cli.compare_en_ja_corpus_models --limit 100 --only-different`
- Compare Juman vs Sudachi on a reproducible sample: `PYTHONPATH=src python3 -m ltc.cli.compare_en_ja_corpus_backends --left-backend jumanpp --right-backend sudachi_a --selection random --seed 17 --limit 40 --only-different`
- Register a canonical Awesome Align model: `PYTHONPATH=src python3 -m ltc.cli.register_awesome_model --pair en-ja --source /path/to/model --copy-files`
- Check the current Awesome Align resolution: `PYTHONPATH=src python3 -m ltc.cli.awesome_model_status --pair en-ja`
- Production guard for aligner model selection: `LTC_REQUIRE_PRODUCTION_MODEL=1`

Keep this repository open-source friendly. Do not add Media of Langue private DB infrastructure, deployment runbooks, production credentials, or internal data-loading settings here.

## Acknowledgements

We use the following libraries and datasets. We gratefully respect and acknowledge these projects.

- [Used NLP library List](documents/Acknowledgements/Used_nlp_library_list.md)
- [Used Data-set List](documents/Acknowledgements/Used_dataset_list.md)
