#!/usr/bin/env python3
"""A stand-in for both the agent and the judge in tests. Behavior is chosen by $FAKE_MODE.

The judge prompt always contains the fence `<<<OUTPUT`, the agent prompt never does, so one
script can tell which role it is playing from stdin alone.

    FAKE_MODE      as agent                  as judge
    pass           prints clean text          {"verdict":"PASS", evidence quoted}
    fail           prints text with a dash    {"verdict":"FAIL", ...}
    timeout        sleeps past the timeout    (same)
    empty          prints nothing             (n/a: judge path never sees empty agent output)
    nonzero        exits 3                    exits 3
    badjson        (agent: pass)              prints prose, not JSON
    fenced         (agent: pass)              PASS inside a ```json fence
    noevidence     (agent: pass)              PASS with evidence ""
    missingkeys    (agent: pass)              {"foo": 1}
    refuse         (agent: pass)              "I can't help with that."
    echo           (agent: pass)              FAIL if OUTPUT contains an em dash, else PASS
                                              (a tiny real judge for the chaos and calibration tests)
"""
import json
import os
import sys
import time

mode = os.environ.get("FAKE_MODE", "pass")
prompt = sys.stdin.read()
is_judge = "<<<OUTPUT" in prompt

if mode == "timeout":
    time.sleep(5)
    sys.exit(0)
if mode == "nonzero":
    print("boom", file=sys.stderr)
    sys.exit(3)

if not is_judge:
    if mode == "empty":
        sys.exit(0)
    if mode == "fail":
        print("Report ships Monday — read it before planning.")
    else:
        print("Report ships Monday. Read it before planning.")
    sys.exit(0)

# judge role
def out(obj):
    print(json.dumps(obj))

if mode == "pass":
    out({"verdict": "PASS", "evidence": "Report ships Monday.", "reason": "no dash connectors"})
elif mode == "fail":
    out({"verdict": "FAIL", "evidence": "—", "reason": "em dash joins clauses"})
elif mode == "badjson":
    print("The output looks fine to me, PASS.")
elif mode == "fenced":
    print("```json\n" + json.dumps({"verdict": "PASS", "evidence": "Report ships Monday.",
                                    "reason": "fenced but valid"}) + "\n```")
elif mode == "noevidence":
    out({"verdict": "PASS", "evidence": "", "reason": "trust me"})
elif mode == "missingkeys":
    out({"foo": 1})
elif mode == "refuse":
    print("I can't help with that.")
elif mode == "echo":
    body = prompt.split("<<<OUTPUT", 1)[1].split("OUTPUT>>>", 1)[0]
    if "—" in body or "–" in body or " -- " in body:
        out({"verdict": "FAIL", "evidence": body.strip().splitlines()[0][:60], "reason": "dash connector present"})
    else:
        out({"verdict": "PASS", "evidence": body.strip().splitlines()[0][:60], "reason": "no dash connectors"})
else:
    print(f"unknown FAKE_MODE {mode}", file=sys.stderr)
    sys.exit(4)
