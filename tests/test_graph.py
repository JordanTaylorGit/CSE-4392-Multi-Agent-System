import json
from pathlib import Path
from threading import Barrier

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from harness.graph import build_graph
from harness.workspace import RunWorkspace

ROOT = Path(__file__).resolve().parents[1]
CONFIG = {"configurable": {"thread_id": "test"}, "recursion_limit": 300}


def case(method, target="original"):
    return {"id": f"{method}-01", "method": method, "target": target,
            "unit": "off" if method == "EP" else "timerOff",
            "setup": {"state": "OFF" if method == "EP" else "COOL", "room.temp": 68},
            "inputs": {}, "expected": {"ac.isOn": False},
            "partition": "fixture", "rationale": "Control-flow test fixture only"}


class FakeBuilder:
    def __init__(self, outcomes=()):
        self.outcomes = list(outcomes)
        self.targets = []

    def compile(self, run, attempt):
        return {"passed": True, "log": "Fixture compile"}

    def __call__(self, run, target, attempt):
        self.targets.append(target)
        passed, complete = self.outcomes.pop(0) if self.outcomes else (True, True)
        name = "testcases_final.json" if target == "original" else "testcases_refactored.json"
        return {"passed": passed, "complete": complete, "tests": len(run.json(name)["cases"]),
                "covered": 2 if complete else 1, "missed": 0 if complete else 1,
                "percent": 100 if complete else 50, "excluded_main_branches": 8,
                "log": "Fixture build", "report_dir": str(run.directory)}


class FakeModel:
    def __init__(self, run, barrier=None):
        self.run = run
        self.calls = []
        self.barrier = barrier

    def respond(self, messages):
        request = json.loads(messages[1].content)
        stage = request["stage"]
        self.calls.append(stage)
        if stage in {"ep", "bva"}:
            if self.barrier:
                self.barrier.wait(timeout=5)
            answer = {"generated_by": f"{stage}-tests", "target": "original",
                      "cases": [case(stage.upper())]}
        elif stage.startswith("gap_"):
            target = stage.removeprefix("gap_")
            extra = case("GAP", target)
            extra["setup"] = {"state": "HEAT", "room.temp": 76}
            answer = {"cases": [extra], "notes": "Fixture additional test",
                      "files": [{"path": f"java/src/test/java/Extra{target}Test.java",
                                 "content": f"class Extra{target}Test {{}}"}]}
        else:
            target = "original" if stage == "repair_original" else "refactored"
            original = next(iter(self.run.source_files("original").values()))
            answer = {"files": [{"path": f"java/src/{target}/java/cse4392/SeasonSwitch.java",
                                 "content": original}], "notes": "Fixture transition matrix"}
        return AIMessage(content=json.dumps(answer))


def setup(tmp_path, outcomes=(), barrier=None, checkpointer=None):
    run = RunWorkspace.create(ROOT, tmp_path / "run", "seasonswitch")
    model = FakeModel(run, barrier)
    builder = FakeBuilder(outcomes)
    graph = build_graph(model=RunnableLambda(model.respond), run=run,
                        checkpointer=checkpointer or InMemorySaver(), build_runner=builder)
    return run, model, builder, graph


def decide(result, decision="accept"):
    pending = result["__interrupt__"][0].value
    return Command(resume={"gate": pending["gate"], "reviewer": "TEST FIXTURE",
                           "decision": decision,
                           "requested_changes": [] if decision == "accept" else ["Fixture revision"],
                           "artifact_sha256": pending["artifact_sha256"],
                           "timestamp_utc": "2026-11-16T12:00:00Z"})


def test_parallel_generation_stops_at_both_human_gates(tmp_path):
    run, model, builder, graph = setup(tmp_path, barrier=Barrier(2))
    first = graph.invoke({}, CONFIG)
    assert first["__interrupt__"][0].value["gate"] == "review_testcases"
    assert builder.targets == []
    second = graph.invoke(decide(first), CONFIG)
    assert second["__interrupt__"][0].value["gate"] == "review_refactored"
    assert builder.targets == ["original"]
    tests_before = run.source_files("test")
    done = graph.invoke(decide(second), CONFIG)
    assert done["status"] == "complete"
    assert builder.targets == ["original", "refactored"]
    assert run.source_files("test") == tests_before
    assert len(run.json("hitl_decisions.json")) == 2
    assert model.calls.count("ep") == model.calls.count("bva") == 1


def test_five_rejections_stop_without_sixth_generation(tmp_path):
    _, model, builder, graph = setup(tmp_path)
    result = graph.invoke({}, CONFIG)
    for _ in range(5):
        result = graph.invoke(decide(result, "request_changes"), CONFIG)
    assert result["status"] == "blocked"
    assert model.calls.count("ep") == 5
    assert builder.targets == []


def test_stale_human_approval_cannot_release_changed_cases(tmp_path):
    run, _, builder, graph = setup(tmp_path)
    result = graph.invoke({}, CONFIG)
    cases = run.json("testcases_final.json")
    cases["cases"][0]["expected"] = {"ac.isOn": True}
    run.save("testcases_final.json", cases)
    blocked = graph.invoke(decide(result), CONFIG)
    assert blocked["status"] == "blocked"
    assert "changed" in blocked["error"]
    assert builder.targets == []


def test_sqlite_resume_uses_checkpoint_without_regenerating_cases(tmp_path):
    database = str(tmp_path / "checkpoints.sqlite")
    with SqliteSaver.from_conn_string(database) as saver:
        run, model, builder, graph = setup(tmp_path, checkpointer=saver)
        first = graph.invoke({}, CONFIG)
    with SqliteSaver.from_conn_string(database) as saver:
        graph = build_graph(model=RunnableLambda(model.respond), run=RunWorkspace(run.directory),
                            checkpointer=saver, build_runner=builder)
        second = graph.invoke(decide(first), CONFIG)
    assert second["__interrupt__"][0].value["gate"] == "review_refactored"
    assert model.calls.count("ep") == model.calls.count("bva") == 1


def test_failed_tests_exhaust_repair_budget_without_refactoring(tmp_path):
    _, model, builder, graph = setup(tmp_path, outcomes=[(False, False)] * 6)
    first = graph.invoke({}, CONFIG)
    result = graph.invoke(decide(first), CONFIG)
    assert result["status"] == "blocked"
    assert model.calls.count("repair_original") == 5
    assert "refactor" not in model.calls
    assert builder.targets == ["original"] * 6


@pytest.mark.parametrize("target", ["original", "refactored"])
def test_coverage_gaps_add_tests_only_after_human_review(tmp_path, target):
    outcomes = [(True, False), (True, True)] if target == "original" else [(True, True), (True, False)]
    run, model, _, graph = setup(tmp_path, outcomes=outcomes)
    first = graph.invoke({}, CONFIG)
    result = graph.invoke(decide(first), CONFIG)
    if target == "refactored":
        result = graph.invoke(decide(result), CONFIG)
    assert f"gap_{target}" in model.calls
    assert not any("Extra" in path for path in run.source_files("test"))
    result = graph.invoke(decide(result), CONFIG)
    assert any("Extra" in path for path in run.source_files("test"))
    if "__interrupt__" in result:
        result = graph.invoke(decide(result), CONFIG)
    assert result["status"] == "complete", result.get("error")
