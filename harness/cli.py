"""Start, inspect, and resume a run without storing a provider client in state."""
from __future__ import annotations

import argparse
import fcntl
import json
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from jsonschema import ValidationError
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from harness.graph import build_graph
from harness.model import create_model
from harness.stages import Stages
from harness.workspace import RunWorkspace

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def run_lock(run):
    """Do not let two CLI processes mutate the same run at once."""
    with (run.directory / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("This run is already active in another process") from exc
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def project_status(run, snapshot):
    values = dict(snapshot.values)
    pending = [i.value for task in snapshot.tasks for i in task.interrupts]
    status = "waiting_for_human" if pending else values.get("status", "in_progress")
    report = {**values, "status": status, "pending": pending, "next_nodes": list(snapshot.next)}
    run.save("status.json", report)
    lines = ["# Run state", "", f"- run_id: `{run.directory.name}`", f"- status: `{status}`",
             f"- next_nodes: `{', '.join(snapshot.next) or 'none'}`", "",
             "SQLite checkpoints are the resume source; this file is a readable projection.", "",
             "## Stage attempts", "", "| Stage | Attempts |", "| --- | ---: |"]
    lines += [f"| {stage} | {count} |" for stage, count in values.get("counts", {}).items()]
    if values.get("error"):
        lines += ["", "## Blocked", "", values["error"]]
    if pending:
        lines += ["", "## Pending human review", "", "```json", json.dumps(pending[0], indent=2), "```"]
    (run.directory / "STATE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    results = values.get("results", {})
    summary = ["# Pipeline run report", "", f"Status: **{status}**.", "",
               "| Target | Tests | Passed | Covered | Missed | Branch % | Excluded main branches |",
               "| --- | ---: | --- | ---: | ---: | ---: | ---: |"]
    coverage = []
    for target, result in results.items():
        pct = result.get("percent")
        displayed = f"{pct:.4f}" if pct is not None else "unavailable"
        summary.append(f"| {target} | {result['tests']} | {result['passed']} | {result['covered']} | "
                       f"{result['missed']} | {displayed} | {result['excluded_main_branches']} |")
        coverage.append(f"{target} {result['covered']} {result['missed']} {displayed}")
    summary += ["", "Coverage counts method-level JaCoCo branches once and excludes main(), following P3's scope.",
                "The 100% gate requires zero missed branches and a nonempty passing suite; rounded percentages do not decide it.",
                "EP and BVA are separate parallel graph nodes and join before review.",
                "An Ollama server may queue concurrent requests depending on its configuration.",
                "Approved Java tests are reused unchanged against the refactored Maven profile.",
                "Human approvals, model transcripts, source diffs, and build reports are stored in this run directory."]
    if values.get("error"):
        summary += ["", "Blocked: " + values["error"]]
    (run.directory / "run-report.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    (run.directory / "coverage.txt").write_text("\n".join(coverage) + "\n", encoding="utf-8")
    return report


def drive(graph, run, value, config):
    for _ in graph.stream(value, config, stream_mode="values"):
        project_status(run, graph.get_state(config))
    return project_status(run, graph.get_state(config))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start", help="Start a new live Ollama run")
    start.add_argument("--project", default="seasonswitch")
    for name in ("status", "resume"):
        command = commands.add_parser(name)
        command.add_argument("--run", type=Path, required=True)
        if name == "resume":
            command.add_argument("--decision", type=Path,
                                 help="JSON containing an actual human review decision")
    args = parser.parse_args(argv)
    try:
        if args.command == "start":
            run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:6]
            run = RunWorkspace.create(ROOT, ROOT / "runs" / run_id, args.project)
            print(f"Run directory: {run.directory}", flush=True)
        else:
            run = RunWorkspace(args.run)
        config = {"configurable": {"thread_id": run.directory.name}, "recursion_limit": 300}
        with run_lock(run), SqliteSaver.from_conn_string(str(run.directory / "checkpoints.sqlite")) as saver:
            model = create_model()
            graph = build_graph(model=model, run=run, checkpointer=saver)
            snapshot = graph.get_state(config)
            if args.command == "status":
                status = project_status(run, snapshot)
            else:
                value = {} if args.command == "start" else None
                if args.command == "resume":
                    pending = [i.value for task in snapshot.tasks for i in task.interrupts]
                    if pending:
                        if args.decision is None:
                            raise ValueError("This run is awaiting human review; provide --decision decision.json")
                        decision = json.loads(args.decision.read_text())
                        if not isinstance(decision, dict):
                            raise ValueError("A decision must be a JSON object")
                        decision.setdefault("gate", pending[0]["gate"])
                        decision.setdefault("timestamp_utc", datetime.now(UTC).isoformat(timespec="seconds"))
                        # Invalid CLI input must leave the graph paused, rather than consume the interrupt.
                        stages = Stages(model, run, None)
                        payload = stages.review_payload(pending[0]["gate"], snapshot.values)
                        stages.validate_decision(payload, decision)
                        value = Command(resume=decision)
                    elif args.decision:
                        raise ValueError("There is no pending human review for this run")
                    elif not snapshot.next:
                        raise ValueError("Run has ended; inspect status or start a new run")
                status = drive(graph, run, value, config)
        print(json.dumps({"status": status["status"], "run": str(run.directory),
                          "pending": status["pending"], "error": status.get("error", "")}, indent=2))
        return 1 if status["status"] == "blocked" else 0
    except (OSError, ValueError, ValidationError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
