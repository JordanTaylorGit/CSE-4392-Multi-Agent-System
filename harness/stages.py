"""Adapters from graph stages to team skills, helpers, and run artifacts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, validate

from harness.model import SkillClient
from harness.workspace import RunWorkspace, digest

SOURCE_RESPONSE = {
    "type": "object", "required": ["files", "notes"], "additionalProperties": False,
    "properties": {
        "files": {"type": "array", "minItems": 1, "items": {
            "type": "object", "required": ["path", "content"], "additionalProperties": False,
            "properties": {"path": {"type": "string"},
                           "content": {"type": "string", "minLength": 1}}}},
        "notes": {"type": "string", "minLength": 1},
    },
}


class Stages:
    def __init__(self, model, run: RunWorkspace, builder):
        self.run = run
        self.model = SkillClient(model, run.directory / "transcripts")
        self.builder = builder
        schemas = run.workspace / "schemas"
        self.case_schema = json.loads((schemas / "testcase.schema.json").read_text())
        self.set_schema = json.loads((schemas / "testcase-set.schema.json").read_text())
        self.set_schema["properties"]["cases"]["items"] = self.case_schema
        self.decision_validator = Draft202012Validator(
            json.loads((schemas / "hitl_decision.schema.json").read_text()),
            format_checker=FormatChecker())

    def prompt(self, name: str) -> str:
        return (self.run.workspace / ".agents" / name / "SKILL.md").read_text()

    def context(self, state: dict) -> dict:
        vocabulary = self.run.profile_path.parent / "JUNIT_CASE_FORMAT.md"
        return {"profile": self.run.profile, "original": self.run.source_files("original"),
                "refactored": self.run.source_files("refactored"),
                "tests": self.run.source_files("test"),
                "case_vocabulary": vocabulary.read_text() if vocabulary.exists() else "",
                "feedback": state.get("feedback", "")}

    def generate(self, method: str, state: dict) -> dict:
        result = self.model.request(method.lower(), self.prompt(f"{method.lower()}-tests"),
                                    "Generate the original-target case set using this schema. "
                                    "Use only the documented project adapter vocabulary.",
                                    {**self.context(state), "schema": self.set_schema})
        validate(result, self.set_schema)
        if result["target"] != "original" or any(
            c["method"] != method or c["target"] != "original" for c in result["cases"]
        ):
            raise ValueError(f"{method} generator returned the wrong method or target")
        self.run.save(f"testcases_{method.lower()}.json", result)
        return result

    def merge(self):
        r = self.run.directory
        self.run.helper("merge_cases", "--profile", self.run.profile_path,
                        "--ep", r / "testcases_ep.json", "--bva", r / "testcases_bva.json",
                        "--out", r / "testcases_final.json", "--report", r / "dedupe-report.md")

    def cases_path(self, state: dict, target="original") -> Path:
        if state.get("pending_gap"):
            return self.run.directory / "testcases_proposed.json"
        name = "testcases_final.json" if target == "original" else "testcases_refactored.json"
        return self.run.directory / name

    def fingerprint(self, gate: str, state: dict) -> str:
        if gate == "review_testcases":
            content = {"cases": self.cases_path(state).read_text(),
                       "report": (self.run.directory / "dedupe-report.md").read_text(),
                       "source": self.run.source_files("original")}
        else:
            content = {"sources": self.run.source_files("refactored"),
                       "notes": (self.run.directory / "refactor-notes.md").read_text()}
            # Bind both the proposed case revision and its approved base to G3.
            for name in ("testcases_final.json", "testcases_refactored.json", "testcases_proposed.json"):
                path = self.run.directory / name
                if path.exists():
                    content[name] = path.read_text()
        content["tests"] = self.run.source_files("test")
        content["pending_gap"] = state.get("pending_gap")
        return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()

    def prepare_review(self, gate: str, state: dict) -> dict:
        if gate == "review_testcases":
            self.run.helper("review_cases", "prepare", "--cases", self.cases_path(state),
                            "--report", self.run.directory / "dedupe-report.md")
        history = self.run.json("hitl_decisions.json") if (
            self.run.directory / "hitl_decisions.json").exists() else []
        return {"review_fingerprint": self.fingerprint(gate, state), "review_index": len(history)}

    def review_payload(self, gate: str, state: dict) -> dict:
        if self.fingerprint(gate, state) != state["review_fingerprint"]:
            raise ValueError("Reviewed artifacts changed; start a new review instead of approving stale data")
        artifact_hash = digest(self.cases_path(state)) if gate == "review_testcases" else state["review_fingerprint"]
        cases = self.cases_path(state, "original" if gate == "review_testcases" else "refactored")
        if not cases.exists():
            cases = self.run.directory / "testcases_final.json"
        return {"gate": gate, "artifact_sha256": artifact_hash,
                "run_dir": str(self.run.directory),
                "cases": str(cases),
                "sources": str(self.run.workspace / "java/src"),
                "notes": str(self.run.directory / ("dedupe-report.md" if gate == "review_testcases" else "refactor-notes.md")),
                "proposed_tests": state.get("pending_gap", {}).get("files", []),
                "instruction": "Review the artifacts, source diff, and any proposed tests. "
                               "Supply reviewer, decision, requested_changes, and this artifact_sha256."}

    def validate_decision(self, payload: dict, decision: dict):
        self.decision_validator.validate(decision)
        if decision["gate"] != payload["gate"] or decision.get("artifact_sha256") != payload["artifact_sha256"]:
            raise ValueError("Decision does not identify the current gate and reviewed artifact")
        if not decision["reviewer"].strip():
            raise ValueError("A human reviewer must be named")
        changes = decision["requested_changes"]
        if (decision["decision"] == "accept" and changes) or (
            decision["decision"] == "request_changes" and (not changes or any(not c.strip() for c in changes))
        ):
            raise ValueError("Acceptance has no requested changes; rejection requires nonempty changes")
    def record_decision(self, payload: dict, decision: dict, state: dict):
        self.validate_decision(payload, decision)
        self.review_payload(payload["gate"], state)  # Recheck after the interrupt resumes.
        history = self.run.json("hitl_decisions.json") if (
            self.run.directory / "hitl_decisions.json").exists() else []
        index = state["review_index"]
        if len(history) == index:
            self.run.save("hitl_decisions.json", [*history, decision])
        elif len(history) != index + 1 or history[index] != decision:
            raise ValueError("Review history changed concurrently")
        if decision["decision"] == "accept" and payload["gate"] == "review_testcases":
            self.run.helper("review_cases", "check", "--cases", self.cases_path(state),
                            "--report", self.run.directory / "dedupe-report.md",
                            "--log", self.run.directory / "hitl_decisions.json")

    def materialize(self):
        self.run.helper("materialize_junit", "--profile", self.run.profile_path,
                        "--cases", self.run.directory / "testcases_final.json",
                        "--report", self.run.directory / "dedupe-report.md",
                        "--log", self.run.directory / "hitl_decisions.json",
                        "--out", self.run.workspace / self.run.profile["test_root"] / "GeneratedPipelineTest.java")

    def change_source(self, stage: str, target: str, state: dict, attempt: int):
        task = ("Refactor into the State pattern; preserve behavior and compatibility with ALL supplied "
                "tests. Return the complete refactored Java files under java/src/refactored/java, "
                "and notes with the state/action/temperature transition matrix. "
                if stage == "refactor" else
                "Repair production Java sources using the failure evidence. Do not change tests, "
                "expected results, or build configuration. ")
        task += "Return JSON matching the response_schema; paths are repository-relative."
        context = {**self.context(state), "failure": state.get("build", {}),
                   "response_schema": SOURCE_RESPONSE}
        if stage == "refactor":
            self.run.save(f"prompts/refactor-v{attempt}.json", {"skill": self.prompt("refactor-state"),
                                                              "task": task, "context": context})
        result = self.model.request(stage, self.prompt("refactor-state" if stage == "refactor" else "testgen"),
                                    task, context)
        validate(result, SOURCE_RESPONSE)
        self.run.write_sources(result["files"], target, replace_tree=stage == "refactor",
                               reason=f"{stage} attempt {attempt}")
        if target == "refactored":
            with (self.run.directory / "refactor-notes.md").open(
                "w" if stage == "refactor" else "a", encoding="utf-8"
            ) as notes:
                notes.write(result["notes"] + "\n")

    def propose_gap(self, target: str, state: dict, attempt: int) -> dict:
        schema = {**SOURCE_RESPONSE, "required": ["files", "notes", "cases"],
                  "properties": {**SOURCE_RESPONSE["properties"],
                                 "cases": {"type": "array", "minItems": 1, "items": self.case_schema}}}
        report = Path(state["build"]["report_dir"]) / "jacoco.xml"
        result = self.model.request(f"gap_{target}", self.prompt("testgen"),
            "Add GAP cases and NEW JUnit test files for uncovered branches. Never replace existing "
            "tests, repeat an existing case ID, weaken assertions, or change production sources. "
            "Each new file name must end in Test.java. For callbacks outside the initial profile, "
            "use the method name from the coverage report as the unit. Match response_schema.",
            {**self.context(state), "target": target, "attempt": attempt,
             "approved_cases": self.run.json("testcases_final.json" if target == "original" else "testcases_refactored.json"),
             "coverage": report.read_text() if report.exists() else state["build"],
             "response_schema": schema})
        validate(result, schema)
        existing = self.run.json("testcases_final.json" if target == "original" else "testcases_refactored.json")
        ids = {c["id"] for c in existing["cases"]}
        keys = self.run.profile["dedupe_key"]
        fingerprints = {json.dumps([c[k] for k in keys], sort_keys=True) for c in existing["cases"]}
        for case in result["cases"]:
            key = json.dumps([case[k] for k in keys], sort_keys=True)
            if case["target"] != target or case["method"] != "GAP" or case["id"] in ids or key in fingerprints:
                raise ValueError("GAP cases must be new, unique, and match the current target")
            ids.add(case["id"])
            fingerprints.add(key)
        self.run.validate_sources(result["files"], "test", append_only=True)
        if any(not item["path"].endswith("Test.java") for item in result["files"]):
            raise ValueError("Supplemental Java test filenames must end in Test.java")
        self.run.save("testcases_proposed.json", {**existing, "cases": [*existing["cases"], *result["cases"]]})
        return result

    def apply_gap(self, target: str, state: dict):
        self.run.write_sources(state["pending_gap"]["files"], "test", append_only=True,
                               reason=f"Approved {target} coverage additions")
        name = "testcases_final.json" if target == "original" else "testcases_refactored.json"
        # Preserve exact bytes, which are the identity in the G1 approval record.
        (self.run.directory / name).write_bytes((self.run.directory / "testcases_proposed.json").read_bytes())
