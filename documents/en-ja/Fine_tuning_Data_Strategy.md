# en-ja Fine-tuning Data Strategy

This note records the current recommendation for `en_ja` alignment fine-tuning.

## Conclusion

For `en_ja` fine-tuning, do **not** use this repository's small tracked corpus
as the main training source.

Use public parallel corpora with clearer provenance as the primary source, and
use this repository's local suite only for regression checks and small-scale
manual inspection.

## Recommended priority

### 1. Main backbone: JParaCrawl

Use JParaCrawl as the main broad-coverage backbone.

Why:

- very large public English-Japanese parallel corpus
- built specifically for `en_ja`
- better fit than tiny local examples when the goal is robust alignment

Current caveat:

- the terms are research-oriented and not general commercial use
- it is web-mined data, so filtering is still important

### 2. High-trust clean supplement: ASPEC-JE

Use ASPEC-JE as a cleaner formal-domain supplement.

Why:

- strong provenance
- curated scientific-paper domain
- useful when we want more trustworthy sentence pairs than noisy web crawl data

Current caveat:

- domain is narrow
- scientific abstracts are not representative of colloquial `en_ja`

### 3. Colloquial supplement: JESC

Use JESC as a colloquial-domain supplement, but not as the only source.

Why:

- large English-Japanese subtitle corpus
- useful for spoken and informal language that ASPEC does not cover well

Current caveat:

- subtitle alignment is inherently noisier than formal parallel text
- sentence shortening, paraphrase, and subtitle timing effects can distort
  word-level alignment

### 4. Optional mined expansion: WikiMatrix / CCMatrix / OPUS sources

Use these only after the main pipeline is working and only with filtering.

Why:

- they can expand coverage
- they may help if we later want more lexical variety

Current caveat:

- they are mined corpora, not first-choice high-trust data for a first
  `en_ja` fine-tuned aligner
- source mixing can make debugging much harder

## Recommended first training mix

If we build a first public `en_ja` fine-tuned Awesome Align model, start with a
simple source-aware mixture instead of one huge unfiltered dump.

Suggested order:

1. JParaCrawl as the main volume source
2. ASPEC-JE as the clean precision-oriented supplement
3. JESC as a smaller colloquial supplement

The exact proportions should be tuned later, but the key idea is:

- let JParaCrawl provide coverage
- let ASPEC stabilize quality
- let JESC restore casual-language behavior

## Data preparation rules

Before training:

- deduplicate aggressively
- remove exact or near-duplicate sentence pairs across sources
- keep source provenance for every line
- apply basic length-ratio and empty-line filtering
- keep train/dev/test split boundaries stable by hashing, not by random reruns

Prefer a source-aware manifest such as:

```text
source_name<TAB>src_sentence ||| tgt_sentence
```

even if the final trainer consumes only:

```text
src_sentence ||| tgt_sentence
```

The source-aware manifest makes later debugging much easier.

## Evaluation policy

Do not treat this repository's current `projects/quality/en_ja/cases.json` as a
training set.

Use it as:

- a regression suite for contributors
- a quick precision-oriented sanity check

Also add a separate manually reviewed evaluation set from trusted public data.

Suggested target:

- 100 to 300 manually reviewed sentence pairs
- mixed across formal, colloquial, and web-general domains
- focused on content-word alignment quality, not only sentence-level adequacy

## Current local finding

As of 2026-05-03 in this repository:

- smoke baseline: 11/11 on the strict local suite
- official public Awesome Align `w/o --train_co`: 9/11
- official public Awesome Align `w/ --train_co`: 8/11

So the current bottleneck is not "we need any fine-tuned model".
It is "we need an `en_ja`-appropriate fine-tuned model trained on better data".

## Repository workflow

This repository now includes a first data-preparation workflow for that plan:

- [projects/training/en_ja/README.md](../../projects/training/en_ja/README.md)

It prepares a source-aware manifest plus Awesome Align `train/dev/test` files
from local copies of public corpora.

If a downloaded source is not already in the repository's canonical
`english<TAB>japanese` TSV shape, convert it first with:

```bash
PYTHONPATH=src python3 -m ltc.cli.convert_en_ja_public_source ...
```

## Training objective note

For the first `en_ja` fine-tuned Awesome Align attempt, start without
`--train_co`.

Reason:

- the Awesome Align authors note that `--train_co` can improve recall while
  reducing precision
- our current local `en_ja` checks are precision-sensitive

Once a precision-stable model exists, we can revisit recall-oriented settings.
