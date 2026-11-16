"""Unit tests for P4 Phase B, using only illustrative case data."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "merge_cases.py"
SPEC = importlib.util.spec_from_file_location("merge_cases", MODULE_PATH)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class MergeCasesTests(unittest.TestCase):
    def setUp(self):
        self.profile = {"units": [{"name": "cool"}], "dedupe_key": ["unit", "setup", "inputs"]}
        self.ep = {"generated_by": "ep-tests", "target": "original", "cases": [self.case("EP-01", "EP", "base")]}
        self.bva = {"generated_by": "bva-tests", "target": "original", "cases": [self.case("BVA-01", "BVA", "boundary")]}

    def case(self, cid, method, value, expected="ok"):
        return {"id": cid, "method": method, "target": "original", "unit": "cool",
                "setup": {"state": "OFF"}, "inputs": {"scenario": value},
                "expected": {"stdout": expected}, "partition": value, "rationale": "illustrative test"}

    def test_distinct_cases_are_preserved(self):
        merged, report = mod.merge_sets(self.ep, self.bva, self.profile)
        self.assertEqual([c["id"] for c in merged["cases"]], ["EP-01", "BVA-01"])
        self.assertIn("Removed duplicates: 0", report)

    def test_identical_inputs_and_expectations_deduplicate(self):
        self.bva["cases"][0]["inputs"] = {"scenario": "base"}
        merged, report = mod.merge_sets(self.ep, self.bva, self.profile)
        self.assertEqual(len(merged["cases"]), 1)
        self.assertIn("| BVA-01 | EP-01 |", report)

    def test_conflicting_expectations_stop(self):
        self.bva["cases"][0]["inputs"] = {"scenario": "base"}
        self.bva["cases"][0]["expected"] = {"stdout": "different"}
        with self.assertRaisesRegex(mod.MergeError, "Conflicting expected"):
            mod.merge_sets(self.ep, self.bva, self.profile)

    def test_schema_rejects_missing_fields(self):
        del self.ep["cases"][0]["rationale"]
        with self.assertRaisesRegex(mod.MergeError, "schema error"):
            mod.merge_sets(self.ep, self.bva, self.profile)

    def test_rejects_unknown_unit(self):
        self.ep["cases"][0]["unit"] = "unknown"
        with self.assertRaisesRegex(mod.MergeError, "unknown unit"):
            mod.merge_sets(self.ep, self.bva, self.profile)

    def test_rejects_mixed_targets(self):
        self.bva["target"] = "refactored"
        self.bva["cases"][0]["target"] = "refactored"
        with self.assertRaisesRegex(mod.MergeError, "target values differ"):
            mod.merge_sets(self.ep, self.bva, self.profile)

    def test_rejects_duplicate_ids(self):
        self.bva["cases"][0]["id"] = "EP-01"
        self.bva["cases"][0]["method"] = "EP"
        with self.assertRaises(mod.MergeError):
            mod.merge_sets(self.ep, self.bva, self.profile)

    def test_cli_conflict_writes_report_but_no_case_set(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.bva["cases"][0]["inputs"] = {"scenario": "base"}
            self.bva["cases"][0]["expected"] = {"stdout": "different"}
            for name, data in (("profile.json", self.profile), ("ep.json", self.ep), ("bva.json", self.bva)):
                (d / name).write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run([sys.executable, str(MODULE_PATH),
                                     "--profile", str(d / "profile.json"), "--ep", str(d / "ep.json"),
                                     "--bva", str(d / "bva.json"), "--out", str(d / "out.json"),
                                     "--report", str(d / "report.md")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertFalse((d / "out.json").exists())
            self.assertIn("Conflicting expected", (d / "report.md").read_text())

    def test_cli_failed_rerun_invalidates_previous_case_set(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for name, data in (("profile.json", self.profile), ("ep.json", self.ep), ("bva.json", self.bva)):
                (d / name).write_text(json.dumps(data), encoding="utf-8")
            command = [sys.executable, str(MODULE_PATH),
                       "--profile", str(d / "profile.json"), "--ep", str(d / "ep.json"),
                       "--bva", str(d / "bva.json"), "--out", str(d / "out.json"),
                       "--report", str(d / "report.md")]

            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, msg=first.stderr)
            self.assertTrue((d / "out.json").exists())

            # Same output directory, but a now-conflicting BVA response.
            self.bva["cases"][0]["inputs"] = {"scenario": "base"}
            self.bva["cases"][0]["expected"] = {"stdout": "different"}
            (d / "bva.json").write_text(json.dumps(self.bva), encoding="utf-8")
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertFalse((d / "out.json").exists())
            self.assertIn("Conflicting expected", (d / "report.md").read_text())

    def test_cli_writes_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for name, data in (("profile.json", self.profile), ("ep.json", self.ep), ("bva.json", self.bva)):
                (d / name).write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run([sys.executable, str(MODULE_PATH),
                                     "--profile", str(d / "profile.json"), "--ep", str(d / "ep.json"),
                                     "--bva", str(d / "bva.json"), "--out", str(d / "out.json"),
                                     "--report", str(d / "report.md")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertEqual(len(json.loads((d / "out.json").read_text())["cases"]), 2)
            self.assertIn("G1 human review", (d / "report.md").read_text())


if __name__ == "__main__":
    unittest.main()
