"""P4 adapt-mode regression tests; review decisions are synthetic test fixtures."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOL_DIR = Path(__file__).resolve().parents[1]
ROOT = TOOL_DIR.parents[1]
sys.path.insert(0, str(TOOL_DIR))
SPEC = importlib.util.spec_from_file_location("materialize_junit", TOOL_DIR / "materialize_junit.py")
materialize = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(materialize)


class AdaptModeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.case_file = self.base / "testcases_final.json"
        self.report = self.base / "dedupe-report.md"
        self.log = self.base / "hitl_decisions.json"
        self.test_root = self.base / "tests"
        self.test_root.mkdir()
        self.output = self.test_root / "SeasonSwitchAdaptedTest.java"
        self.profile_path = ROOT / "projects/seasonswitch/profile.json"
        self.profile, self.adapter = materialize.profile_and_adapter(self.profile_path)
        self.profile = {**self.profile, "test_root": "tests"}
        self.cases = [{
            "id": "BVA-01", "method": "BVA", "target": "original", "unit": "timerOff",
            "setup": {"state": "COOL", "room.temp": 68}, "inputs": {},
            "expected": {"state": "COOL", "ac.isOn": False,
                         "stdout": "Cooling stopped. RmTemp=68\n"},
            "partition": "coolTemp-at", "rationale": "at the cooling threshold",
        }]
        self.save_cases()

    def save_cases(self, target="original"):
        self.case_file.write_text(json.dumps({
            "generated_by": "testgen", "target": target, "cases": self.cases,
        }), encoding="utf-8")
        self.report.write_text("# Deduplication report\n", encoding="utf-8")

    def approve_fixture(self, decision="accept"):
        self.log.write_text(json.dumps([{
            "gate": "review_testcases", "reviewer": "Synthetic fixture",
            "timestamp_utc": "2026-11-17T12:00:00+00:00", "decision": decision,
            "requested_changes": [] if decision == "accept" else ["Changes required"],
            "artifact_sha256": hashlib.sha256(self.case_file.read_bytes()).hexdigest(),
        }]), encoding="utf-8")

    def run_cli(self, mode="adapt"):
        argv = ["--mode", mode, "--profile", str(self.profile_path),
                "--cases", str(self.case_file), "--report", str(self.report),
                "--log", str(self.log), "--out", str(self.output)]
        with patch.object(materialize, "ROOT", self.base), \
             patch.object(materialize, "profile_and_adapter", return_value=(self.profile, self.adapter)), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return materialize.main(argv)

    def test_adapt_reuses_exact_original_expectations(self):
        self.approve_fixture()
        original_bytes = self.case_file.read_bytes()
        self.assertEqual(self.run_cli(), 0)
        source = self.output.read_text(encoding="utf-8")
        self.assertIn('assertEquals("Cooling stopped. RmTemp=68\\n", actualOutput);', source)
        self.assertIn("assertEquals(false, s.ac.isOn);", source)
        self.assertIn("assertEquals(SeasonSwitch.COOL, SeasonSwitch.state);", source)
        self.assertEqual(source.count("    @Test"), 1)
        self.assertEqual(self.case_file.read_bytes(), original_bytes)

    def test_no_approval_blocks_adapt(self):
        self.assertEqual(self.run_cli(), 1)
        self.assertFalse(self.output.exists())

    def test_rejection_blocks_adapt(self):
        self.approve_fixture("request_changes")
        self.assertEqual(self.run_cli(), 1)
        self.assertFalse(self.output.exists())

    def test_stale_approval_blocks_adapt(self):
        self.approve_fixture()
        self.cases[0]["expected"]["stdout"] = "modified after G1"
        self.save_cases()
        self.assertEqual(self.run_cli(), 1)
        self.assertFalse(self.output.exists())

    def test_refactored_input_cannot_bypass_original_g1(self):
        self.cases[0]["target"] = "refactored"
        self.save_cases(target="refactored")
        self.approve_fixture()
        self.assertEqual(self.run_cli(), 1)
        self.assertFalse(self.output.exists())

    def test_unknown_expected_is_not_silently_ignored(self):
        self.cases[0]["expected"]["unknown.property"] = 1
        self.save_cases()
        self.approve_fixture()
        self.assertEqual(self.run_cli(), 1)
        self.assertFalse(self.output.exists())

    def test_existing_generated_java_cleared_when_review_goes_stale(self):
        self.approve_fixture()
        self.assertEqual(self.run_cli(), 0)
        self.assertTrue(self.output.exists())
        self.cases[0]["expected"]["stdout"] = "changed"
        self.save_cases()
        self.assertEqual(self.run_cli(), 1)
        self.assertFalse(self.output.exists())

    def test_generate_default_remains_supported(self):
        self.approve_fixture()
        self.assertEqual(self.run_cli(mode="generate"), 0)
        self.assertIn("s.timerOff();", self.output.read_text())

    def test_adapter_rejects_mixed_targets(self):
        self.cases.append({**self.cases[0], "id": "EP-02", "target": "refactored"})
        with self.assertRaisesRegex(ValueError, "one supported target"):
            self.adapter.render(self.cases, self.profile, "SeasonSwitchAdaptedTest")


if __name__ == "__main__":
    unittest.main()
