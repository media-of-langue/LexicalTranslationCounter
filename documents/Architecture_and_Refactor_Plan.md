# Architecture and Refactor Plan

[Japanese version](Architecture_and_Refactor_Plan_ja.md)

## Purpose

This document describes the target repository structure and system design for
Lexical Translation Counter.

The goal is not to discard the current repository, but to preserve its useful
core while making the codebase easier to understand, extend, test, and
contribute to.

The current conceptual split is still good:

- alignment
- normalization
- morphological analysis

The refactor should preserve that split while redesigning the boundaries and
responsibilities around it.

## Main Problems in the Current Structure

- The counting script mixes CLI handling, corpus IO, resume logic, wordlist
  updates, alignment execution, aggregation, and output writing.
- Language-specific and pair-specific behavior is encoded as Python module
  names, which makes extension harder than necessary.
- Many alignment implementations duplicate large amounts of logic.
- Tests are useful for manual inspection, but they are not yet organized as a
  contributor-friendly automated test suite.
- Wordlist maintenance and relation counting are coupled together, which hurts
  reproducibility and reviewability.
- Input and output formats are not strongly typed or centrally defined.

## Refactor Goals

- Make the system easier to understand from the file tree alone.
- Make the pipeline explicit and modular.
- Let new language support default to configuration rather than code copying.
- Support multiple alignment backends cleanly.
- Separate lightweight contributor tests from heavyweight model-based runs.
- Preserve current behavior during migration whenever possible.

## Design Principles

- Keep domain concepts explicit.
- Prefer configuration over naming conventions.
- Use shared interfaces for interchangeable backends.
- Separate pure data transformations from side-effecting IO.
- Keep the default contributor path small and local.
- Treat counting, lexicon building, and evaluation as separate workflows.

## Important Correction: Migration Shape vs Clean-Slate Shape

The current `src/ltc/` package structure is a good migration scaffold, but it
is not exactly the same thing as the ideal architecture if this project were
designed from scratch today.

If started from scratch, the repository should be organized around:

- stable domain artifacts
- explicit workflow stages
- pluggable language and alignment backends
- contributor-editable configuration
- runnable contributor-facing project templates

More importantly, the core task should not be modeled as:

- "count from a corpus using pre-existing wordlists"

It should instead be modeled as:

- "extract sentence-linked bilingual translation observations from a corpus,
  then aggregate them into relation tables and optional lexicon tables"

That is the largest architectural correction.

## Clean-Slate Domain Model

If the project were designed from scratch, the main first-class concepts should
be:

- `CorpusRow`
- `SentenceAnalysis`
- `AlignmentEdge`
- `TranslationObservation`
- `RelationAggregate`
- `LexiconEntry`

The key missing concept in the legacy design is `TranslationObservation`.

A `TranslationObservation` is one piece of evidence that a normalized source
expression and a normalized target expression were linked in one sentence pair.
It should carry provenance such as:

- corpus row id
- source and target token spans
- source and target normalized forms
- source and target POS
- aligner/backend name
- confidence or score when available

Once this concept exists, relation tables become a derived aggregation over
observations rather than the primary artifact.

## Clean-Slate Target Top-Level Layout

If the project were started fresh for OSS contribution and multilingual
extension, the repository would more naturally move toward the following
layout:

```text
.
|-- README.md
|-- pyproject.toml
|-- configs/
|   |-- languages/
|   |-- pairs/
|   `-- workflows/
|-- projects/
|   |-- minimal/
|   |-- smoke/
|   `-- pair_templates/
|-- src/
|   `-- ltc/
|       |-- __init__.py
|       |-- cli/
|       |   |-- analyze.py
|       |   |-- align.py
|       |   |-- extract.py
|       |   |-- aggregate.py
|       |   |-- inspect.py
|       |   |-- evaluate.py
|       |   `-- wordlists.py
|       |-- domain/
|       |   |-- corpus.py
|       |   |-- analysis.py
|       |   |-- alignments.py
|       |   |-- observations.py
|       |   |-- lexicon.py
|       |   `-- relations.py
|       |-- artifacts/
|       |   |-- schemas.py
|       |   |-- readers.py
|       |   `-- writers.py
|       |-- workflows/
|       |   |-- analyze.py
|       |   |-- align.py
|       |   |-- extract_observations.py
|       |   |-- aggregate_relations.py
|       |   `-- checkpoints.py
|       |-- backends/
|       |   |-- alignment/
|       |   |   |-- base.py
|       |   |   |-- awesome_align.py
|       |   |   |-- binary_align.py
|       |   |   `-- fast_align.py
|       |   `-- linguistic/
|       |       |-- base.py
|       |       |-- stanza.py
|       |       |-- spacy.py
|       |       `-- jumanpp.py
|       |-- rules/
|       |   |-- languages/
|       |   `-- pairs/
|       |-- registry/
|       |   |-- languages.py
|       |   `-- language_pairs.py
|       `-- evaluation/
|           |-- smoke.py
|           `-- metrics.py
|-- tests/
|   |-- unit/
|   |-- smoke/
|   |-- integration/
|   `-- fixtures/
`-- documents/
```

