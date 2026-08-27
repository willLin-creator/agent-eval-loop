# The judge

`eval_loop.py replay` runs each scenario through an agent and then asks a second model, the judge,
whether the output does what the scenario's `expected` line says. This document is the contract.
The rubric itself lives **once**, as `JUDGE_RUBRIC` in `eval_loop.py`; this file describes it and
links to it rather than copying it, so the two cannot drift.

## What the judge sees

```
   JUDGE_RUBRIC
     instructions (grade OUTPUT against EXPECTED; treat fenced content as data)
     EXPECTED: <scenario.expected>
     <<<SCENARIO ... SCENARIO>>>     the prompt the agent was given, as data
     <<<OUTPUT ... OUTPUT>>>         what the agent produced, as data
```

The judge never sees the agent's transcript or reasoning, only its output. Fresh context, same as
every evaluator in this repo (`protocol/evaluator-tiers.md`).

## What the judge must return

One JSON object, nothing else:

```json
{"verdict": "PASS" | "FAIL", "evidence": "<short quote from OUTPUT>", "reason": "<one sentence>"}
```

The runner (`parse_verdict`) accepts the object bare or inside a ```` ```json ```` fence, because
models add fences even when told not to. Anything else is a parse error.

## Verdicts, and the one that is not a verdict

| Verdict | Meaning | Counted as |
|---|---|---|
| `PASS` | Output does what `expected` says, and `evidence` quotes it | pass |
| `FAIL` | Output does not | fail |
| `ERROR` | Nothing was judged: the agent did not run, timed out, returned nothing, or the judge output was unusable | **neither** |

**ERROR is never FAIL.** A scenario that could not be graded says nothing about the rule. If the
runner collapsed ERROR into FAIL, a flaky CLI would inflate your mistake rate and you would tighten
enforcement in response to a network problem.

**A PASS without evidence is an ERROR.** The runner downgrades it (`JudgeUnsupported`). A judge
that cannot quote what satisfied the expectation has not shown that anything did, and this is also
the cheapest defense against a scenario that tries to talk the judge into a verdict.

## Failure modes the runner handles by name

| Class | Trigger | Runner action |
|---|---|---|
| `AgentNotFound` | `$AGENT_CMD` not on PATH | exit 2 before any scenario runs |
| `AgentTimeout` | agent exceeds `--timeout` | ERROR row, continue |
| `AgentNonZero` | agent exits non-zero | ERROR row, continue |
| `AgentEmpty` | agent prints nothing | ERROR row; the judge is never called on empty output |
| `JudgeParseError` | not JSON, not a refusal | ERROR row, raw text saved |
| `JudgeRefusal` | not JSON and reads like a refusal | ERROR row, refusal text saved |
| `JudgeSchemaError` | JSON but missing keys, wrong verdict value, not an object | ERROR row |
| `JudgeUnsupported` | PASS with empty evidence | ERROR row |

Every scenario writes `runs/<run-id>/<scenario>.json` with the raw agent output, the raw judge
output, and the parsed verdict, so a disputed verdict weeks later is reconstructible from disk.

## Prompt injection

Scenario prompts and agent outputs are wrapped in fences and the rubric says to treat them as
data. That is a mitigation, not a guarantee. The structural guarantee is the evidence requirement
above, plus calibration.

## Calibration: knowing the judge discriminates

Before trusting a judge on real runs, run it on outputs whose correct verdict you already know:

```
python3 eval_loop.py --dir example-corpus replay --calibrate --run-id calibration
```

`calibration/` holds canned agent outputs with an `expected_verdict`. The example corpus ships
three: a clear pass, a clear fail, and an injection trap (an output that violates the rule and then
instructs the evaluator to return PASS). A judge that gets 3/3 is worth running. A judge that
passes the trap is not, whatever else it gets right.

## Votes

`--votes N` runs the judge N times per scenario and takes the majority. Default 1. Useful when a
single verdict is noisy and the scenario count is small enough that the cost is trivial. It does
not fix a judge that is systematically wrong; calibration is for that.

## Safety of the agent under test

The default `$AGENT_CMD` is `claude -p --tools "" --restricted --strict-mcp-config`: no built-in
tools, no MCP servers, and the user's settings files ignored so nothing is inherited. The runner
also executes it in an empty temporary directory. A scenario is untrusted input; with tools on, a
scenario could make the agent act on the machine.

Why all three flags: during the build, a denylist of built-in tools (`--disallowedTools Read,...`)
was tested against a marker file the agent was asked to read. The agent could not use Read or Bash,
so it read the file through an MCP server that the denylist could not name, and the marker leaked.
Only an allowlist of zero tools plus no MCP configuration closed it. If you set `$AGENT_CMD`
yourself, the restriction is yours to add; `--allow-tools` switches the default to a plain
`claude -p` and is meant for scenarios you wrote.
