#!/usr/bin/env python3
"""Demo helper: park N runs at the pipeline's N stopping points.

Usage: python3 scripts/demo_park.py RUN_G1 RUN_G3 RUN_DONE
  RUN_G1    left awaiting review_testcases (nothing done)
  RUN_G3    G1 auto-accepted, left awaiting review_refactored
  RUN_DONE  G1 and G3 auto-accepted, runs to completion
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
ACCEPT_AT = {"review_testcases": "review_refactored", "review_refactored": "complete"}


def env():
    e = dict(__import__("os").environ)
    tools = Path.home() / "tools"
    jdks = sorted(tools.glob("jdk-*")); mvns = sorted(tools.glob("apache-maven-*"))
    if jdks:
        e["JAVA_HOME"] = str(jdks[-1]); e["PATH"] = f"{jdks[-1]}/bin:{e['PATH']}"
    if mvns:
        e["PATH"] = f"{mvns[-1]}/bin:{e['PATH']}"
    return e


def status(rid):
    p = RUNS / rid / "status.json"
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def main():
    park_g1, park_g3, park_done = sys.argv[1:4]
    targets = {park_g1: "review_testcases", park_g3: "review_refactored", park_done: "complete"}
    E = env()
    done_flags = set()
    while len(done_flags) < 3:
        for rid, target in targets.items():
            if rid in done_flags:
                continue
            s = status(rid)
            st = s.get("status")
            if target == "review_testcases":
                if st == "waiting_for_human":
                    done_flags.add(rid)  # parked at G1 — leave it
                continue
            if st == "complete" and target == "complete":
                done_flags.add(rid)
                continue
            pending = s.get("pending") or []
            if st == "waiting_for_human" and pending:
                gate = pending[0]["gate"]
                if gate == target:
                    done_flags.add(rid)  # parked at requested gate
                    continue
                dfile = RUNS / rid / f".park-decision-{int(time.time())}.json"
                dfile.write_text(json.dumps({
                    "gate": gate, "reviewer": "auto-park (devin)",
                    "decision": "accept", "requested_changes": [],
                    "artifact_sha256": pending[0]["artifact_sha256"]}))
                subprocess.Popen(
                    ["uv", "run", "python", "-m", "harness", "resume",
                     "--run", str(RUNS / rid), "--decision", str(dfile)],
                    cwd=ROOT, env=E, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(5)
        time.sleep(10)
    print("all parked")


if __name__ == "__main__":
    main()
