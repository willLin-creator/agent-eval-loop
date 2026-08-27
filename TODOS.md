# TODOS

Work considered for v0.1 and deliberately left out, with the reason. Each entry has enough context
to pick up cold.

## Second-signal relaxation

**What:** let a rule relax only when zero recurrences AND a replay scenario for that rule has passed
N times. **Why:** recurrence alone cannot distinguish "internalized" from "the hook is silently
doing the work". **Why not yet:** it couples relaxation to scenario coverage, and most rules have no
scenario; in v0.1 that would make relaxation impossible for nearly everything. **Start:** add
`relax_requires_replay: true` to the rule schema, read `runs/` for the latest verdicts per rule in
`recommend()`, emit INSUFFICIENT with a "no passing replay" note when missing. **Blocked by:** a
corpus with scenarios for the rules you want to relax.

## Automatic case capture from hat panels

**What:** when a hat panel's reconcile step adopts a finding, write the case file without a human
invoking `skills/correct/`. **Why:** the manual step is the point of highest friction in the loop.
**Why not yet:** needs the panel orchestrator to emit findings in a structured form; today they are
prose. **Start:** a `findings.json` contract for hat outputs, then a small adapter that maps adopted
findings to `cases/`.

## Continuous scoring

**What:** run `score` and `graduate` on a schedule (cron, a git hook, a CI job). **Why not yet:**
real corpora are private, so a public CI job could only score the example corpus, which proves
nothing. Locally this is one cron line; see `scripts/` in the sibling memory-vault repo for the
pattern. **Start:** `graduate` is already idempotent, so a daily run appends only on change.

## Viewer

**What:** a browsable view of `score` output over time. **Why not yet:** the table is enough for
one person; the JSON output exists for anyone who wants to chart it.

## Scenario authoring guide

**What:** a document on writing scenarios whose `expected` line a judge can grade reliably. **Why
not yet:** three scenarios is too few to know what the guidance should say. **Start:** after a
corpus has ten or more scenarios and some calibration history, write down what separated the
reliable ones.

## Judge plugins, scenario DSL

**What:** pluggable judge backends, a richer scenario format. **Why not yet:** three scenarios do
not justify an abstraction. The `$JUDGE_CMD` string is the plugin interface for now.

## Larger corpora

**What:** an index (SQLite) once a flat directory of cases stops being instant. **Why not yet:**
hundreds of files load in well under a second. Revisit at tens of thousands.
