"""Maven execution and report-based coverage; model claims are never evidence."""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from harness.workspace import RunWorkspace, child_environment


def read_reports(directory: Path, returncode: int) -> dict:
    tests = failures = skipped = covered = missed = excluded = 0
    suites = list((directory / "surefire").glob("TEST-*.xml"))
    for path in suites:
        suite = ET.parse(path).getroot()
        tests += int(suite.get("tests", 0))
        failures += int(suite.get("failures", 0)) + int(suite.get("errors", 0))
        skipped += int(suite.get("skipped", 0))
    report = directory / "jacoco.xml"
    if report.exists():
        for method in ET.parse(report).getroot().iter("method"):
            for counter in method.findall("counter"):
                if counter.get("type") != "BRANCH":
                    continue
                hit, unhit = int(counter.get("covered", 0)), int(counter.get("missed", 0))
                if min(hit, unhit) < 0:
                    raise ValueError("Invalid negative branch counter")
                if method.get("name") == "main":
                    excluded += hit + unhit
                else:
                    covered += hit
                    missed += unhit
    total = covered + missed
    passed = returncode == 0 and tests > 0 and failures == 0 and skipped == 0
    return {"passed": passed, "complete": passed and total > 0 and missed == 0,
            "tests": tests, "failures": failures, "skipped": skipped,
            "covered": covered, "missed": missed,
            "percent": 100 * covered / total if total else None,
            "excluded_main_branches": excluded, "report_dir": str(directory)}


def execute(command: list[str], cwd: Path, timeout=180) -> tuple[int, str]:
    process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True,
                               env=child_environment(), start_new_session=True)
    try:
        output, _ = process.communicate(timeout=timeout)
        return process.returncode, output
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        output, _ = process.communicate()
        return 124, output + f"\nBuild timed out after {timeout}s.\n"


class MavenRunner:
    def __init__(self, executable="mvn", timeout=180):
        self.executable = executable
        self.timeout = timeout

    def compile(self, run: RunWorkspace, attempt: int) -> dict:
        code, log = execute([self.executable, "-B", "-P", "refactored", "clean", "compile"],
                            run.workspace / "java", self.timeout)
        (run.directory / f"compile-{attempt}.log").write_text(log, encoding="utf-8")
        return {"passed": code == 0, "log": log[-16000:]}

    def __call__(self, run: RunWorkspace, target: str, attempt: int) -> dict:
        if target not in {"original", "refactored"} or not run.source_files(target):
            raise ValueError(f"Missing {target} Java sources")
        directory = run.directory / target / f"attempt-{attempt}"
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True)
        code, log = execute(
            [self.executable, "-B", "-P", target, "clean", "test", "jacoco:report"],
            run.workspace / "java", self.timeout)
        (directory / "maven.log").write_text(log, encoding="utf-8")
        build_dir = run.workspace / "java/target"
        for source, destination in ((build_dir / "surefire-reports", directory / "surefire"),
                                    (build_dir / "site/jacoco/jacoco.xml", directory / "jacoco.xml")):
            if source.is_dir():
                shutil.copytree(source, destination)
            elif source.is_file():
                shutil.copy2(source, destination)
        result = read_reports(directory, code)
        result["log"] = log[-16000:]
        run.save(f"{target}/attempt-{attempt}/result.json", result)
        return result