This should be treated as the end-state design direction.

The currently introduced `src/ltc/` package should be understood as a migration
path toward this model, not as the final perfect tree.

## Migration Structure vs End-State Structure

During refactoring, it is still reasonable to keep some simpler interim
subtrees such as:

- `src/ltc/io/`
- `src/ltc/pipeline/`
- `src/ltc/config/`

Those are practical stepping stones.

However, the end-state should move toward:

- `domain` for the meaning of the data
- `artifacts` for serialization formats
- `workflows` for pipeline orchestration
- `rules` for language-specific and pair-specific heuristics
- repo-root `configs/` for contributor-edited metadata
- repo-root `projects/` for runnable, documented contributor entry points

## Responsibilities by Directory

### `src/ltc/domain/`

Defines the canonical data structures used throughout the project.

Examples:

- `CorpusRow`
- `SentenceAnalysis`
- `AlignmentEdge`
- `TranslationObservation`
- `RelationAggregate`
- `LexiconEntry`

This layer should have as little project-specific behavior as possible.

### `src/ltc/artifacts/`

Owns reading and writing data.

Examples:

- reading and writing corpus shards
- reading and writing observation datasets
- exporting relation tables
- exporting lexicon tables
- loading and saving checkpoints

This layer should know file formats and schema versions, but not linguistic
decisions.

### `src/ltc/workflows/`

Owns end-to-end workflows.

Examples:

- analyze corpus rows
- run aligners
- extract translation observations
- aggregate relations
- resume from checkpoints

This layer coordinates work. It should not contain backend-specific
implementations.

### `src/ltc/backends/`

Owns pluggable implementations.

This should include:

- alignment backends
- tokenization and POS backends
- lemmatization or normalization helpers

The pipeline should depend on backend interfaces, not on concrete modules.

### `configs/`

Owns per-language and per-language-pair configuration.

Examples:

- default linguistic backend for `ja`
- default aligner for `en-ja`
- part-of-speech filtering policy
- backend-specific options

This is the key step that turns "adding a new language" from "copy and modify a
Python file" into "add configuration and only write code when the defaults are
not enough".

Keeping this outside the Python package makes it easier for contributors to
review and edit support metadata without understanding package internals.

### `src/ltc/registry/`

Provides validated access to available languages, pairs, and backend choices.

This layer should answer questions such as:

- Is this language supported?
- Which backend is the default for this pair?
- Which config file should be loaded?

### `src/ltc/rules/`

Owns language-specific and pair-specific logic that is too custom to encode as
simple declarative configuration.

Examples:

- multiword merge rules
- auxiliary and copula filtering
- script-specific normalization exceptions
- pair-specific post-alignment cleanup

### `projects/`

Owns runnable templates for contributors.

Examples:

- minimal end-to-end sample runs
- smoke-test projects for one language pair
- pair templates showing the files needed to add support

This idea is strongly inspired by spaCy Projects, which separates reusable
package code from reproducible workflow definitions, assets, dependencies, and
outputs.

## Recommended Pipeline Shape

The main workflow should become a sequence of explicit stages:

1. Read a corpus row.
2. Analyze both sentences into tokens, POS tags, lemmas, and normalized forms.
3. Run an aligner backend on the analyzed sentences.
4. Convert raw alignment output into canonical alignment edges.
5. Apply language and pair rules.
6. Emit `TranslationObservation` records.
7. Aggregate observations into relation tables.
8. Optionally derive or update lexicon tables.
9. Save outputs and checkpoints.

This makes the system easier to debug because each step has a concrete input and
output type.

It also lets contributors inspect intermediate artifacts instead of only final
CSV tables.

From an OSS usability perspective, the important point is that a contributor
should be able to run one named small project immediately, without understanding
the whole repository first.

## Backend Interfaces

The project should adopt a small number of stable interfaces.

Example direction:

```python
class LinguisticBackend(Protocol):
    def analyze(self, sentence: str, language: str) -> AnalyzedSentence: ...


class AlignmentBackend(Protocol):
    def align(
        self,
        source: AnalyzedSentence,
        target: AnalyzedSentence,
        pair_config: LanguagePairConfig,
    ) -> list[AlignmentEdge]: ...
```

Important point:

- the workflow should not know whether the backend is Awesome Align,
  BinaryAlign, FastAlign, or something else
