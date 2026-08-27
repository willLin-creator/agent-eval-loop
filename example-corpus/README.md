# Example corpus

A small corpus seeded so that the first run of every subcommand shows every check firing. Run from
the repo root with `--today 2026-08-27` to reproduce the documented output exactly.

| Item | What it demonstrates |
|---|---|
| `rules/verify-before-send.md` | 3 recurrences in 90 days: `graduate` RECOMMENDs promote (pinned to hook) |
| `rules/no-dash-connectors.md` | 0 recurrences in 180 days, old enough: `graduate` RECOMMENDs relax (hook to pinned) |
| `rules/never-send-without-approval.md` | qualifies to relax but `never_relax: true`: BLOCKED |
| `rules/one-clarifying-question.md` | created 12 days ago, 0 cases: INSUFFICIENT, not a relax candidate |
| `rules/check-calendar-first.md` | 1 recurrence: `score` flags low N, no recommendation either way |
| `cases/2026-08-20-quote-the-source-1.md` | dangling `rule:`: `check` fails, `score` counts it under `_unlinked` |
| `scenarios/` | three hand-authored replay scenarios, one per rule family |
| `calibration/` | three canned outputs (clear pass, clear fail, prompt-injection trap) for `replay --calibrate` |

```
python3 eval_loop.py check    --dir example-corpus --today 2026-08-27   # exits 1: one dangling case
python3 eval_loop.py score    --dir example-corpus --today 2026-08-27
python3 eval_loop.py graduate --dir example-corpus --today 2026-08-27
```
