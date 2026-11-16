#!/usr/bin/env python3
"""G1 manual review helper for the testgen skill.

This utility presents the merged case set, records an explicit human decision,
and verifies a decision before Phase C. It does not pause/resume LangGraph or
approve anything automatically; the overarching harness owns that gate.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from merge_cases import MergeError, get_validator, read_json, validate_set

ROOT = Path(__file__).resolve().parents[2]
GATE = "review_testcases"
HEX_SHA256 = re.compile(r"[a-f0-9]{64}\Z")


class ReviewError(Exception):
    """A review is missing, invalid, rejected, or no longer applicable."""


def review_source(cases_path: Path, report_path: Path) -> tuple[dict[str, Any], str]:
    """Read the current artifacts and return the case set and its byte-level hash."""
    try:
        content = cases_path.read_bytes()
        report_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReviewError(f"Cannot read G1 artifacts: {exc}") from exc
    try:
        cases = json.loads(content)
        validate_set(cases, "G1 cases", get_validator())
    except (ValueError, MergeError) as exc:
        raise ReviewError(f"Invalid G1 case set: {exc}") from exc
    if cases["target"] != "original":
        raise ReviewError("G1 test-case review applies to original target only")
    if cases["generated_by"] != "testgen":
        raise ReviewError("G1 requires the merged testgen output")
    ids = [case["id"] for case in cases["cases"]]
    if len(ids) != len(set(ids)):
        raise ReviewError("G1 case set contains duplicate IDs")
    return cases, hashlib.sha256(content).hexdigest()


def decision_validator() -> Draft202012Validator:
    try:
        schema = read_json(ROOT / "schemas/hitl_decision.schema.json")
    except MergeError as exc:
        raise ReviewError(str(exc)) from exc
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_decision(record: Any, validator: Draft202012Validator) -> None:
    issues = list(validator.iter_errors(record))
    if issues:
        raise ReviewError(f"Invalid HITL decision: {issues[0].message}")
    if record["gate"] == GATE:
        fingerprint = record.get("artifact_sha256", "")
        if not HEX_SHA256.fullmatch(fingerprint):
            raise ReviewError("G1 decision requires a 64-character artifact_sha256")
        if record["decision"] == "request_changes" and not record["requested_changes"]:
            raise ReviewError("A rejected G1 review must describe requested changes")
        if record["decision"] == "accept" and record["requested_changes"]:
            raise ReviewError("An accepted G1 review cannot also request changes")


def load_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewError(f"Cannot read decisions log: {exc}") from exc
    # A legacy single decision is accepted. New writes preserve the full history as a list.
    entries = [content] if isinstance(content, dict) else content
    if not isinstance(entries, list):
        raise ReviewError("HITL log must be a decision or an array of decisions")
    validator = decision_validator()
    for i, item in enumerate(entries):
        try:
            validate_decision(item, validator)
        except ReviewError as exc:
            raise ReviewError(f"HITL log entry {i}: {exc}") from exc
    return entries


def store_history(path: Path, entries: list[dict[str, Any]]) -> None:
    """Write the complete audit log without truncating it mid-write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".hitl-", suffix=".json", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(entries, handle, indent=2)
            handle.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def prepare(args: argparse.Namespace) -> int:
    cases, digest = review_source(args.cases, args.report)
    kinds = Counter(case["method"] for case in cases["cases"])
    print(f"G1 HUMAN REVIEW — {len(cases['cases'])} cases (EP: {kinds['EP']}, BVA: {kinds['BVA']}, GAP: {kinds['GAP']})")
    print(f"Cases: {args.cases}\nDedupe report: {args.report}")
    print(f"SHA256: {digest}")
    print("\nReview the actual case set AND deduplication report before deciding:")
    for case in cases["cases"]:
        print(f"  {case['id']}: {case['unit']} / {case['partition']} | expected={json.dumps(case['expected'], sort_keys=True)}")
    print("\nG1 is PENDING until a human records an explicit decision.")
    return 0


def record(args: argparse.Namespace) -> int:
    _, digest = review_source(args.cases, args.report)
    if digest != args.expected_sha256:
        raise ReviewError("Case set changed since review (SHA256 mismatch); review it again")
    reviewer = args.reviewer.strip()
    if not reviewer:
        raise ReviewError("Human reviewer must be named")
    changes = [change.strip() for change in args.change]
    if args.decision == "request_changes" and (not changes or any(not c for c in changes)):
        raise ReviewError("request_changes requires at least one nonempty --change")
    if args.decision == "accept" and changes:
        raise ReviewError("accept cannot include --change")
    record_data = {
        "gate": GATE,
        "reviewer": reviewer,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "decision": args.decision,
        "requested_changes": changes,
        "artifact_sha256": digest,
    }
    if args.resulting_diff:
        record_data["resulting_diff"] = args.resulting_diff
    validate_decision(record_data, decision_validator())
    history = load_history(args.log)
    history.append(record_data)
    store_history(args.log, history)
    print(f"Recorded G1 {args.decision} from {reviewer} for {digest}")
    return 0


def check(args: argparse.Namespace) -> int:
    _, digest = review_source(args.cases, args.report)
    history = load_history(args.log)
    last = next((item for item in reversed(history) if item["gate"] == GATE), None)
    if last is None:
        raise ReviewError("G1 pending: no human test-case review decision exists")
    if last["artifact_sha256"] != digest:
        raise ReviewError("G1 pending: latest decision was for a different case-set revision")
    if last["decision"] != "accept":
        raise ReviewError("G1 blocked: reviewer requested changes: " + "; ".join(last["requested_changes"]))
    print(f"G1 APPROVED for {digest} by {last['reviewer']}. Phase C may proceed.")
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="operation", required=True)
    for name in ("prepare", "record", "check"):
        sub = subs.add_parser(name)
        sub.add_argument("--cases", type=Path, required=True, help="testcases_final.json")
        sub.add_argument("--report", type=Path, required=True, help="dedupe-report.md")
        if name in ("record", "check"):
            sub.add_argument("--log", type=Path, required=True, help="hitl_decisions.json")
        if name == "record":
            sub.add_argument("--reviewer", required=True, help="Actual human reviewer")
            sub.add_argument("--decision", choices=("accept", "request_changes"), required=True)
            sub.add_argument("--expected-sha256", required=True, help="SHA256 printed by prepare")
            sub.add_argument("--change", action="append", default=[], help="Requested change; repeat as needed")
            sub.add_argument("--resulting-diff", help="Optional reference to reviewed change evidence")
        sub.set_defaults(run={"prepare": prepare, "record": record, "check": check}[name])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        return args.run(args)
    except ReviewError as exc:
        print(f"G1 BLOCKED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
