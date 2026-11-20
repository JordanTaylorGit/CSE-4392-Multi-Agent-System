"""G1 CLI regression tests using illustrative (not real) human decisions."""
import contextlib
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "review_cases.py"
# Load the module once so tests exercise the same functions without a Python startup per assertion.
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("review_cases", SCRIPT)
review_cases = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review_cases)


class ReviewCasesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.cases = self.folder / "testcases_final.json"
        self.report = self.folder / "dedupe-report.md"
        self.log = self.folder / "hitl_decisions.json"
        self.set_data()

    def set_data(self, expected="off", target="original"):
        self.data = {
            "generated_by": "testgen", "target": target,
            "cases": [{
                "id": "EP-01", "method": "EP", "target": target,
                "unit": "off", "setup": {}, "inputs": {},
                "expected": {"stdout": expected},
                "partition": "off-case", "rationale": "illustrative test case",
            }],
        }
        self.cases.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        self.report.write_text("# Test-case deduplication report\n\nNo duplicates.\n", encoding="utf-8")

    def digest(self):
        return hashlib.sha256(self.cases.read_bytes()).hexdigest()

    def call(self, action, *args):
        argv = [sys.executable, str(SCRIPT), action, "--cases", str(self.cases),
                "--report", str(self.report), *args]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = review_cases.main(argv[2:])
        return SimpleNamespace(returncode=status, stdout=out.getvalue(), stderr=err.getvalue())

    def record(self, decision="accept", *args, sha=None):
        return self.call("record", "--log", str(self.log), "--reviewer", "Real Tester",
                         "--decision", decision, "--expected-sha256", sha or self.digest(), *args)

    def check(self):
        return self.call("check", "--log", str(self.log))

    def test_script_entrypoint(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--help"],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("prepare", result.stdout)

    def test_prepare_shows_digest_and_cases_but_does_not_approve(self):
        result = self.call("prepare")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(self.digest(), result.stdout)
        self.assertIn("EP-01", result.stdout)
        self.assertIn("PENDING", result.stdout)
        self.assertFalse(self.log.exists())

    def test_check_blocks_missing_decision(self):
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("pending", result.stderr.lower())

    def test_accept_records_schema_valid_history_and_allows_check(self):
        response = self.record()
        self.assertEqual(response.returncode, 0, response.stderr)
        decisions = json.loads(self.log.read_text())
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["gate"], "review_testcases")
        self.assertEqual(decisions[0]["decision"], "accept")
        self.assertEqual(decisions[0]["artifact_sha256"], self.digest())
        verified = self.check()
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertIn("APPROVED", verified.stdout)

    def test_rejection_with_feedback_blocks_phase_c(self):
        response = self.record("request_changes", "--change", "Add an OFF transition case")
        self.assertEqual(response.returncode, 0, response.stderr)
        checked = self.check()
        self.assertNotEqual(checked.returncode, 0)
        self.assertIn("Add an OFF transition case", checked.stderr)

    def test_requested_changes_cannot_be_empty(self):
        response = self.record("request_changes")
        self.assertNotEqual(response.returncode, 0)
        self.assertFalse(self.log.exists())

    def test_accept_cannot_request_changes(self):
        response = self.record("accept", "--change", "Make a change")
        self.assertNotEqual(response.returncode, 0)
        self.assertFalse(self.log.exists())

    def test_record_rejects_digest_mismatch(self):
        response = self.record(sha="0" * 64)
        self.assertNotEqual(response.returncode, 0)
        self.assertIn("SHA256 mismatch", response.stderr)
        self.assertFalse(self.log.exists())

    def test_changed_case_set_invalidates_prior_approval(self):
        self.assertEqual(self.record().returncode, 0)
        self.set_data(expected="new behavior")
        self.assertNotEqual(self.check().returncode, 0)
        self.assertIn("different case-set revision", self.check().stderr)

    def test_latest_rejection_overrides_earlier_acceptance(self):
        self.assertEqual(self.record().returncode, 0)
        self.assertEqual(self.record("request_changes", "--change", "Fix partition").returncode, 0)
        decisions = json.loads(self.log.read_text())
        self.assertEqual(len(decisions), 2)
        self.assertNotEqual(self.check().returncode, 0)

    def test_other_gate_entries_are_preserved(self):
        self.log.write_text(json.dumps([{
            "gate": "review_refactored", "reviewer": "Other Reviewer",
            "timestamp_utc": "2026-11-15T13:30:00+00:00",
            "decision": "accept", "requested_changes": [],
        }]))
        self.assertEqual(self.record().returncode, 0)
        decisions = json.loads(self.log.read_text())
        self.assertEqual(len(decisions), 2)
        self.assertEqual(decisions[0]["gate"], "review_refactored")
        self.assertEqual(self.check().returncode, 0)

    def test_invalid_existing_history_blocks_recording(self):
        self.log.write_text('[{"gate":"not-a-real-gate"}]')
        response = self.record()
        self.assertNotEqual(response.returncode, 0)
        self.assertIn("Invalid HITL decision", response.stderr)
        self.assertEqual(json.loads(self.log.read_text()), [{"gate": "not-a-real-gate"}])

    def test_single_decision_history_converts_to_list(self):
        self.assertEqual(self.record().returncode, 0)
        prior = json.loads(self.log.read_text())[0]
        self.log.write_text(json.dumps(prior), encoding="utf-8")
        self.assertEqual(self.record().returncode, 0)
        self.assertEqual(len(json.loads(self.log.read_text())), 2)

    def test_invalid_case_set_cannot_be_reviewed(self):
        del self.data["cases"][0]["rationale"]
        self.cases.write_text(json.dumps(self.data), encoding="utf-8")
        self.assertNotEqual(self.call("prepare").returncode, 0)

    def test_refactored_cases_cannot_enter_original_gate(self):
        self.set_data(target="refactored")
        self.assertNotEqual(self.call("prepare").returncode, 0)
        self.assertIn("original target only", self.call("prepare").stderr)

    def test_missing_dedupe_report_prevents_approval(self):
        self.report.unlink()
        self.assertNotEqual(self.record().returncode, 0)
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
