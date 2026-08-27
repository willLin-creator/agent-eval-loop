# Evaluator tiers

Two rules about which model evaluates, and one about how it is run.

## Evaluator >= generator

The evaluator must be at least as capable as the generator it grades. A weaker judge cannot see
what a stronger generator got wrong; it can only see what it would have gotten wrong itself, which
is a different and smaller set. If you can only afford one frontier call in the loop, spend it on
the evaluator.

## A floor, not a ladder

Do not route evaluation down to a small model to save tokens. First-pass correctness beats the
token delta, and a wrong verdict costs more than the call it saved: it either passes a defect or
sends the generator chasing a ghost. Set a floor (the most capable model you use routinely) and run
every evaluator at or above it. Reserve the frontier tier for architecture, security, concurrency,
novel design, and any evaluation whose verdict is hard to reverse once acted on.

Going below the floor is defensible only when all three hold:

1. The check is strictly mechanical against a pattern that already landed.
2. There is zero judgment per item.
3. The result is verifiable by a gate that does not involve the small model.

When unsure, the floor.

## Fresh context

The evaluator runs in a fresh context with the draft and the rubric, never the generator's
transcript. It should not know what the generator was thinking, only what it produced. This is
what makes it a skeptic rather than a second reader nodding along.

## How `eval_loop.py replay` applies this

The replay runner takes `--agent-model-tier N` and `--judge-model-tier N` as optional ordinals and
warns when the judge's is lower. It cannot know which model a command string invokes, so the
ordinals are yours to declare; the warning is there so the rule is at least visible when it is
broken.

## Panels

One evaluator sees one set of failure modes. When a draft can fail in several unrelated ways
(domain correctness, automation safety, structural shape), run several evaluators with different
lenses rather than the same evaluator several times. Diversity of lens catches what redundancy
cannot. The hats in `../hats/` are that diversity, written down.
