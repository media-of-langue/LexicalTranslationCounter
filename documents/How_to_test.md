# How to test

## prepare test data
Place the following test data in /root/src/test/data/. For the contents of the file, refer to [File Reference](File_Reference.md).

The number of lines of corpus test data should not exceed 100 lines

- corpus_{la1}_{la2}.csv
- wordlist_{la}_{pos_tag}.csv

`src/test/data/` contains the tracked fixtures. Test outputs are generated under `src/test/result_of_test/` and are intentionally not tracked.

## alignment function
The result of aligning the corpus of test data is output.

```
cd /root/src/test/
python3 alignment_test.py {la1} {la2}
```
The results are output to /root/src/test/result_of_test/ in the following format
```
sentece_la1:Resumption of the session
sentece_la2:Reprise de la session
new align
word_A - word_a word_B - word_b

ex:
sentece_la1:Resumption of the session
sentece_la2:Reprise de la session
new align
Resumption - Reprise  session - session  
```

You can also test for a single sentence pair.
Please specify the sentences for sentence_la1 and sentence_la2 in the code.

```
cd /root/src/test/
python3 alignment_test_single.py {la1} {la2}
```
The results are output to the console in the following format.
```
sentece_la1:Resumption of the session
sentece_la2:Reprise de la session
new align
word_A - word_a word_B - word_b

ex:
sentece_la1:Resumption of the session
sentece_la2:Reprise de la session
new align
Resumption - Reprise  session - session  
```

## normalize function
It returns the result of normalizing a word based on its part-of-speech.

By default, the test mode is set to True and the word id is not returned.
```
cd /root/src/test/
python3 normalizer_test.py {la}
```
```
ex)
python3 normalizer_test.py en
```

The results are output to /root/src/test/result_of_test/ for each part-of-speech in the following format.
However, this file will only output the forms and words in wordlist that change.
```
word_origin->normalized_word

ex)
plays->play
```

You can also test with respect to a single word.
```
cd /root/src/test/
python3 normalizer_test_single.py {la} {word}
```
```
ex)
python3 normalizer_test_single.py en plays
```


## morphological function

Run morphological_test.py in '/root/src/test/'specifying two languages, including the newly created language.In principle, the other language should be English, and the test can be run with the other language only if there is no test corpus available for English.

Morphological analysis results of the sentences in the corpus are output.

```
cd /root/src/test/
python3 morphological_test.py {la1} {la2}
```

```
ex) python3 morphological_test.py en fr
```

The results are output to /root/src/test/result_of_test/ in the following format.
```
word_la1:pos_tag_la1 word_la1:pos_tag_la1 word_la1:pos_tag_la1 word_la1:pos_tag_la1
word_la2:pos_tag_la2 word_la2:pos_tag_la2 word_la2:pos_tag_la2 word_la2:pos_tag_la2

ex)
Resumption:n of:N/A the:N/A session:n 
Reprise:n de:N/A la:N/A session:n 
```

A single sentence can also be tested.
Sentences should be specified by directly rewriting the sentences in the code.
```
cd /root/src/test/
python3 morphological_test_single.py {la}
```

```
ex) python3 morphological_test_single.py en
```

The results are displayed in the console in the following format.
```
word_la:pos_tag_la word_la:pos_tag_la word_la:pos_tag_la word_la:pos_tag_la

ex)
Resumption:n of:N/A the:N/A session:n 
```

## en-ja quality checks

For contributor-friendly `en_ja` quality work, use the curated local checks
instead of manually editing the old test scripts.

```
PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality --fail-on-error
```

This runs the fast `core` suite.

For a broader local regression pass, run:

```
PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality \
  --suite extended \
  --fail-on-error
```

This runs a small gold set stored in:

`projects/quality/en_ja/cases.json`

There is also a second fresh sample pack for checking a different slice of
tracked-corpus sentences:

`projects/quality/en_ja/sample_pack_2.json`

Run it with:

```bash
PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality \
  --cases projects/quality/en_ja/sample_pack_2.json \
  --suite core \
  --fail-on-error
```

There is also a third fresh pack built from another tracked-corpus slice:

`projects/quality/en_ja/sample_pack_3.json`

```bash
PYTHONPATH=src python3 -m ltc.cli.evaluate_en_ja_quality \
  --cases projects/quality/en_ja/sample_pack_3.json \
  --suite core \
  --fail-on-error
```

