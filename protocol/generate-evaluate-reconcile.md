# Generate, Evaluate, Reconcile

The protocol behind every evaluation in this repo. Three steps, three roles, and one rule about who
decides.

```
   GENERATE                 EVALUATE                       RECONCILE
   primary agent  ------>   separate skeptical agent  --->  primary agent again
   holds the context        fresh context, assumes          adopts what it genuinely
   produces the draft       the draft is WRONG              missed, discards critique
                            challenges on three axes        that only lacked context
                                                            then ships
```

## 1. Generate

The primary agent produces the draft: a spec, a message, a plan, a recommendation, a piece of code.
It has the most context of anyone in the loop and it keeps that context through step 3.

## 2. Evaluate

A different agent, in a **fresh context**, reads the draft assuming it is wrong and tries to show
how. Fresh context is the whole point: an evaluator that shares the generator's context shares its
blind spots and rubber-stamps its own work. The evaluator challenges on three axes:

| Axis | The question |
|---|---|
| Goal alignment | Does this serve the stated goal, or a proxy for it? Would the owner recognize it as progress on what they said mattered? |
| Decision grade | Is there a recommendation with a next step, or is this a summary wearing a recommendation's clothes? |
| Ready as-is | Would the owner ship, send, or act on this without editing it? If not, what exactly would they change? |

For work with a domain, the evaluator wears a hat (see `../hats/`). For work with an oracle (code
with tests), the evaluator runs the oracle first and reads second.

## 3. Reconcile

The primary agent reads the critique **skeptically**. It adopts what the evaluator genuinely
caught. It discards what the evaluator flagged only because it lacked context the primary has. It
does not argue with the evaluator and it does not defer to it. Then it ships.

## The one rule

**Final judgment stays with the primary. The evaluator challenges; it does not gate.**

An evaluator that can block is an evaluator that will be appeased, and appeasement produces drafts
that are defensible instead of good. The evaluator's job is to make the primary see what it missed.
The primary's job is to decide. Keep those separate.

## When to skip it

Pass-through output with no judgment in it: a link, a calendar time, a lookup result. Running an
evaluator over a fact wastes the evaluator.

## What this repo adds

Every Reconcile step is a place where a correction can happen: the evaluator caught something the
primary should have known. That correction is a **case** (`docs/SCHEMA.md`). Write it with
`skills/correct/`. Over time the cases tell you which rules the primary keeps missing, and
`eval_loop.py graduate` tells you which of those need a mechanism instead of a reminder.
