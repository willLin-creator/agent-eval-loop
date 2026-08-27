# Architecture

## The claim

An agent that gets corrected should get corrected less over time, and the amount of enforcement
each rule needs should follow the evidence in both directions. Most systems can say the first half
and cannot measure it. This repo measures it, and uses the measurement.

## The loop

```
                         work with no oracle (spec, message, plan)
                                        |
                                        v
                 GENERATE ---> EVALUATE (hat panel, fresh context) ---> RECONCILE
                                                                            |
                                     "the draft should have known this"     |
                                                                            v
                                                              CORRECTION  (skills/correct)
                                                                            |
                                                                            v
      rules/<slug>.md  <---- tagged by slug ----   cases/<date>-<slug>.md  (one file each)
       tier: hook|pinned|recall                             |
              ^                                             v
              |                              eval_loop.py score      per-rule recurrence
              |                                             |         over rolling windows
              |                                             v
       a HUMAN moves the tier   <---------   eval_loop.py graduate   RECOMMEND / BLOCKED /
       (never the tool)                       appends to ledger.md   INSUFFICIENT, both directions
              |
              v
       the next GENERATE runs with lighter or heavier enforcement, on evidence
```

Alongside, `eval_loop.py replay` runs hand-written scenarios through the agent and a judge, for the
small set of rules where a behavior is stable enough to script. Replay is a second signal, not the
spine: most corrections are one-off situations that cannot be replayed, and the recurrence count
does not need them to be.

## The three tiers

| Tier | What it means | Cost |
|---|---|---|
| `hook` | A mechanism enforces the rule (a pre-tool check, a lint, a guard script). The agent cannot violate it even if it forgets. | Highest. Every hook is code to maintain and a place the agent's judgment is overridden. |
| `pinned` | The rule is loaded into context every session. The agent is reminded, not prevented. | Context tokens on every turn. |
| `recall` | The agent is trusted to remember. The rule exists in memory and is recalled when relevant. | Nearly free, until it is forgotten. |

The interesting question is not "which tier should a rule be in" but "which tier does the
evidence say it needs right now". A rule that recurs three times in ninety days at `pinned` needs a
hook. A `hook` rule with zero recurrences in six months is a candidate for `pinned`: either the
model has internalized it, or the hook is doing the work invisibly, and the only way to find out is
to relax it and watch the count.

## Both directions, with brakes

```
              n >= promote_n within promote_window_days
   recall  ------------------------------------------------>  pinned  ------------------>  hook
     ^                                                          ^                            |
     |            0 recurrences across relax_window_days        |                            |
     +----------------------------------------------------------+----------------------------+
                          and today - created >= relax_window_days     (else INSUFFICIENT)
                          and never_relax is false                     (else BLOCKED)
```

Three brakes on relaxation:

1. **`created`.** A rule written ten days ago has zero recurrences in 180 days by arithmetic, not by
   merit. Relaxation needs the rule to be older than its own window.
2. **`never_relax`.** Safety rules (never send without approval, never write to production, never
   leak private data) do not relax on evidence. A quiet window means the guard is working. `graduate`
   still reports the candidate, marked BLOCKED, so you can see the rule would have qualified.
3. **Recommend only.** `graduate` appends a row to `ledger.md`. It never edits a rule file. A human
   reads the row and moves the tier, or does not. The tool that measures is not the tool that acts.

## Standalone by default, integrates by pointer

The corpus is a directory of Markdown files with flat frontmatter. The engine is one stdlib Python
file. Nothing here imports, reads, or requires a memory system, a task tracker, or any particular
agent framework. `tests/` includes a test that runs the engine against a corpus with no other
system present.

Integration is by pointer. If you run a memory layer, a rule slug is a fine thing for a memory to
link to, and a promoted rule is a fine thing to write a memory about. If you run a harness that
evaluates code, its evaluator can wear a hat from `hats/`. If you run an assistant that gets
corrected, its correction path can call `skills/correct/`. None of those are required for the
loop to close; they make it close faster.

## What the example corpus demonstrates

`example-corpus/` is seeded so the first run of every subcommand shows every check firing: a rule
that promotes, one that relaxes, one blocked by `never_relax`, one too new to relax, one with too
few cases to trust, one dangling case, three scenarios, three calibration outputs. Run everything
with `--today 2026-08-27` to reproduce the documented output. `example-corpus/README.md` maps each
seeded item to what it shows.

## What this repo is not

Not a benchmark. The numbers are about your agent under your corrections, and they are not
comparable to anyone else's.

Not a replacement for tests. Where an oracle exists, use it; `hats/` and the judge are for the
work that has none.

Not autonomous. Every tier move is a human decision with a ledger row behind it. The loop gets
lighter because someone decided it should, on evidence the loop produced.
