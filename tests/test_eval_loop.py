#!/usr/bin/env python3
"""Tests for eval_loop.py. Run from the repo root: python3 -m unittest -v

Layout of the fixtures:

    example-corpus/            the committed corpus, read-only in tests; asserts the documented
                               behavior of every seeded item on --today 2026-08-27
    tmp corpus (per test)      built by mk_corpus() from small dicts, for one-variable tests

Agent and judge are both tests/fake_cmd.py, selected by AGENT_CMD / JUDGE_CMD and steered by
FAKE_MODE. No network, no real CLI. `LIVE=1 python3 -m unittest tests.test_eval_loop.LiveTests`
runs the one real end-to-end scenario plus calibration against the configured CLI.
"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import eval_loop as el  # noqa: E402

TODAY = date(2026, 8, 27)
EXAMPLE = ROOT / "example-corpus"
FAKE = f"{sys.executable} {ROOT / 'tests' / 'fake_cmd.py'}"


def mk_corpus(root, rules=(), cases=(), scenarios=(), calibrations=()):
    root = Path(root)
    for sub in ("rules", "cases", "scenarios", "calibration"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    for r in rules:
        fm = "\n".join(f"{k}: {v}" for k, v in r.items() if k != "body")
        (root / "rules" / f"{r['slug']}.md").write_text(f"---\n{fm}\n---\n{r.get('body', 'rule text')}\n")
    for i, c in enumerate(cases):
        fm = "\n".join(f"{k}: {v}" for k, v in c.items() if k != "body")
        (root / "cases" / f"case-{i}.md").write_text(f"---\n{fm}\n---\n{c.get('body', 'what went wrong')}\n")
    for s in scenarios:
        (root / "scenarios" / f"{s['name']}.md").write_text(
            f"---\nrule: {s['rule']}\nexpected: {s['expected']}\n---\n{s['prompt']}\n")
    for c in calibrations:
        (root / "calibration" / f"{c['name']}.md").write_text(
            f"---\nscenario: {c['scenario']}\nexpected_verdict: {c['expected_verdict']}\n---\n{c['output']}\n")
    return root


def rule(slug, tier="pinned", created="2026-01-01", **kw):
    return {"slug": slug, "tier": tier, "created": created, **kw}


def sha_tree(path):
    h = hashlib.sha256()
    for p in sorted(Path(path).rglob("*")):
        if p.is_file():
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()


class TmpCorpusTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="eval-loop-test-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


# ------------------------------------------------------------------ parse_frontmatter
class TestParseFrontmatter(unittest.TestCase):
    def test_good(self):
        fm, body = el.parse_frontmatter("---\nslug: a-b\ntier: hook\n---\nbody text\n")
        self.assertEqual(fm, {"slug": "a-b", "tier": "hook"})
        self.assertEqual(body, "body text\n")

    def test_quoted_values_are_unquoted(self):
        fm, _ = el.parse_frontmatter('---\nexpected: "no dashes"\n---\n')
        self.assertEqual(fm["expected"], "no dashes")

    def test_no_frontmatter(self):
        fm, body = el.parse_frontmatter("just a body\n")
        self.assertEqual(fm, {})
        self.assertEqual(body, "just a body\n")

    def test_unterminated_fence_is_no_frontmatter(self):
        fm, _ = el.parse_frontmatter("---\nslug: x\nno closing fence\n")
        self.assertEqual(fm, {})


# ------------------------------------------------------------------ load_corpus / check
class TestLoadAndCheck(TmpCorpusTest):
    def test_missing_dir_raises(self):
        with self.assertRaises(el.CorpusNotFound):
            el.load_corpus(Path(self.tmp) / "nope", TODAY)

    def test_empty_corpus_is_ok(self):
        c = el.load_corpus(mk_corpus(self.tmp), TODAY)
        self.assertEqual((len(c.rules), len(c.cases), c.errors), (0, 0, []))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(el.check(c), 0)
        self.assertIn("ok: 0 rules", out.getvalue())

    def test_missing_frontmatter_collected(self):
        root = mk_corpus(self.tmp)
        (root / "rules" / "bad.md").write_text("no fences here\n")
        c = el.load_corpus(root, TODAY)
        self.assertEqual(len(c.errors), 1)
        self.assertIsInstance(c.errors[0], el.SchemaError)
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(el.check(c), 1)
        self.assertIn("SchemaError", err.getvalue())

    def test_dangling_rule_collected_and_case_still_loaded(self):
        root = mk_corpus(self.tmp, cases=[{"date": "2026-08-01", "rule": "ghost"}])
        c = el.load_corpus(root, TODAY)
        self.assertEqual(len(c.cases), 1)
        self.assertIsInstance(c.errors[0], el.DanglingRule)

    def test_duplicate_slug(self):
        root = mk_corpus(self.tmp, rules=[rule("a")])
        (root / "rules" / "b.md").write_text("---\nslug: a\ntier: hook\ncreated: 2026-01-01\n---\n")
        c = el.load_corpus(root, TODAY)
        kinds = {type(e) for e in c.errors}
        self.assertTrue(kinds & {el.DuplicateSlug, el.SchemaError})

    def test_bad_slug_path_traversal(self):
        root = mk_corpus(self.tmp, cases=[{"date": "2026-08-01", "rule": "../../etc/passwd"}])
        c = el.load_corpus(root, TODAY)
        self.assertIsInstance(c.errors[0], el.BadSlug)

    def test_future_date_rejected(self):
        root = mk_corpus(self.tmp, rules=[rule("a")], cases=[{"date": "2026-09-01", "rule": "a"}])
        c = el.load_corpus(root, TODAY)
        self.assertEqual(len(c.errors), 1)
        self.assertIn("after today", str(c.errors[0]))

    def test_bad_date_rejected(self):
        root = mk_corpus(self.tmp, rules=[rule("a")], cases=[{"date": "08/01/2026", "rule": "a"}])
        c = el.load_corpus(root, TODAY)
        self.assertIsInstance(c.errors[0], el.SchemaError)

    def test_bad_tier_rejected(self):
        root = mk_corpus(self.tmp, rules=[rule("a", tier="mandatory")])
        c = el.load_corpus(root, TODAY)
        self.assertIn("tier", str(c.errors[0]))

    def test_body_is_never_linted(self):
        body = "pipes | everywhere | 2099-01-01 | rule: ghost | ../../etc"
        root = mk_corpus(self.tmp, rules=[rule("a")], cases=[{"date": "2026-08-01", "rule": "a", "body": body}])
        c = el.load_corpus(root, TODAY)
        self.assertEqual(c.errors, [])

    def test_example_corpus_has_exactly_one_problem_the_dangling_case(self):
        c = el.load_corpus(EXAMPLE, TODAY)
        self.assertEqual(len(c.errors), 1)
        self.assertIsInstance(c.errors[0], el.DanglingRule)
        self.assertIn("quote-the-source", str(c.errors[0]))
        self.assertEqual(len(c.rules), 5)
        self.assertEqual(len(c.scenarios), 3)
        self.assertEqual(len(c.calibrations), 3)


# ------------------------------------------------------------------ count_in_window / score
class TestScore(TmpCorpusTest):
    def test_window_boundaries(self):
        cases = [{"rule": "a", "date": date(2026, 8, 27)},   # day 0
                 {"rule": "a", "date": date(2026, 7, 28)},   # day 30, inside a 30-day window
                 {"rule": "a", "date": date(2026, 7, 27)}]   # day 31, outside
        self.assertEqual(el.count_in_window(cases, "a", 30, TODAY), 2)
        self.assertEqual(el.count_in_window(cases, "a", 31, TODAY), 3)
        self.assertEqual(el.count_in_window(cases, "b", 30, TODAY), 0)

    def test_zero_window_is_an_arg_error(self):
        with self.assertRaises(el.ArgError):
            el.count_in_window([], "a", 0, TODAY)

    def test_low_n_flag(self):
        root = mk_corpus(self.tmp, rules=[rule("one"), rule("two"), rule("three")],
                         cases=[{"date": "2026-08-01", "rule": "one"}]
                               + [{"date": "2026-08-0%d" % d, "rule": "two"} for d in (1, 2)]
                               + [{"date": "2026-08-0%d" % d, "rule": "three"} for d in (1, 2, 3)])
        rows = {r["rule"]: r for r in el.score(el.load_corpus(root, TODAY), TODAY)["rules"]}
        self.assertTrue(rows["one"]["low_n"])
        self.assertTrue(rows["two"]["low_n"])
        self.assertFalse(rows["three"]["low_n"])

    def test_no_evidence_flag(self):
        root = mk_corpus(self.tmp, rules=[rule("quiet")])
        row = el.score(el.load_corpus(root, TODAY), TODAY)["rules"][0]
        self.assertTrue(row["no_evidence"])
        self.assertFalse(row["low_n"])

    def test_unlinked_counted_separately(self):
        root = mk_corpus(self.tmp, rules=[rule("a")],
                         cases=[{"date": "2026-08-01", "rule": "a"}, {"date": "2026-08-02", "rule": "ghost"}])
        result = el.score(el.load_corpus(root, TODAY), TODAY)
        self.assertEqual(result["_unlinked"], {"n": 1, "rules": ["ghost"]})
        self.assertEqual(result["rules"][0]["n_total"], 1)

    def test_example_corpus_documented_flags(self):
        rows = {r["rule"]: r for r in el.score(el.load_corpus(EXAMPLE, TODAY), TODAY)["rules"]}
        self.assertEqual(rows["verify-before-send"]["n_promote_window"], 3)
        self.assertTrue(rows["check-calendar-first"]["low_n"])
        self.assertTrue(rows["one-clarifying-question"]["no_evidence"])
        self.assertEqual(rows["no-dash-connectors"]["n_relax_window"], 0)


# ------------------------------------------------------------------ graduate
class TestGraduate(TmpCorpusTest):
    def _rows(self, root):
        return {r["rule"]: r for r in el.recommend(el.load_corpus(root, TODAY), TODAY)}

    def test_promote_on_threshold(self):
        root = mk_corpus(self.tmp, rules=[rule("a", tier="pinned")],
                         cases=[{"date": "2026-08-0%d" % d, "rule": "a"} for d in (1, 2, 3)])
        r = self._rows(root)["a"]
        self.assertEqual((r["direction"], r["verdict"], r["note"]), ("promote", "RECOMMEND", "pinned -> hook"))

    def test_below_threshold_no_row(self):
        root = mk_corpus(self.tmp, rules=[rule("a", tier="pinned")],
                         cases=[{"date": "2026-08-0%d" % d, "rule": "a"} for d in (1, 2)])
        self.assertEqual(self._rows(root), {})

    def test_hook_cannot_promote_further(self):
        root = mk_corpus(self.tmp, rules=[rule("a", tier="hook")],
                         cases=[{"date": "2026-08-0%d" % d, "rule": "a"} for d in (1, 2, 3)])
        self.assertEqual(self._rows(root), {})

    def test_relax_recommend(self):
        root = mk_corpus(self.tmp, rules=[rule("a", tier="hook", created="2025-01-01")],
                         cases=[{"date": "2025-06-01", "rule": "a"}])
        r = self._rows(root)["a"]
        self.assertEqual((r["direction"], r["verdict"], r["note"]), ("relax", "RECOMMEND", "hook -> pinned"))

    def test_relax_blocked_by_created(self):
        root = mk_corpus(self.tmp, rules=[rule("a", tier="hook", created="2026-08-15")])
        r = self._rows(root)["a"]
        self.assertEqual(r["verdict"], "INSUFFICIENT")

    def test_relax_blocked_by_never_relax(self):
        root = mk_corpus(self.tmp, rules=[rule("a", tier="hook", created="2025-01-01", never_relax="true")])
        r = self._rows(root)["a"]
        self.assertEqual((r["verdict"], r["note"]), ("BLOCKED", "never_relax"))

    def test_recall_cannot_relax_further(self):
        root = mk_corpus(self.tmp, rules=[rule("a", tier="recall", created="2025-01-01")])
        self.assertEqual(self._rows(root), {})

    def test_per_rule_threshold_override(self):
        root = mk_corpus(self.tmp, rules=[rule("a", tier="pinned", promote_n="1")],
                         cases=[{"date": "2026-08-01", "rule": "a"}])
        self.assertEqual(self._rows(root)["a"]["verdict"], "RECOMMEND")

    def test_graduate_never_touches_rules(self):
        root = mk_corpus(self.tmp, rules=[rule("a", tier="pinned")],
                         cases=[{"date": "2026-08-0%d" % d, "rule": "a"} for d in (1, 2, 3)])
        before = sha_tree(root / "rules")
        el.graduate(el.load_corpus(root, TODAY), TODAY)
        self.assertEqual(before, sha_tree(root / "rules"))

    def test_ledger_created_with_header_and_idempotent(self):
        root = mk_corpus(self.tmp, rules=[rule("a", tier="pinned")],
                         cases=[{"date": "2026-08-0%d" % d, "rule": "a"} for d in (1, 2, 3)])
        c = el.load_corpus(root, TODAY)
        rows, appended = el.graduate(c, TODAY)
        self.assertEqual(len(appended), 1)
        text = c.ledger_path.read_text()
        self.assertTrue(text.startswith("# Graduation ledger"))
        self.assertEqual(text.count("| a |"), 1)
        rows, appended = el.graduate(el.load_corpus(root, TODAY), TODAY)
        self.assertEqual(appended, [])
        self.assertEqual(c.ledger_path.read_text().count("| a |"), 1)
        rows, appended = el.graduate(el.load_corpus(root, TODAY), TODAY, force=True)
        self.assertEqual(len(appended), 1)
        self.assertEqual(c.ledger_path.read_text().count("| a |"), 2)

    def test_ledger_appends_when_verdict_changes(self):
        root = mk_corpus(self.tmp, rules=[rule("a", tier="hook", created="2025-01-01", never_relax="true")])
        c = el.load_corpus(root, TODAY)
        el.graduate(c, TODAY)                                   # BLOCKED
        (root / "rules" / "a.md").write_text("---\nslug: a\ntier: hook\ncreated: 2025-01-01\nnever_relax: false\n---\n")
        rows, appended = el.graduate(el.load_corpus(root, TODAY), TODAY)   # now RECOMMEND
        self.assertEqual([r["verdict"] for r in appended], ["RECOMMEND"])
        self.assertEqual(c.ledger_path.read_text().count("| a |"), 2)

    def test_example_corpus_documented_recommendations(self):
        rows = {r["rule"]: r for r in el.recommend(el.load_corpus(EXAMPLE, TODAY), TODAY)}
        self.assertEqual(rows["verify-before-send"]["verdict"], "RECOMMEND")
        self.assertEqual(rows["verify-before-send"]["direction"], "promote")
        self.assertEqual(rows["no-dash-connectors"]["verdict"], "RECOMMEND")
        self.assertEqual(rows["no-dash-connectors"]["direction"], "relax")
        self.assertEqual(rows["never-send-without-approval"]["verdict"], "BLOCKED")
        self.assertEqual(rows["one-clarifying-question"]["verdict"], "INSUFFICIENT")
        self.assertNotIn("check-calendar-first", rows)


# ------------------------------------------------------------------ replay pieces
class TestParseVerdict(unittest.TestCase):
    def test_clean(self):
        v = el.parse_verdict('{"verdict":"pass","evidence":"x","reason":"y"}')
        self.assertEqual(v["verdict"], "PASS")

    def test_fenced(self):
        v = el.parse_verdict('```json\n{"verdict":"FAIL","evidence":"x","reason":"y"}\n```')
        self.assertEqual(v["verdict"], "FAIL")

    def test_not_json(self):
        with self.assertRaises(el.JudgeParseError):
            el.parse_verdict("Looks fine to me.")

    def test_refusal(self):
        with self.assertRaises(el.JudgeRefusal):
            el.parse_verdict("I can't help with that.")

    def test_missing_keys(self):
        with self.assertRaises(el.JudgeSchemaError):
            el.parse_verdict('{"foo": 1}')

    def test_bad_verdict_value(self):
        with self.assertRaises(el.JudgeSchemaError):
            el.parse_verdict('{"verdict":"MAYBE","evidence":"x","reason":"y"}')

    def test_pass_without_evidence(self):
        with self.assertRaises(el.JudgeUnsupported):
            el.parse_verdict('{"verdict":"PASS","evidence":"  ","reason":"y"}')

    def test_non_object(self):
        with self.assertRaises(el.JudgeSchemaError):
            el.parse_verdict('[1,2]')


class TestRunAgent(unittest.TestCase):
    def _run(self, mode, timeout=2):
        os.environ["FAKE_MODE"] = mode
        try:
            return el.run_agent(FAKE, "prompt", timeout)
        finally:
            os.environ.pop("FAKE_MODE", None)

    def test_pass(self):
        self.assertIn("Monday", self._run("pass"))

    def test_timeout(self):
        with self.assertRaises(el.AgentTimeout):
            self._run("timeout", timeout=1)

    def test_nonzero(self):
        with self.assertRaises(el.AgentNonZero):
            self._run("nonzero")

    def test_empty(self):
        with self.assertRaises(el.AgentEmpty):
            self._run("empty")

    def test_not_found(self):
        with self.assertRaises(el.AgentNotFound):
            el.run_agent("definitely-not-a-real-command-xyz", "p", 2)

    def test_prompt_with_quotes_goes_through_stdin(self):
        # a shell-hostile prompt must not break the invocation
        out = el.run_agent(FAKE, "it's \"quoted\" and $HOME and `backticks`", 2)
        self.assertTrue(out.strip())


class TestReplay(TmpCorpusTest):
    def _corpus(self):
        root = mk_corpus(self.tmp, rules=[rule("no-dash")],
                         scenarios=[{"name": "no-dash", "rule": "no-dash",
                                     "expected": "no dash connectors", "prompt": "write a note"}])
        return el.load_corpus(root, TODAY)

    def _replay(self, mode, votes=1):
        os.environ["FAKE_MODE"] = mode
        try:
            return el.replay(self._corpus(), FAKE, FAKE, 2, votes, "t")
        finally:
            os.environ.pop("FAKE_MODE", None)

    def test_pass_and_records_written(self):
        results, run_dir = self._replay("pass")
        self.assertEqual(results[0]["verdict"], "PASS")
        rec = json.loads((run_dir / "no-dash.json").read_text())
        self.assertIn("agent_output", rec)
        self.assertIn("judge_output", rec)

    def test_fail(self):
        self.assertEqual(self._replay("fail")[0][0]["verdict"], "FAIL")

    def test_agent_failures_are_error_not_fail(self):
        for mode in ("timeout", "nonzero", "empty"):
            r = self._replay(mode)[0][0]
            self.assertEqual(r["verdict"], "ERROR", mode)
            self.assertIn("Agent", r["error"], mode)

    def test_judge_failures_are_error_not_pass(self):
        for mode in ("badjson", "noevidence", "missingkeys", "refuse"):
            r = self._replay(mode)[0][0]
            self.assertEqual(r["verdict"], "ERROR", mode)
            self.assertIn("Judge", r["error"], mode)

    def test_fenced_judge_output_is_parsed(self):
        self.assertEqual(self._replay("fenced")[0][0]["verdict"], "PASS")

    def test_votes_majority(self):
        r = self._replay("pass", votes=3)[0][0]
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["votes"], "3/3 PASS")

    def test_chaos_judge_always_pass_without_evidence(self):
        # every scenario must land as ERROR, none as PASS
        root = mk_corpus(self.tmp, rules=[rule("a"), rule("b")],
                         scenarios=[{"name": n, "rule": n, "expected": "x", "prompt": "p"} for n in ("a", "b")])
        os.environ["FAKE_MODE"] = "noevidence"
        try:
            results, _ = el.replay(el.load_corpus(root, TODAY), FAKE, FAKE, 2, 1, "chaos")
        finally:
            os.environ.pop("FAKE_MODE", None)
        self.assertEqual([r["verdict"] for r in results], ["ERROR", "ERROR"])


class TestReplayBlockers(TmpCorpusTest):
    def test_case_errors_do_not_block_replay(self):
        c = el.load_corpus(EXAMPLE, TODAY)            # has exactly one dangling CASE
        self.assertEqual(el.replay_blockers(c), [])

    def test_scenario_error_blocks_replay(self):
        root = mk_corpus(self.tmp, rules=[rule("a")],
                         scenarios=[{"name": "s", "rule": "ghost", "expected": "x", "prompt": "p"}])
        c = el.load_corpus(root, TODAY)
        self.assertEqual(len(el.replay_blockers(c)), 1)


class TestCalibrate(TmpCorpusTest):
    def test_echo_judge_matches_example_calibration(self):
        # the tiny real judge in fake_cmd (echo mode) should agree with all three expected verdicts
        os.environ["FAKE_MODE"] = "echo"
        try:
            c = el.load_corpus(EXAMPLE, TODAY)
            results, _ = el.calibrate(c, FAKE, 2, 1, "t")
        finally:
            os.environ.pop("FAKE_MODE", None)
            shutil.rmtree(EXAMPLE / "runs" / "t", ignore_errors=True)
        self.assertTrue(all(r["match"] for r in results), [(r["calibration"], r["verdict"]) for r in results])


# ------------------------------------------------------------------ cli + no-vault
class TestCli(TmpCorpusTest):
    def _cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "eval_loop.py"), *args],
                              capture_output=True, text=True)

    def test_check_example_exits_1_naming_dangling_case(self):
        p = self._cli("--dir", str(EXAMPLE), "--today", "2026-08-27", "check")
        self.assertEqual(p.returncode, 1)
        self.assertIn("quote-the-source", p.stderr)

    def test_score_json(self):
        p = self._cli("--dir", str(EXAMPLE), "--today", "2026-08-27", "--json", "score")
        self.assertEqual(p.returncode, 0)
        self.assertEqual(len(json.loads(p.stdout)["rules"]), 5)

    def test_missing_dir_exit_2(self):
        p = self._cli("--dir", str(Path(self.tmp) / "nope"), "check")
        self.assertEqual(p.returncode, 2)
        self.assertIn("no corpus", p.stderr)

    def test_bad_today_exit_2(self):
        p = self._cli("--dir", str(EXAMPLE), "--today", "yesterday", "check")
        self.assertEqual(p.returncode, 2)

    def test_runs_without_any_vault_present(self):
        # standalone by default: a corpus with no MEMORY.md and no memory files anywhere near it
        root = mk_corpus(self.tmp, rules=[rule("a")], cases=[{"date": "2026-08-01", "rule": "a"}])
        self.assertFalse(list(Path(self.tmp).rglob("MEMORY.md")))
        p = self._cli("--dir", str(root), "--today", "2026-08-27", "score")
        self.assertEqual(p.returncode, 0, p.stderr)


@unittest.skipUnless(os.environ.get("LIVE") == "1", "set LIVE=1 to run against the real CLI")
class LiveTests(unittest.TestCase):
    def test_calibration_against_real_judge(self):
        c = el.load_corpus(EXAMPLE, TODAY)
        judge_cmd = os.environ.get("JUDGE_CMD", el.DEFAULT_JUDGE_CMD)
        results, _ = el.calibrate(c, judge_cmd, 120, 1, "live-test")
        self.assertTrue(all(r["match"] for r in results), [(r["calibration"], r["verdict"], r["reason"]) for r in results])



if __name__ == "__main__":
    unittest.main()


class VersionTests(unittest.TestCase):
    def test_version_flag_prints_the_module_version(self):
        import subprocess, sys, pathlib
        root = pathlib.Path(__file__).resolve().parents[1]
        out = subprocess.run([sys.executable, str(root / "eval_loop.py"), "--version"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0)
        self.assertIn("agent-eval-loop 0.1.0", out.stdout + out.stderr)

