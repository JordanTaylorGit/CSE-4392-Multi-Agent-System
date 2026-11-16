"""Explicit LangGraph control flow for assignment steps 1–12."""
from __future__ import annotations

from copy import deepcopy
from typing import TypedDict

from langgraph.errors import GraphInterrupt
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from harness.build import MavenRunner
from harness.stages import Stages
from harness.workspace import RunWorkspace, digest


class State(TypedDict, total=False):
    status: str
    error: str
    counts: dict[str, int]
    feedback: str
    ep_error: str
    bva_error: str
    generation_failed: bool
    build: dict
    results: dict[str, dict]
    target: str
    pending_gap: dict
    review_fingerprint: str
    review_index: int
    after_review: str
    decision: str
    tests_digest: str
    cases_digest: str
    minimum_tests: int
    approved_refactor_digest: str
    compiled: bool


def increment(state: State, key: str, *, bounded=True) -> tuple[dict, int]:
    counts = dict(state.get("counts", {}))
    count = counts.get(key, 0) + 1
    if bounded and count > 5:
        raise ValueError(f"{key}: five-attempt limit reached; human intervention required")
    counts[key] = count
    return counts, count


def build_graph(*, model, run: RunWorkspace, checkpointer, build_runner=None):
    """Inject the model, build executor, and durable checkpoint implementation."""
    stages = Stages(model, run, build_runner or MavenRunner())

    def guarded(name, function):
        def node(state: State):
            try:
                return function(state)
            except GraphInterrupt:
                raise
            except Exception as exc:  # noqa: BLE001 -- provider-neutral stage failure boundary
                return {"status": "blocked", "error": f"{name}: {exc}"}
        return node

    def prepare_generation(state):
        counts, _ = increment(state, "generation")
        return {"counts": counts, "status": "in_progress", "error": "", "target": "original",
                "ep_error": "", "bva_error": "", "generation_failed": False, "pending_gap": {}}

    def generator(method):
        def node(state):
            try:
                stages.generate(method, state)
                return {f"{method.lower()}_error": ""}
            except Exception as exc:  # noqa: BLE001 -- join must receive both provider outcomes
                # Separate state keys let both parallel nodes fail without an update conflict.
                return {f"{method.lower()}_error": str(exc)}
        return node

    def merge(state):
        errors = [state.get("ep_error"), state.get("bva_error")]
        if any(errors):
            return {"generation_failed": True, "feedback": "\n".join(e for e in errors if e)}
        stages.merge()
        return {**stages.prepare_review("review_testcases", state), "after_review": "materialize"}

    def review(gate):
        def node(state):
            payload = stages.review_payload(gate, state)
            decision = interrupt(payload)
            stages.record_decision(payload, decision, state)
            updates = {"decision": decision["decision"],
                       "feedback": "\n".join(decision["requested_changes"])}
            if gate == "review_refactored" and decision["decision"] == "accept":
                updates["approved_refactor_digest"] = run.source_digest("refactored")
            return updates
        return node

    def materialize(state):
        stages.materialize()
        return {"tests_digest": run.source_digest("test"),
                "cases_digest": digest(run.directory / "testcases_final.json"),
                "minimum_tests": len(run.json("testcases_final.json")["cases"])}

    def build(target):
        def node(state):
            if run.source_digest("test") != state["tests_digest"]:
                raise ValueError("Test sources changed outside the approved workflow")
            name = "testcases_final.json" if target == "original" else "testcases_refactored.json"
            if digest(run.directory / name) != state["cases_digest"]:
                raise ValueError("Approved case expectations changed")
            if target == "refactored" and run.source_digest(target) != state["approved_refactor_digest"]:
                raise ValueError("Refactored source changed after G3 approval")
            counts, attempt = increment(state, f"build_{target}", bounded=False)
            result = stages.builder(run, target, attempt)
            if result["passed"] and result["tests"] < state["minimum_tests"]:
                raise ValueError("Passing suite executed fewer tests than the approved set")
            return {"counts": counts, "build": result, "target": target,
                    "minimum_tests": max(state["minimum_tests"], result["tests"]),
                    "results": {**state.get("results", {}), target: result}}
        return node

    def repair(target):
        def node(state):
            counts, attempt = increment(state, f"repair_{target}")
            stages.change_source(f"repair_{target}", target, state, attempt)
            updates = {"counts": counts}
            if target == "refactored":
                compiled = stages.builder.compile(run, f"repair-{attempt}")
                updates.update(compiled=compiled["passed"], feedback=compiled["log"],
                               after_review="build_refactored")
                if compiled["passed"]:
                    updates.update(stages.prepare_review("review_refactored", state))
            return updates
        return node

    def refactor(state):
        counts, attempt = increment(state, "refactor")
        stages.change_source("refactor", "refactored", state, attempt)
        result = stages.builder.compile(run, attempt)
        updates = {"counts": counts, "compiled": result["passed"], "feedback": result["log"],
                   "target": "refactored", "after_review": "adapt"}
        if result["passed"]:
            updates.update(stages.prepare_review("review_refactored", state))
        return updates

    def adapt(state):
        adapted = deepcopy(run.json("testcases_final.json"))
        adapted["target"] = "refactored"
        for case in adapted["cases"]:
            case["target"] = "refactored"
        run.save("testcases_refactored.json", adapted)
        # The Maven profile changes the source root; assertions and expected values stay intact.
        return {"cases_digest": digest(run.directory / "testcases_refactored.json")}

    def gap(target):
        def node(state):
            counts, attempt = increment(state, f"gap_{target}")
            proposal = stages.propose_gap(target, state, attempt)
            updates = {"counts": counts, "pending_gap": proposal, "after_review": "apply_gap",
                       "target": target}
            gate = "review_testcases" if target == "original" else "review_refactored"
            updates.update(stages.prepare_review(gate, {**state, **updates}))
            return updates
        return node

    def apply_gap(state):
        stages.apply_gap(state["target"], state)
        name = "testcases_final.json" if state["target"] == "original" else "testcases_refactored.json"
        return {"tests_digest": run.source_digest("test"), "cases_digest": digest(run.directory / name),
                "minimum_tests": state["minimum_tests"] + len(state["pending_gap"]["cases"]),
                "pending_gap": {}}

    def finish(state):
        if not all(state["results"][target]["complete"] for target in ("original", "refactored")):
            raise ValueError("Both targets must have passing tests and complete measured branch coverage")
        return {"status": "complete", "error": ""}

    graph = StateGraph(State)
    nodes = {"prepare_generation": prepare_generation, "merge": merge,
             "review_testcases": review("review_testcases"), "materialize": materialize,
             "build_original": build("original"), "repair_original": repair("original"),
             "gap_original": gap("original"), "refactor": refactor,
             "review_refactored": review("review_refactored"), "adapt": adapt,
             "build_refactored": build("refactored"), "repair_refactored": repair("refactored"),
             "gap_refactored": gap("refactored"), "apply_gap": apply_gap, "finish": finish}
    for name, function in nodes.items():
        graph.add_node(name, guarded(name, function))
    graph.add_node("ep", generator("EP"))
    graph.add_node("bva", generator("BVA"))

    def connect(source, choose, destinations):
        graph.add_conditional_edges(source, lambda s: END if s.get("status") == "blocked" else choose(s),
                                    {name: name for name in [*destinations, END]})

    graph.add_edge(START, "prepare_generation")
    connect("prepare_generation", lambda _: ["ep", "bva"], ["ep", "bva"])
    graph.add_edge(["ep", "bva"], "merge")
    connect("merge", lambda s: "prepare_generation" if s.get("generation_failed") else "review_testcases",
            ["prepare_generation", "review_testcases"])
    connect("review_testcases", lambda s: ("gap_original" if s.get("pending_gap") else "prepare_generation")
            if s["decision"] == "request_changes" else s["after_review"],
            ["gap_original", "prepare_generation", "apply_gap", "materialize"])
    connect("materialize", lambda _: "build_original", ["build_original"])
    for target, next_stage in (("original", "refactor"), ("refactored", "finish")):
        connect(f"build_{target}", lambda s, t=target, n=next_stage: n if s["build"]["complete"]
                else (f"gap_{t}" if s["build"]["passed"] else f"repair_{t}"),
                [next_stage, f"gap_{target}", f"repair_{target}"])
        gate = "review_testcases" if target == "original" else "review_refactored"
        connect(f"gap_{target}", lambda _, g=gate: g, [gate])
    connect("repair_original", lambda _: "build_original", ["build_original"])
    connect("repair_refactored", lambda s: "review_refactored" if s["compiled"] else "repair_refactored",
            ["review_refactored", "repair_refactored"])
    connect("refactor", lambda s: "review_refactored" if s["compiled"] else "refactor",
            ["review_refactored", "refactor"])
    connect("review_refactored", lambda s: ("gap_refactored" if s.get("pending_gap") else "refactor")
            if s["decision"] == "request_changes" else s["after_review"],
            ["gap_refactored", "refactor", "adapt", "apply_gap", "build_refactored"])
    connect("adapt", lambda _: "build_refactored", ["build_refactored"])
    connect("apply_gap", lambda s: f"build_{s['target']}", ["build_original", "build_refactored"])
    graph.add_edge("finish", END)
    return graph.compile(checkpointer=checkpointer)
