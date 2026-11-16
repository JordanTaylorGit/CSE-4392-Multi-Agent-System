"""Phase C regression tests with synthetic G1 decisions, not real human approvals."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

TOOL_DIR = Path(__file__).resolve().parents[1]
ROOT = TOOL_DIR.parents[1]
sys.path.insert(0, str(TOOL_DIR))
SPEC = importlib.util.spec_from_file_location("materialize_junit", TOOL_DIR / "materialize_junit.py")
materialize = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(materialize)


class MaterializeJUnitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.cases_file = self.base / "testcases_final.json"
        self.report = self.base / "dedupe-report.md"
        self.log = self.base / "hitl_decisions.json"
        self.output = ROOT / "java/src/test/java/cse4392/SeasonSwitchGeneratedTest.java"
        self.profile = ROOT / "projects/seasonswitch/profile.json"
        if self.output.exists():
            self.fail(f"Test output path already exists: {self.output}")
        self.addCleanup(lambda: self.output.unlink(missing_ok=True))
        self.cases = [{
            "id": "BVA-01", "method": "BVA", "target": "original", "unit": "timerOff",
            "setup": {"state": "COOL", "room.temp": 68}, "inputs": {},
            "expected": {"state": "COOL", "ac.isOn": False,
                         "stdout": "Cooling stopped. RmTemp=68\n"},
            "partition": "coolTemp-at", "rationale": "boundary at 68",
        }]
        self.save_cases()

    def save_cases(self):
        self.cases_file.write_text(json.dumps({"generated_by": "testgen", "target": "original", "cases": self.cases}), encoding="utf-8")
        self.report.write_text("# Deduplication report\n", encoding="utf-8")

    def approve_fixture(self):
        self.log.write_text(json.dumps([{
            "gate": "review_testcases", "reviewer": "Synthetic unit-test reviewer",
            "timestamp_utc": "2026-11-15T13:30:00+00:00", "decision": "accept",
            "requested_changes": [],
            "artifact_sha256": hashlib.sha256(self.cases_file.read_bytes()).hexdigest(),
        }]), encoding="utf-8")

    def args(self, out=None, profile=None):
        return ["--profile", str(profile or self.profile), "--cases", str(self.cases_file),
                "--report", str(self.report), "--log", str(self.log),
                "--out", str(out or self.output)]

    def run_cli(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return materialize.main(self.args() + list(args))

    def test_no_g1_decision_blocks_java(self):
        self.assertEqual(self.run_cli(), 1)
        self.assertFalse(self.output.exists())

    def test_rejected_decision_blocks_java(self):
        self.approve_fixture()
        history = json.loads(self.log.read_text())
        history[0]["decision"] = "request_changes"
        history[0]["requested_changes"] = ["Fix expected result"]
        self.log.write_text(json.dumps(history))
        self.assertEqual(self.run_cli(), 1)
        self.assertFalse(self.output.exists())

    def test_stale_decision_blocks_java(self):
        self.approve_fixture()
        self.cases[0]["expected"]["stdout"] = "other output"
        self.save_cases()
        self.assertEqual(self.run_cli(), 1)
        self.assertFalse(self.output.exists())

    def test_generates_junit_with_exact_expected_values(self):
        self.approve_fixture()
        self.assertEqual(self.run_cli(), 0)
        java = self.output.read_text()
        self.assertTrue(java.startswith(materialize.MARKER))
        self.assertEqual(java.count("    @Test"), 1)
        self.assertIn('@DisplayName("BVA-01 coolTemp-at")', java)
        self.assertIn("s.cool();", java)
        self.assertIn("s.room.temp = 68;", java)
        self.assertIn("s.timerOff();", java)
        self.assertIn("assertEquals(false, s.ac.isOn);", java)
        self.assertIn('assertEquals("Cooling stopped. RmTemp=68\\n", actualOutput);', java)
        self.assertIn("SeasonSwitch.state", java)

    def test_unknown_setup_is_rejected_instead_of_ignored(self):
        self.cases[0]["setup"]["mystery"] = 1
        self.save_cases()
        self.approve_fixture()
        self.assertEqual(self.run_cli(), 1)
        self.assertFalse(self.output.exists())

    def test_unknown_expected_is_rejected_instead_of_ignored(self):
        self.cases[0]["expected"]["made.up"] = 123
        self.save_cases()
        self.approve_fixture()
        self.assertEqual(self.run_cli(), 1)

    def test_wrong_expected_type_is_rejected(self):
        self.cases[0]["expected"]["ac.isOn"] = "false"
        self.save_cases()
        self.approve_fixture()
        self.assertEqual(self.run_cli(), 1)

    def test_refuses_to_overwrite_handwritten_test_file(self):
        self.approve_fixture()
        # Do not mutate teammates' files. Any non-generated file should be refused.
        with tempfile.TemporaryDirectory() as temp:
            test_root = Path(temp) / "tests"
            test_root.mkdir()
            fake = test_root / "SeasonSwitchTest.java"
            fake.write_text("// Hand-written JUnit source\n")
            with patch.object(materialize, "ROOT", Path(temp)):
                profile = {"language": "java", "test_root": "tests"}
                with patch.object(materialize, "profile_and_adapter", return_value=(profile, None)):
                    args = SimpleNamespace(profile=self.profile, cases=self.cases_file,
                                           report=self.report, log=self.log, out=fake)
                    with self.assertRaisesRegex(materialize.MaterializeError, "overwrite"):
                        materialize.materialize(args)
            self.assertEqual(fake.read_text(), "// Hand-written JUnit source\n")

    def test_existing_generated_java_is_invalidated_on_failure(self):
        self.approve_fixture()
        self.assertEqual(self.run_cli(), 0)
        self.assertTrue(self.output.exists())
        self.cases[0]["expected"]["unsupported"] = 42
        self.save_cases()
        self.approve_fixture()
        self.assertEqual(self.run_cli(), 1)
        self.assertFalse(self.output.exists())

    def test_bad_output_destination_is_rejected(self):
        self.approve_fixture()
        with contextlib.redirect_stderr(io.StringIO()):
            code = materialize.main(self.args(out=self.base / "Elsewhere.java"))
        self.assertEqual(code, 1)

    def test_grade_classifier_requires_its_own_adapter(self):
        self.approve_fixture()
        with contextlib.redirect_stderr(io.StringIO()):
            status = materialize.main(self.args(profile=ROOT / "projects/grade-classifier/profile.json"))
        self.assertEqual(status, 1)

    @unittest.skipUnless(shutil.which("javac"), "JDK not installed")
    def test_generated_java_compiles_and_runs_with_original_java_and_stub_junit_api(self):
        self.approve_fixture()
        self.assertEqual(self.run_cli(), 0)
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            api = folder / "org/junit/jupiter/api"
            api.mkdir(parents=True)
            for annotation in ("Test", "BeforeEach", "AfterEach", "DisplayName"):
                signature = "String value();" if annotation == "DisplayName" else ""
                (api / f"{annotation}.java").write_text(
                    "package org.junit.jupiter.api; public @interface " + annotation + " {" + signature + "}")
            (api / "Assertions.java").write_text(
                "package org.junit.jupiter.api; public class Assertions {"
                "public static void assertEquals(Object a, Object b) {"
                "if (!java.util.Objects.equals(a,b)) throw new AssertionError(a+\" != \"+b); } }")
            runner = folder / "GeneratedRunner.java"
            runner.write_text(
                'package cse4392; public class GeneratedRunner { '
                'public static void main(String[] a) { '
                'SeasonSwitchGeneratedTest t = new SeasonSwitchGeneratedTest(); '
                't.setUp(); try { t.test_BVA_01(); } finally { t.tearDown(); } '
                'System.out.println("GENERATED_TEST_PASSED"); } }',
                encoding="utf-8")
            source = ROOT / "java/src/original/java/cse4392/SeasonSwitch.java"
            files = [source, self.output, runner, *api.glob("*.java")]
            command = ["javac", "--release", "17", "-d", str(folder / "classes"), *map(str, files)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=25)
            self.assertEqual(result.returncode, 0, result.stdout + "\n" + result.stderr)
            execute = subprocess.run(["java", "-Djava.awt.headless=true", "-cp",
                                      str(folder / "classes"), "cse4392.GeneratedRunner"],
                                     capture_output=True, text=True, timeout=20)
            self.assertEqual(execute.returncode, 0, execute.stdout + "\n" + execute.stderr)
            self.assertIn("GENERATED_TEST_PASSED", execute.stdout)


if __name__ == "__main__":
    unittest.main()
