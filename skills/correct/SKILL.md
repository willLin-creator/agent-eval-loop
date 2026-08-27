---
name: correct
description: Turn a correction the user just gave into a schema-valid case file in the eval corpus, and create or link the rule it is evidence for. The write path of the eval loop.
---

# /correct

When the user corrects you, the correction is data. This skill writes it down in the shape
`eval_loop.py` can count, so the next `score` reflects it and the next `graduate` can act on it.

## Trigger

Any of these, in the user's words or yours:
- The user says you got something wrong and says what should have happened.
- An evaluator or hat panel catches something the draft should have known (the Reconcile step of
  `protocol/generate-evaluate-reconcile.md`).
- You notice, unprompted, that you violated a rule that exists.

Not a trigger: a preference stated for the first time with no violation behind it. That is a rule
without a case; write the rule file and stop.

## Steps

1. **Locate the corpus.** `$AGENT_EVAL_DIR` if set, else `corpus/` in the current repo, else ask
   once. Never write into `example-corpus/`.

2. **Find the rule.** List `rules/` and match the correction to an existing slug by reading the
   rule bodies, not the filenames. If one matches, use it. If none does, propose a new slug
   (`^[a-z0-9-]+$`, a short verb phrase: `verify-before-send`, `one-clarifying-question`) and
   confirm it with the user in the same breath as the case. A new rule file needs `slug`, `tier`
   (default `recall`), `created` (today), and a one-paragraph body. Never guess `never_relax`; ask
   if the rule is a safety rule.

3. **Write the case.** File: `cases/<today>-<slug>-<n>.md`, where `<n>` is 1 plus the number of
   cases already present for that slug today.

   ```
   ---
   date: <YYYY-MM-DD, today>
   rule: <slug>
   severity: <low | medium | high, optional>
   ---
   <What went wrong, in two or three sentences, written for a reader who was not there.
    Then the rule, restated in the form that would have prevented it.>
   ```

   The body is prose. It is never linted, so write it for a human. Quote the user's correction
   where it helps.

4. **Validate.** Run `python3 eval_loop.py --dir <corpus> check`. If it fails, fix the file you
   wrote before doing anything else.

5. **Report in one line.** "Logged as `<slug>` (case N in the last 90 days)." Read N from
   `score`. If N just crossed the rule's `promote_n`, say so: the next `graduate` will recommend
   a promotion and the user may want to run it now.

6. **Optional pointer.** If the user runs a memory layer, link the memory that carries this rule to
   the slug (for example a `[[slug]]` reference), and if the rule was just promoted to `hook`, note
   in the memory that a mechanism now enforces it. Do this only if such a layer exists; the case
   file is the record either way.

## What this skill never does

- Never edits a rule's `tier`. That is a human decision recorded by `graduate`'s ledger.
- Never writes a case for a correction that has not happened.
- Never merges two corrections into one case. Two on one day for one rule is two files.
- Never writes into `example-corpus/`.

## Example

User: "You proposed Thursday at 10 without checking my calendar. Thursday at 10 is booked."

Written: `cases/2026-08-27-check-calendar-first-1.md`

```
---
date: 2026-08-27
rule: check-calendar-first
severity: low
---
Proposed "Tuesday at 2 or Thursday at 10" in a draft reply without opening the calendar. Thursday
at 10 was already booked. Rule: check the calendar before proposing any specific time, or say the
calendar was not checked and defer the times.
```

Reported: "Logged as `check-calendar-first` (case 2 in the last 90 days)."
