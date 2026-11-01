#!/usr/bin/env python3
"""Lint the skill graph. Not a runner -- it never executes a stage.

Checks that every skill declares a complete frontmatter block, that stage ids are unique, that
everything referenced by `orchestrates:` exists, and that every `schema:` points at parseable JSON.

    python3 scripts/validate_skills.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ("id", "order", "executor", "inputs", "outputs", "gate")


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not match:
        raise ValueError("missing frontmatter")
    meta: dict = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, raw = line.partition(":")
        raw = raw.split(" #")[0].strip()
        meta[key.strip()] = ([v.strip() for v in raw[1:-1].split(",") if v.strip()]
                             if raw.startswith("[") and raw.endswith("]") else raw)
    return meta


def main() -> int:
    errors: list[str] = []
    stages: dict[str, dict] = {}

    for path in sorted((ROOT / ".agents").glob("*/SKILL.md")):
        if path.parent.name == "_template":
            continue
        try:
            meta = frontmatter(path)
        except ValueError as exc:
            errors.append(f"{path.parent.name}/SKILL.md: {exc}")
            continue
        for key in REQUIRED:
            if key not in meta:
                errors.append(f"{path.parent.name}/SKILL.md: missing '{key}'")
        if path.parent.name != meta.get("id"):
            errors.append(f"{path.parent.name}/SKILL.md: id '{meta.get('id')}' does not match directory")
        if meta.get("id") in stages:
            errors.append(f"{path.parent.name}/SKILL.md: duplicate id '{meta.get('id')}'")
        stages[meta.get("id", path.stem)] = meta

    for stage_id, meta in stages.items():
        for target in meta.get("orchestrates", []) + meta.get("subskills", []):
            if target not in stages:
                errors.append(f"{stage_id}: references unknown stage '{target}'")
        schema = meta.get("schema")
        if schema:
            schema_path = ROOT / schema
            if not schema_path.exists():
                errors.append(f"{stage_id}: schema '{schema}' not found")
            else:
                try:
                    json.loads(schema_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    errors.append(f"{stage_id}: schema '{schema}' is not valid JSON: {exc}")

    referenced = {t for m in stages.values() for t in m.get("orchestrates", []) + m.get("subskills", [])}
    orphans = set(stages) - referenced - {"orchestrator"}
    if orphans:
        errors.append(f"stages not reachable from orchestrator: {sorted(orphans)}")

    # project profiles
    profiles = sorted((ROOT / "projects").glob("*/profile.json"))
    if not profiles:
        errors.append("no project profiles found under projects/*/profile.json")
    required_profile = ("project", "subject", "language", "source", "units",
                        "state_variables", "observable", "boundaries", "dedupe_key", "coverage")
    for path in profiles:
        try:
            profile = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.parent.name}/profile.json: invalid JSON: {exc}")
            continue
        for key in required_profile:
            if key not in profile:
                errors.append(f"{path.parent.name}/profile.json: missing '{key}'")
        if profile.get("project") != path.parent.name:
            errors.append(f"{path.parent.name}/profile.json: project '{profile.get('project')}' "
                          f"does not match directory")
        if not profile.get("dedupe_key"):
            errors.append(f"{path.parent.name}/profile.json: dedupe_key must be non-empty")
        source = profile.get("source")
        if source and not (ROOT / source).exists():
            errors.append(f"{path.parent.name}/profile.json: source '{source}' not found")

    if errors:
        print("skill graph is invalid:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"skill graph ok: {len(stages)} stages, "
          f"{sum(1 for m in stages.values() if m.get('gate') == 'human')} HITL gates, "
          f"{len(profiles)} project profiles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
