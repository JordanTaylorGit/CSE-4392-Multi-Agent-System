#!/usr/bin/env python3
"""Live monitor + HITL console for the LangGraph SeasonSwitch pipeline.

Serves a single-page dashboard over the runs/ directory:
  python3 scripts/pipeline_ui.py [--port 8000]
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
PAGE = (Path(__file__).with_name("pipeline_ui.html")).read_text()

STAGES = [
    ("generation", "Generate EP + BVA cases"),
    ("merge", "Merge + dedupe"),
    ("review_testcases", "G1 · review test cases"),
    ("build_original", "Materialize + build original"),
    ("refactor", "State-pattern refactor"),
    ("review_refactored", "G3 · review refactor"),
    ("build_refactored", "Adapt + build refactored"),
    ("finish", "Complete"),
]
GATE_ARTIFACTS = {
    "review_testcases": ["dedupe-report.md", "testcases_final.json"],
    "review_refactored": ["refactor-notes.md"],
}


def tool_env() -> dict:
    env = dict(os.environ)
    tools = Path.home() / "tools"
    jdks = sorted(tools.glob("jdk-*")) if tools.exists() else []
    mvns = sorted(tools.glob("apache-maven-*")) if tools.exists() else []
    if jdks:
        env["JAVA_HOME"] = str(jdks[-1])
        env["PATH"] = f"{jdks[-1]}/bin:{env['PATH']}"
    if mvns:
        env["PATH"] = f"{mvns[-1]}/bin:{env['PATH']}"
    return env


def load_status(rdir: Path) -> dict:
    p = rdir / "status.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def stage_states(status: dict, rdir: Path) -> list[dict]:
    """Map status.json onto the fixed stage list."""
    counts = status.get("counts") or {}
    pending = status.get("pending") or []
    pending_gate = pending[0]["gate"] if pending else None
    done = set()
    if counts.get("generation") and (rdir / "testcases_ep.json").exists():
        done.add("generation")
    if (rdir / "testcases_final.json").exists() or (rdir / "testcases_proposed.json").exists():
        done.add("merge")
    decisions = []
    hp = rdir / "hitl_decisions.json"
    if hp.exists():
        try:
            decisions = json.loads(hp.read_text())
        except Exception:
            pass
    if counts.get("build_original"):
        done |= {"review_testcases", "build_original"}
    elif any(d.get("gate") == "review_testcases" and d.get("decision") == "accept" for d in decisions):
        done.add("review_testcases")
    if counts.get("refactor"):
        done.add("refactor")
    if counts.get("build_refactored"):
        done |= {"review_refactored", "build_refactored"}
    elif any(d.get("gate") == "review_refactored" and d.get("decision") == "accept" for d in decisions):
        done.add("review_refactored")
    if status.get("status") == "complete":
        done.add("finish")

    out, met_current = [], False
    for key, label in STAGES:
        if key in done:
            state = "done"
        elif pending_gate == key:
            state = "gate"
            met_current = True
        elif not met_current:
            state = "current"
            met_current = True
        else:
            state = "pending"
        out.append({"key": key, "label": label, "state": state})
    if status.get("status") == "blocked":
        for s in reversed(out):
            if s["state"] in ("current", "gate"):
                s["state"] = "blocked"
                break
    return out


def run_detail(rdir: Path) -> dict:
    status = load_status(rdir)
    pending = status.get("pending") or []
    cases = []
    for name in ("testcases_proposed.json", "testcases_final.json"):
        p = rdir / name
        if p.exists():
            try:
                cases = json.loads(p.read_text()).get("cases", [])
            except Exception:
                pass
            break
    artifacts = {}
    if pending:
        for name in GATE_ARTIFACTS.get(pending[0]["gate"], []):
            ap = rdir / name
            if ap.exists():
                artifacts[name] = ap.read_text()[:40000]
    if (rdir / "run-report.md").exists():
        artifacts["run-report.md"] = (rdir / "run-report.md").read_text()[:40000]
    return {
        "id": rdir.name,
        "status": status.get("status", "unknown"),
        "counts": status.get("counts") or {},
        "error": status.get("error", ""),
        "pending": pending,
        "stages": stage_states(status, rdir),
        "results": status.get("results") or {},
        "cases": [{k: c.get(k) for k in ("id", "method", "unit", "partition")} for c in cases],
        "artifacts": artifacts,
        "decisions": (json.loads((rdir / "hitl_decisions.json").read_text())
                      if (rdir / "hitl_decisions.json").exists() else []),
    }


class Feed:
    """Per-run live feed: file-backed, so restarts keep history."""
    lock = threading.Lock()
    watchers: dict[str, threading.Thread] = {}
    last: dict[str, dict] = {}

    @classmethod
    def path(cls, rdir: Path) -> Path:
        return rdir / "ui-feed.log"

    @classmethod
    def emit(cls, rdir: Path, kind: str, msg: str):
        line = f"{datetime.now(timezone.utc):%H:%M:%S} [{kind}] {msg}\n"
        with cls.lock:
            with cls.path(rdir).open("a") as f:
                f.write(line)

    @classmethod
    def watch(cls, rdir: Path):
        key = rdir.name
        if key in cls.watchers:
            return
        t = threading.Thread(target=cls._loop, args=(rdir,), daemon=True)
        cls.watchers[key] = t
        t.start()

    @classmethod
    def _loop(cls, rdir: Path):
        cls.last[rdir.name] = {}
        while True:
            try:
                cls._tick(rdir)
            except Exception as e:
                cls.emit(rdir, "ERROR", f"watcher: {e}")
            time.sleep(2)

    @classmethod
    def _tick(cls, rdir: Path):
        prev = cls.last[rdir.name]
        status = load_status(rdir)
        snap = {
            "status": status.get("status"),
            "counts": dict(status.get("counts") or {}),
            "pending": [p["gate"] for p in status.get("pending") or []],
            "results": list((status.get("results") or {}).keys()),
        }
        if prev.get("status") != snap["status"]:
            if prev:
                cls.emit(rdir, "STATUS", f"run {prev['status']} -> {snap['status']}")
            else:
                cls.emit(rdir, "STATUS", f"run is {snap['status']}")
        old_counts = prev.get("counts") or {}
        for k, v in snap["counts"].items():
            if old_counts.get(k) != v:
                res = (status.get("results") or {}).get(k.replace("build_", ""), {})
                extra = f" ({res.get('tests')} tests, {res.get('percent')}% coverage)" if res else ""
                cls.emit(rdir, "STAGE", f"{k} attempt {v} finished{extra}")
        for g in snap["pending"]:
            if g not in (prev.get("pending") or []):
                cls.emit(rdir, "GATE", f"awaiting human review: {g}")
        # transcript activity
        tdir = rdir / "transcripts"
        cur = {p.name for p in tdir.glob("*.json")} if tdir.exists() else set()
        for name in sorted(cur - set(prev.get("transcripts") or [])):
            cls.emit(rdir, "MODEL", f"model request finished: {name.split('-')[0]}")
        snap["transcripts"] = cur
        if snap["status"] == "complete" and prev.get("status") != "complete" and prev:
            cls.emit(rdir, "STATUS", "run finished — run-report.md ready")
        cls.last[rdir.name] = snap


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        parts = u.path.strip("/").split("/")
        if u.path == "/" or u.path == "/index.html":
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body)
        elif u.path == "/api/runs":
            runs = []
            for d in sorted(RUNS.iterdir(), reverse=True):
                if not d.is_dir() or not (d / "status.json").exists():
                    continue
                s = load_status(d)
                runs.append({"id": d.name, "status": s.get("status", "?"),
                             "pending": [p["gate"] for p in s.get("pending") or []],
                             "counts": s.get("counts") or {}})
            self._json(runs)
        elif len(parts) == 3 and parts[:2] == ["api", "run"]:
            rdir = RUNS / parts[2]
            if not rdir.is_dir():
                return self._json({"error": "no such run"}, 404)
            self._json(run_detail(rdir))
        elif len(parts) == 3 and parts[:2] == ["api", "feed"]:
            rdir = RUNS / parts[2]
            Feed.watch(rdir)
            q = parse_qs(u.query)
            off = int(q.get("since", ["0"])[0])
            p = Feed.path(rdir)
            data = p.read_bytes() if p.exists() else b""
            self._json({"lines": data[off:].decode(errors="replace"), "offset": len(data)})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/api/decide":
            return self._json({"error": "not found"}, 404)
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        rdir = RUNS / body["run_id"]
        status = load_status(rdir)
        pending = status.get("pending") or []
        if not pending:
            return self._json({"error": "run is not awaiting a decision"}, 409)
        decision = {
            "gate": pending[0]["gate"],
            "reviewer": body["reviewer"],
            "decision": body["decision"],
            "requested_changes": body.get("requested_changes", []),
            "artifact_sha256": pending[0]["artifact_sha256"],
        }
        dfile = rdir / f".ui-decision-{int(time.time())}.json"
        dfile.write_text(json.dumps(decision))
        Feed.watch(rdir)
        Feed.emit(rdir, "DECISION",
                  f"{body['reviewer']} -> {body['decision']} on {pending[0]['gate']}"
                  + (f" ({'; '.join(body.get('requested_changes', []))})" if body.get("requested_changes") else ""))
        def resume():
            proc = subprocess.Popen(
                ["uv", "run", "python", "-m", "harness", "resume",
                 "--run", str(rdir), "--decision", str(dfile)],
                cwd=ROOT, env=tool_env(),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                Feed.emit(rdir, "HARNESS", line.rstrip()[:300])
            Feed.emit(rdir, "HARNESS", f"resume exited rc={proc.wait()}")
        threading.Thread(target=resume, daemon=True).start()
        self._json({"ok": True})


if __name__ == "__main__":
    import sys
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8000
    print(f"pipeline UI: http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
