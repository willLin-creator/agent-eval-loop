# Schema

Everything in a corpus is a Markdown file with a short YAML-ish frontmatter block. One parser reads
all of them. Frontmatter is flat `key: value` lines between `---` fences; no nesting, no lists.
Values are strings unless noted. Dates are `YYYY-MM-DD`. Booleans are `true` / `false`.

`check` lints frontmatter and the first body line only. Prose bodies are never linted, so a case
body can contain pipes, dates, or rule-shaped words without tripping anything.

## Corpus layout

```
<corpus>/
  rules/<slug>.md          one file per rule
  cases/<date>-<slug>-<n>.md   one file per correction
  scenarios/<slug>.md      one file per replay scenario
  calibration/<name>.md    canned agent outputs with a known verdict (judge-only)
  ledger.md                append-only decision record written by `graduate`
  runs/                    replay output, one directory per run (gitignore this in a real corpus)
```

## Rule: `rules/<slug>.md`

| Field | Required | Values | Notes |
|---|---|---|---|
| `slug` | yes | `^[a-z0-9-]+$` | Stable identifier. Must equal the filename stem. Never a number: numbers get renumbered, slugs do not. |
| `tier` | yes | `hook` \| `pinned` \| `recall` | Current enforcement. `hook` = a mechanism enforces it. `pinned` = always in context. `recall` = the agent is trusted to remember it. |
| `never_relax` | no, default `false` | bool | Safety rules. `graduate` will still report a relax candidate, marked BLOCKED, and will never recommend it. |
| `created` | yes | date | When the rule was first written. Relaxation requires the rule to be older than `relax_window_days`, otherwise a 10-day-old rule trivially has zero recurrences in 180 days. |
| `promote_n` | no | int | Overrides the global default (3). Recurrences in `promote_window_days` at or above this recommend promotion. |
| `promote_window_days` | no | int | Overrides the global default (90). |
| `relax_window_days` | no | int | Overrides the global default (180). Zero recurrences across this window recommend relaxation. |

Body: the rule, as the agent should read it. One paragraph is plenty. A rule that needs a page is
several rules.

## Case: `cases/<date>-<slug>-<n>.md`

| Field | Required | Values | Notes |
|---|---|---|---|
| `date` | yes | date | The day the correction happened. Never in the future. |
| `rule` | yes | slug | The rule this correction is evidence for. A slug with no matching rule file is a dangling case: `check` fails and `score` counts it under `_unlinked`. |
| `severity` | no | `low` \| `medium` \| `high` | Informational. Scoring counts occurrences; it does not weight them. |

Body: what went wrong, then what the rule is. Written for a reader who was not there. Two
corrections on one day for one rule are two cases. That is honest: it happened twice.

Filename convention `<date>-<slug>-<n>` keeps the directory sortable and makes the second case on a
day obvious. The parser reads frontmatter, not the filename.

## Scenario: `scenarios/<slug>.md`

| Field | Required | Values | Notes |
|---|---|---|---|
| `rule` | yes | slug | The rule this scenario exercises. |
| `expected` | yes | one line | What a passing output does, in observable terms. The judge grades against this line. |

Body: the prompt handed to the agent under test. It reaches the judge inside a delimited data block,
so a scenario cannot instruct the judge.

## Calibration: `calibration/<name>.md`

| Field | Required | Values | Notes |
|---|---|---|---|
| `scenario` | yes | slug | Which scenario this canned output pretends to answer. |
| `expected_verdict` | yes | `PASS` \| `FAIL` \| `ERROR` | What a correct judge returns for this output. |

Body: a canned agent output. `replay --calibrate` sends only these to the judge (no agent run) and
diffs the verdicts. This is how you know the judge discriminates before trusting it on real runs.

## Ledger: `ledger.md`

A Markdown table, appended by `graduate`, read back by `graduate` to stay idempotent.

```
| date | rule | direction | n | window_days | verdict | note |
```

| Column | Values |
|---|---|
| `direction` | `promote` \| `relax` |
| `verdict` | `RECOMMEND` (threshold met, human should move the tier) \| `BLOCKED` (threshold met, `never_relax`) \| `INSUFFICIENT` (relax window not satisfied because the rule is too new) |

`graduate` appends a row only when a rule's `direction` or `verdict` differs from that rule's most
recent row. `--force` appends regardless. `graduate` never edits a rule file; a human moves the tier.

## Tiers and the two directions

```
              n >= promote_n within promote_window_days
   recall  ------------------------------------------------>  pinned  ------------------>  hook
     ^                                                          ^                            |
     |            0 recurrences across relax_window_days        |                            |
     +----------------------------------------------------------+----------------------------+
                          and today - created >= relax_window_days
                          and never_relax is false          (else BLOCKED)
```

Promotion is one step at a time. Relaxation is one step at a time. `graduate` recommends; it does not
move anything.

## Replay verdict (judge output)

The judge must return one JSON object and nothing else:

```json
{"verdict": "PASS", "evidence": "<a quote from the agent output>", "reason": "<one sentence>"}
```

| Verdict | Meaning |
|---|---|
| `PASS` | The output does what `expected` says. `evidence` must be non-empty; a PASS with empty evidence is downgraded to ERROR by the runner. |
| `FAIL` | The output does not do what `expected` says. |
| `ERROR` | Not a judgment about the rule: the agent did not run, timed out, returned nothing, or the judge output could not be parsed. ERROR is never counted as FAIL. |

Fenced JSON (```` ```json ... ``` ````) is accepted and unwrapped. Anything else is a parse error.
