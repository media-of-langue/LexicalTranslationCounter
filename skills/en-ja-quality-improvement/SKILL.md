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

## Interaction protocol

When working with a user on `en_ja` quality, prefer a JSON-first loop that
keeps the reasoning auditable and makes it easy for a new user to react without
knowing the codebase.

Use the following stages.

### Stage 1: baseline packet

Before making a risky quality judgment, return a short JSON packet plus a brief
human summary.

Use this shape:

```json
{
  "stage": "baseline",
  "focus": "one short sentence about the current target",
  "baseline_checks": {
    "unit_tests": "pass|fail|not-run",
    "extended_suite": "pass|fail|not-run",
    "sample_pack_2": "pass|fail|not-run",
    "sample_pack_3": "pass|fail|not-run"
  },
  "target_cases": [
    {
      "case_name": "case or row id",
      "reason": "why this case is being inspected"
    }
  ],
  "suspected_layers": [
    "tokenizer_pos|normalization|alignment|postprocessing|lexicalization"
  ],
  "next_commands": [
    "exact command 1",
    "exact command 2"
  ]
}
```

### Stage 2: review packet

After inspecting one or more cases, return a machine-readable review packet so
the user can comment on the semantic judgment directly.

Use this shape:

```json
{
  "stage": "review",
  "summary": "short human-readable summary",
  "cases": [
    {
      "case_name": "case name or row id",
      "source": "source sentence",
      "target": "target sentence",
      "current_output": [
        "normalized relation 1",
        "normalized relation 2"
      ],
      "questionable_relations": [
        {
          "relation": "e.g. side -> そちら側",
          "why_questionable": "short semantic reason"
        }
      ],
      "phrase_observations": [
        "e.g. that side -> そちら側"
      ],
      "candidate_decisions": [
        {
          "action": "keep|remove|phrase_only|project_components|needs_review",
          "target": "relation or phrase",
          "reason": "short reason"
        }
      ],
      "recommended_decision": "one-line recommendation",
      "risk_if_wrong": "what might regress if this decision is wrong"
    }
  ]
}
```

### Stage 3: apply-and-verify packet

After making a change, report the outcome in JSON before giving the prose
summary.

Use this shape:

```json
{
  "stage": "post_change",
  "change_scope": "what was changed",
  "verification": {
    "unit_tests": "pass|fail",
    "extended_suite": "pass|fail",
    "sample_pack_2": "pass|fail|not-run",
    "sample_pack_3": "pass|fail|not-run",
    "staging_checks": "pass|fail|not-run"
  },
  "behavior_change": [
    {
      "case_name": "case name",
      "before": ["relation list before"],
      "after": ["relation list after"]
    }
  ],
  "remaining_questions": [
    "any open semantic judgment still worth user input"
  ]
}
```

## How to use user comments

When the user comments on a JSON review packet:

- treat the comment as a semantic decision first, not as a coding task
- update `candidate_decisions` and `recommended_decision`
- only then change code or test expectations
- preserve the raw phrase observation if the user rejects a naive word-level
  interpretation

Good examples:

- `that side -> そちら側`
  Prefer `phrase_only` unless there is independent evidence for `side -> 側`
- `examples of construction -> 施工事例`
  Often better as `project_components` with
  `construction -> 施工` and `example -> 事例` kept separate from the phrase
- `game title -> ゲームタイトル`
  Often safe to keep as a phrase-level lexical unit and also consider clean
  component promotion

## Default response style

For new users:

- do not assume they want raw inspect output first
- show a short prose summary and then a compact JSON block
- keep the JSON stable enough that the next agent or the same user can continue
  from it directly
- when possible, prefer one JSON packet per turn over multiple incompatible
  mini-formats

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
