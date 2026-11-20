#!/usr/bin/env python3
"""Validate, join, and deduplicate EP/BVA test-case sets for the testgen skill.

Run after both subagents finish. A successful merge produces the case set and a
report for G1 review. This does not approve G1 or generate Java tests.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]


class MergeError(Exception):
    """Invalid input or conflicting cases requiring intervention."""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MergeError(f"Cannot read {path}: {exc}") from exc


def get_validator() -> Draft202012Validator:
    case_schema = read_json(ROOT / "schemas/testcase.schema.json")
    set_schema = read_json(ROOT / "schemas/testcase-set.schema.json")
    registry = Registry().with_resource(
        uri="testcase.schema.json",
        resource=Resource.from_contents(case_schema),
    )
    return Draft202012Validator(set_schema, registry=registry)


def validate_set(data: Any, name: str, validator: Draft202012Validator) -> None:
    errors = sorted(validator.iter_errors(data), key=lambda e: (list(map(str, e.path)), e.message))
    if errors:
        err = errors[0]
        location = ".".join(map(str, err.absolute_path)) or "root"
        raise MergeError(f"{name}: schema error at {location}: {err.message}")
    if not data["generated_by"].strip():
        raise MergeError(f"{name}: generated_by cannot be blank")
    for index, case in enumerate(data["cases"]):
        if case["target"] != data["target"]:
            raise MergeError(f"{name}: case {index} target does not match set target")


def merge_sets(
    ep: Any, bva: Any, profile: Any,
    validator: Draft202012Validator | None = None,
) -> tuple[dict[str, Any], str]:
    """Return merged schema-valid case set and Markdown report; raise on conflict."""
    validator = validator or get_validator()
    validate_set(ep, "EP output", validator)
    validate_set(bva, "BVA output", validator)

    if ep["target"] != bva["target"]:
        raise MergeError("EP and BVA target values differ")
    if not isinstance(profile, dict):
        raise MergeError("Profile must be a JSON object")
    keys = profile.get("dedupe_key")
    if not isinstance(keys, list) or not keys or not all(isinstance(k, str) and k for k in keys):
        raise MergeError("profile.dedupe_key must be a nonempty list of field names")
    if len(keys) != len(set(keys)):
        raise MergeError("profile.dedupe_key contains duplicate field names")
    if not isinstance(profile.get("units"), list):
        raise MergeError("profile.units must be a list")
    known_units = {u.get("name") for u in profile["units"] if isinstance(u, dict)}

    # Preserve EP then BVA order to keep artifacts reproducible.
    seen: dict[str, dict[str, Any]] = {}
    ids: set[str] = set()
    kept: list[dict[str, Any]] = []
    removed: list[tuple[str, str]] = []
    for origin, case_set, expected_method in (
        ("EP", ep, "EP"), ("BVA", bva, "BVA")
    ):
        for case in case_set["cases"]:
            cid = case["id"]
            if cid in ids:
                raise MergeError(f"Duplicate case ID: {cid}")
            ids.add(cid)
            if case["method"] != expected_method:
                raise MergeError(f"{origin} output contains {cid} with method {case['method']}")
            if case["unit"] not in known_units:
                raise MergeError(f"{cid}: unknown unit {case['unit']!r} for project profile")
            missing = [key for key in keys if key not in case]
            if missing:
                raise MergeError(f"{cid}: missing dedupe key fields: {', '.join(missing)}")
            fingerprint = json.dumps([case[key] for key in keys], sort_keys=True, separators=(",", ":"))
            previous = seen.get(fingerprint)
            if previous is None:
                seen[fingerprint] = case
                kept.append(case)
            elif previous["expected"] != case["expected"]:
                raise MergeError(
                    f"Conflicting expected results: {previous['id']} and {cid} "
                    f"have the same dedupe key {keys}"
                )
            else:
                removed.append((cid, previous["id"]))

    result = {"generated_by": "testgen", "target": ep["target"], "cases": kept}
    validate_set(result, "Merged output", validator)
    total = len(ep["cases"]) + len(bva["cases"])
    lines = [
        "# Test-case deduplication report", "",
        f"- Input EP: {len(ep['cases'])}",
        f"- Input BVA: {len(bva['cases'])}",
        f"- Total input: {total}",
        f"- Kept: {len(kept)}",
        f"- Removed duplicates: {len(removed)}",
        f"- Dedupe fields: {', '.join(keys)}",
        "", "## Removed cases", "",
    ]
    if removed:
        lines += ["| Removed | Kept |", "| --- | --- |"]
        lines += [f"| {discarded} | {survivor} |" for discarded, survivor in removed]
    else:
        lines += ["None."]
    lines += ["", "Next step: present the merged cases and this report for G1 human review.", ""]
    return result, "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--ep", type=Path, required=True)
    parser.add_argument("--bva", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="testcases_final.json")
    parser.add_argument("--report", type=Path, required=True, help="dedupe-report.md")
    args = parser.parse_args(argv)
    # An output path must never alias an input; the final case set is invalidated
    # before each attempt so a failed rerun cannot leave a stale approval artifact.
    inputs = {p.resolve() for p in (args.profile, args.ep, args.bva)}
    if args.out.resolve() in inputs or args.report.resolve() in inputs | {args.out.resolve()}:
        parser.error("Output and report paths must differ from inputs and each other")
    try:
        args.out.unlink(missing_ok=True)
        result, report = merge_sets(
            read_json(args.ep), read_json(args.bva), read_json(args.profile)
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        args.report.write_text(report, encoding="utf-8")
    except MergeError as exc:
        # Keep a durable rejection record; do not create testcases_final.json.
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            "# Test-case merge stopped\n\n"
            f"Reason: {exc}\n\n"
            "Do not advance to G1 until the inputs are corrected.\n",
            encoding="utf-8",
        )
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Merged {len(result['cases'])} cases; review {args.report} at gate G1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
