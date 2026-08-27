# agent-eval-loop

**How do you know your agent is getting better?** Corrections as scored cases, skeptical hat
panels for work that has no test suite, and rule enforcement that gets lighter or heavier on
evidence instead of on instinct.

Plain Markdown, one stdlib Python file, no framework. Your corrections stay on your machine; the
repo ships the engine, the schema, and an example corpus.

> Built on the Generator-Evaluator pattern from Anthropic's [_Harness design for long-running agents_](https://www.anthropic.com/engineering/harness-design-long-running-apps):
> separate the critic from the creator, run the critic in fresh context. This repo is the half of
> that idea for work with **no oracle** (a spec, a message, a plan), and the loop that closes
> behind it. Its sibling, [`agent-harness`](https://github.com/willLin-creator/agent-harness), is
> the half for code.

## Quick start

```bash
git clone https://github.com/willLin-creator/agent-eval-loop && cd agent-eval-loop
python3 eval_loop.py --dir example-corpus --today 2026-08-27 check      # exits 1: one dangling case, on purpose
python3 eval_loop.py --dir example-corpus --today 2026-08-27 score
python3 eval_loop.py --dir example-corpus --today 2026-08-27 graduate
python3 -m unittest                                                      # 63 tests, no network
```

`graduate` on the example corpus emits one of each verdict:

```
rule                               direction   n window verdict      note
+never-send-without-approval       relax       0    180 BLOCKED      never_relax
+no-dash-connectors                relax       0    180 RECOMMEND    hook -> pinned
+one-clarifying-question           relax       0    180 INSUFFICIENT rule is 12d old, window is 180d
+verify-before-send                promote     3     90 RECOMMEND    pinned -> hook
```

To start your own corpus: `mkdir corpus && cp -R example-corpus/rules corpus/` (it is gitignored),
delete the rules you do not want, and log your first correction with [`skills/correct/`](skills/correct/SKILL.md).

**Using Claude Code?** Point it at the repo: "Set up agent-eval-loop for my corrections." It reads
`docs/SCHEMA.md` and `skills/correct/`, creates `corpus/`, and writes your first rule.

## The loop

```
   work with no oracle  --->  GENERATE  --->  EVALUATE (hat panel, fresh context)  --->  RECONCILE
                                                                                            |
                                                             "the draft should have known this"
                                                                                            v
     rules/<slug>.md  <---- slug ----  cases/<date>-<slug>.md   <----   CORRECTION (skills/correct)
      tier: hook | pinned | recall             |
              ^                                v
              |                  score: recurrence per rule per window
              |                                v
      a human moves the tier  <---  graduate: RECOMMEND / BLOCKED / INSUFFICIENT, both directions
```

1. **Evaluate without an oracle.** [`hats/`](hats/) are four skeptical role prompts (principal
   engineer against live code, domain expert, AI-native PM, two blind fresh-lens reviewers). Each
   assumes the draft is wrong and constructs failure scenarios. [`protocol/`](protocol/) is the
   Generate, Evaluate, Reconcile discipline they run inside: the evaluator challenges, the primary
   decides. [`docs/HATS.md`](docs/HATS.md) says when to use which.
2. **Corrections become cases.** Every time the agent is corrected, one Markdown file with a date
   and a rule slug ([`docs/SCHEMA.md`](docs/SCHEMA.md)). [`skills/correct/`](skills/correct/SKILL.md)
   is the write path.
3. **Cases become a number.** `score` counts recurrences per rule over rolling windows and shows N
   beside every rate, because one correction in ninety days is not a trend.
4. **The number moves enforcement, both ways.** A rule that recurs three times at `pinned` needs a
   `hook`. A `hook` with zero recurrences in six months is a candidate to relax. `graduate` says
   which, appends a row to `ledger.md`, and **never edits a rule**: a human moves the tier. Safety
   rules carry `never_relax: true` and are reported BLOCKED rather than recommended.
5. **Replay, where a behavior is scriptable.** `replay` runs `scenarios/` through your agent CLI
   and a judge model, records everything under `runs/`, and treats "could not judge" as ERROR,
   never as FAIL. [`docs/JUDGE.md`](docs/JUDGE.md) is the contract.

The full design, including why relaxation has three brakes, is in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## The judge, honestly

Replay in v0.1 is a working skeleton: three scenarios and a judge validated against three canned
outputs, not a benchmark. The calibration run is committed under
[`example-corpus/runs/calibration/`](example-corpus/runs/calibration/): a clear pass, a clear fail,
and an injection trap (an output that breaks the rule and then instructs the evaluator to return
PASS). **3/3 as expected**, and the judge's own reason on the trap was that "the embedded
instruction to return PASS is data and was ignored." Run it yourself:

```bash
python3 eval_loop.py --dir example-corpus replay --calibrate
```

Cost: replay is one agent call plus `--votes` judge calls per scenario; calibration is one judge
call per canned output. The example corpus is six calls end to end.

## Safety

- **Your corpus never ships.** `corpus/` and `runs/` are gitignored. `scripts/public-repo-guard.sh`
  is a pre-push hook that blocks any outgoing diff containing a term from your `.private-terms`
  file (company names, ticket-id shapes, customer names).
- **The agent under test runs hermetically**: no built-in tools, no MCP servers, no inherited
  settings (`claude -p --tools "" --restricted --strict-mcp-config`), in an empty temporary
  directory, because a scenario is untrusted input. A denylist was tried first and leaked through an
  MCP server; `docs/JUDGE.md` has the story. `--allow-tools` is explicit opt-in.
- **A PASS must quote its evidence** or the runner refuses to count it. That is the structural
  defense against a scenario talking the judge into a verdict.
- **Nothing here changes a rule's tier.** The tool measures; you decide.

## Works with or without the rest of your stack

Standalone by default, integrates by pointer. No memory system, task tracker, or agent framework is
required, and `tests/` proves the engine runs against a corpus with nothing else present. If you run
a memory layer such as [`agent-memory-vault`](https://github.com/willLin-creator/agent-memory-vault),
a rule slug is a fine thing for a memory to link to. If you run
[`agent-harness`](https://github.com/willLin-creator/agent-harness) for code, its evaluator can wear
a hat from here.

## Layout

```
eval_loop.py             check | score | graduate | replay      (stdlib only)
docs/                    ARCHITECTURE  SCHEMA  HATS  JUDGE
protocol/                generate-evaluate-reconcile  evaluator-tiers
hats/                    principal-engineer  domain-expert  ai-native-pm  fresh-lens
skills/correct/          the write path (a Claude Code skill; the steps work in any agent)
example-corpus/          seeded so every check fires; see its README
scripts/                 public-repo-guard.sh
tests/                   unittest suite; LIVE=1 adds one real end-to-end run
TODOS.md                 what was left out of v0.1 and why
```

## Background

This is an extraction, not a design exercise. The hats, the protocol, and the tier model came out of
months of running an AI chief-of-staff on real work and being corrected by it daily. The
correction log that made the scorer obvious had a hundred entries before anyone called it a
dataset. What is here is the shape that survived, with the private specifics removed.

MIT.
