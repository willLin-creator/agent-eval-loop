# Hats: evaluating work that has no oracle

A test suite is an oracle. Lint is an oracle. A spec, a customer message, a strategy memo, and a
plan have none: nothing mechanical can tell you they are wrong. For that class of work the
evaluator is a **panel of skeptical role-hats**, each reading in fresh context, each told to assume
the draft is wrong and to construct concrete failure scenarios.

## When a hat panel, when a scored case

```
   Is there an oracle (tests, lint, a checker)?
        yes ---> run it. Then a single fresh-context evaluator reads what the oracle cannot see.
        no  ---> is the draft high-stakes (writes real records, irreversible, someone is liable)?
                    yes ---> full panel: domain expert + principal engineer + AI-native PM
                             (+ two fresh-lens reviewers when the STRUCTURE is the risk)
                    no  ---> one hat, chosen by where the draft is most likely to be wrong
   Every correction that comes out of any of these ---> a case (docs/SCHEMA.md)
```

Match rigor to stakes. A full panel is 5 to 7 agent runs. Spending that on a low-stakes draft
trains everyone to skim the findings.

## The four hats

| Hat | Catches | Load-bearing when |
|---|---|---|
| [`principal-engineer`](../hats/principal-engineer.md) | False claims about current behavior; promised value the design cannot deliver | The draft describes a system that exists |
| [`domain-expert`](../hats/domain-expert.md) | Field-level errors; things dangerous to automate on a record someone signs | The output touches a record with a liable owner |
| [`ai-native-pm`](../hats/ai-native-pm.md) | Over-generalization from few examples; silent-harm paths; unbuildable confidence models | The draft proposes an agent acting on real data |
| [`fresh-lens`](../hats/fresh-lens.md) (run two) | Structure that mirrors input order instead of the problem; overlap, gaps, wrong altitude | The draft decomposes work into parts |

Each hat file is a template with `{{SLOTS}}`. Fill them from the draft and from what you have
verified about the real system. Never fill a slot from the draft's own claims about the system;
that is the thing the panel is checking.

## Running a panel

1. **Ground first.** Verify what the draft says about the current system against the system itself
   (code, screenshots, real data). Hand the panel the grounding, not the draft's assertions.
2. **Dispatch in parallel**, each hat in its own fresh context, single writer per output file.
3. **Each hat parks, never stalls.** If a hat hits an unknown the grounding missed, it records it as
   a flagged assumption and continues. A hat that stops to ask has broken the panel's parallelism.
4. **Reconcile** (see [`../protocol/generate-evaluate-reconcile.md`](../protocol/generate-evaluate-reconcile.md)).
   The orchestrator holds the most context. It adopts what the hats genuinely caught, discards
   context-free critique, and surfaces contradictions between hats as decisions with a
   recommendation, never as silently resolved.
5. **Write the cases.** Every place the reconcile step says "the draft should have known this" is a
   correction. `skills/correct/` turns it into a case file. That is how a panel run feeds the score.

## Decision packet

The human sees a packet, never raw hat output. Per item: the decision in one line, two to four
options, a recommendation, the evidence (a failure scenario, a code fact, a quote), the tradeoff.
Default strength scales inversely with stakes: for reversible calls, lead with a strong default to
confirm; for irreversible ones, present the options without a pre-selected default so the gate is a
real choice.

## What this is not

Not a replacement for tests where tests are possible. Not a committee: the panel challenges, the
primary decides. Not a one-time review: the same hats run again when the draft changes materially,
and the cases from each run are what make the next run cheaper.