The checks compare normalized content pairs, so they are closer to the final
relation tables than a raw surface-form diff.

The suite mixes small hand-curated pairs and tracked corpus rows whose stable
relations are easy to review.

The `core` suite also prints the surviving surface-level alignment results, so
the quality command itself shows both the normalized relation check and the
actual `source_surface -> target_surface` alignments that remained.

The current default Japanese text backend for this workflow is `sudachi_a`.
Use `LTC_JA_TEXT_BACKEND=jumanpp` only when you explicitly want the legacy
baseline for comparison.

When one case fails, inspect it with:

```
PYTHONPATH=src python3 -m ltc.cli.inspect_en_ja --case {case_name}
```

This prints:

- source tokens and POS tags
- target tokens and POS tags
- ignored indices
- merged alignment groups
- postprocessed groups
- top target candidates for each source content token
- final surface and normalized pairs

For the current `en_ja` reference path, inspect also shows simple confidence
summaries (`best` / `avg`) for each surviving group. Very weak groups are
filtered before they become final relations. The default threshold is `0.2`
and can be overridden with `LTC_EN_JA_MIN_ALIGNMENT_CONFIDENCE`.

Some cases also disallow unexpected extra pairs. This helps catch regressions
where a model still keeps the old required relation but starts emitting new
noisy pairs.

This is meant to support component-level triage:

- if the wrong target token is already the top candidate, the alignment model
  is the main suspect
- if the candidate list looks reasonable but the final pair is wrong, inspect
  postprocessing and grouping
- if the final surface pair is reasonable but the normalized pair is odd,
  inspect POS tagging and normalization

If you want to compare a smoke model and a pinned production model on exactly
the same case, use:

```
PYTHONPATH=src python3 -m ltc.cli.awesome_model_status --pair en-ja

PYTHONPATH=src python3 -m ltc.cli.compare_en_ja_models \
  --case objective_sentence_core_relations \
  --left-model bert-base-multilingual-cased \
  --right-model models/en-ja/awesome-align/production \
  --left-label smoke \
  --right-label production
```

This is useful before deciding whether to change heuristics or switch the
alignment backend/model itself.

If you have not registered a canonical production model yet, do that first:

```
PYTHONPATH=src python3 -m ltc.cli.register_awesome_model \
  --pair en-ja \
  --source /path/to/model \
  --copy-files
```

You can also compare backend choices directly. For example:

```
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

Treat the current SimAlign route as an experimental comparison backend. The
official SimAlign API is simple, but the downstream filtering here is still LTC
logic shared with the Awesome-based path.

If the curated suite still feels too small, audit a few tracked corpus rows
directly:

```
PYTHONPATH=src python3 -m ltc.cli.audit_en_ja_corpus \
  --row-id 2 \
  --row-id 4 \
  --row-id 10
```

For a broader smoke-vs-production comparison across the tracked corpus:

```
PYTHONPATH=src python3 -m ltc.cli.compare_en_ja_corpus_models \
  --limit 100 \
  --only-different
```

To compare the legacy `jumanpp` path against the Sudachi-first path on the same
tracked-corpus rows, use:

```bash
PYTHONPATH=src python3 -m ltc.cli.compare_en_ja_corpus_backends \
  --left-backend jumanpp \
  --right-backend sudachi_a \
  --limit 100 \
  --only-different
```

For less biased review, switch the tracked-corpus check from `head` rows to a
reproducible random or stratified sample:

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

## en-ja public fine-tuning data preparation

If you are preparing public `en_ja` corpora for alignment fine-tuning, first
convert raw source files into the repository's canonical TSV shape:

```bash
PYTHONPATH=src python3 -m ltc.cli.convert_en_ja_public_source \
  paired-tsv \
  --source-name jparacrawl \
  --input-path /path/to/input.tsv \
  --output-path /path/to/jparacrawl_en_ja.tsv
```

Then build the source-aware Awesome Align training files:

```bash
PYTHONPATH=src python3 -m ltc.cli.prepare_en_ja_finetune_data \
  --config projects/training/en_ja/public_sources.example.json \
  --output-dir src/data/training/en_ja_public_mix
```

## Check the outputs
you can check the result of test data on console or outputs file in /root/src/result_of_test/
And checke the acccuracy of the code.