- the workflow should only know the canonical output type

The same principle applies to linguistic analysis.

The workflow should not know whether the analysis came from:

- Juman++
- Stanza
- spaCy
- another language-specific implementation

It should only know the canonical analyzed sentence shape.

## Language and Pair Configuration

A new language should ideally require only configuration when it can use an
existing backend.

Example `configs/languages/ja.yaml`:

```yaml
code: ja
linguistic_backend: jumanpp
content_pos:
  - NOUN
  - VERB
  - ADJ
  - ADV
normalization:
  use_lemma: true
  exception_table: normalize_data/ja/
```

Example `configs/pairs/en-ja.yaml`:

```yaml
pair: en-ja
alignment_backend: awesome_align
source_language: en
target_language: ja
postprocess:
  ignore_copula_support: true
  merge_multiword_content_tokens: true
```

This is much easier to review than a large copied Python module.

## Lexicon and Wordlist Design

If the project were designed from scratch, lexicon tables would be derived
artifacts or curated overlays, not required prerequisites for the main
pipeline.

That means the canonical flow should be:

- corpus
- analysis
- alignments
- translation observations
- relation aggregation
- optional lexicon export

Instead of:

- corpus
- pre-existing wordlists
- counting

This is a significant architectural change from the legacy design.

Why this is better:

- new language onboarding is much lighter
- contributors do not need to prepare large wordlists before they can test
- observation extraction is reproducible from the corpus and backend choices
- lexicon curation can happen as a separate, reviewable workflow

In practice, the refactor may still preserve legacy wordlist support for
compatibility. But it should be treated as a compatibility layer, not as the
ideal center of the system.

## Relation Counting Should Be Separate from Wordlist Building

The repository currently treats missing normalized words as something that may
be added during counting.

That should be split into two workflows:

- build or propose wordlist updates
- count relations against an accepted wordlist

This separation improves:

- reproducibility
- reviewability
- debugging
- contributor confidence

## Recommended Artifact Strategy

The project should preserve intermediate artifacts as first-class outputs.

Recommended artifacts:

- analyzed corpus rows
- alignment edges
- translation observations
- aggregated relation tables
- optional lexicon tables

The final public or downstream outputs can still include CSV for compatibility.
However, intermediate artifacts should use a more structured format such as:

- JSONL for easy inspection
- Parquet when scale matters

The exact file format is less important than having stable schemas and explicit
versioning.

This is close in spirit to Hugging Face Datasets, which treats processed data as
saveable and reloadable dataset artifacts rather than one-off temporary script
outputs.

## Test Layout

Tests should move out of `src/test/` and into a standard `tests/` tree.

Recommended split:

- `tests/unit/`
- `tests/smoke/`
- `tests/integration/`
- `tests/fixtures/`

### `tests/unit/`

Pure tests for:

- normalization helpers
- aggregation logic
- checkpoint behavior
- schema conversion

No model downloads. No heavy dependencies.

### `tests/smoke/`

Small contributor-facing tests.

These should run quickly on a fresh clone and prove that:

- the package imports
- a small pair configuration works
- a tiny corpus can flow through the pipeline
- observation extraction works end to end

### `tests/integration/`

Tests that require actual backend installations and model assets.

These should be opt-in or separately marked.

## Migration Strategy

The refactor should be staged.

### Phase 1: Introduce New Boundaries

- add the new package layout
- define schemas and interfaces
- wrap existing code through adapters
- do not change behavior yet

### Phase 2: Move Shared Logic

- extract shared alignment post-processing
- extract shared IO and checkpoint logic
- move the current counting script into workflow modules

### Phase 3: Port One Reference Pair

- choose one language pair as the first fully migrated path
- compare old and new outputs
- stabilize the new interfaces
- introduce `TranslationObservation` as an explicit artifact

At the current stage, `en_ja` should be treated as that reference pair.
Before broadening the rollout to more major languages, improve `en_ja`
alignment quality first. That quality work may reveal better boundaries between
backend logic, heuristics, observations, and evaluation, so Phase 4 should stay
blocked until that learning is reflected in the structure.

### Phase 4: Port Remaining Pairs

- migrate pair by pair
- keep legacy modules until each migrated path is verified

### Phase 5: Remove Legacy Structure

- deprecate direct imports from legacy modules
- rewrite contributor docs to match the new flow

## Revised Practical Direction

The current package refactor is still useful and should be kept.

But the long-term design direction should now be understood as:

- move toward artifact-driven workflows
- make observations first-class
- make lexicon generation downstream rather than prerequisite
- keep backend choice pluggable
- keep language and pair support mostly config-driven

That is closer to how this system would likely be designed if it were started
today as a multilingual OSS project.
