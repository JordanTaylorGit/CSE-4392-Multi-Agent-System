"""Run artifacts and constrained writes in a private copy of the project."""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}-{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def child_environment() -> dict[str, str]:
    return {key: value for key, value in os.environ.items()
            if key in {"PATH", "JAVA_HOME", "HOME", "LANG", "TMPDIR", "SYSTEMROOT"}}


class RunWorkspace:
    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        self.workspace = self.directory / "workspace"
        self.metadata = json.loads((self.directory / "run.json").read_text())
        self.project = self.metadata["project"]
        self.profile_path = self.workspace / "projects" / self.project / "profile.json"
        self.profile = json.loads(self.profile_path.read_text())

    @classmethod
    def create(cls, root: Path, directory: Path, project: str):
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", project):
            raise ValueError("Project must be a directory name under projects/")
        root = root.resolve()
        profile = root / "projects" / project / "profile.json"
        if not profile.is_file():
            raise ValueError(f"Missing profile: {profile}")
        directory.mkdir(parents=True, exist_ok=False)
        workspace = directory / "workspace"
        for name in (".agents", "schemas", "projects", "java"):
            shutil.copytree(root / name, workspace / name,
                            ignore=shutil.ignore_patterns("target", "__pycache__", "*.pyc"))
        write_json(directory / "run.json", {"project": project, "source_root": str(root)})
        return cls(directory)

    def json(self, name: str):
        return json.loads((self.directory / name).read_text(encoding="utf-8"))

    def save(self, name: str, data) -> None:
        write_json(self.directory / name, data)

    def source_files(self, target: str) -> dict[str, str]:
        folder = self.workspace / "java/src" / target / "java"
        return {str(p.relative_to(self.workspace)): p.read_text(encoding="utf-8")
                for p in sorted(folder.rglob("*.java"))}

    def source_digest(self, target: str) -> str:
        return hashlib.sha256(json.dumps(self.source_files(target), sort_keys=True).encode()).hexdigest()

    def validate_sources(self, files: list[dict], target: str, *, append_only=False) -> list:
        if target not in {"original", "refactored", "test"} or not isinstance(files, list) or not files:
            raise ValueError("Expected a nonempty Java source batch and a known target")
        allowed = (self.workspace / "java/src" / target / "java").resolve()
        pending = []
        seen = set()
        for item in files:
            if not isinstance(item, dict) or set(item) != {"path", "content"}:
                raise ValueError("A source needs only path and content")
            relative = Path(item["path"])
            path = (self.workspace / relative).resolve()
            if (relative.is_absolute() or ".." in relative.parts or path.suffix != ".java"
                    or not path.is_relative_to(allowed) or path in seen):
                raise ValueError(f"Disallowed {target} source path: {relative}")
            if not isinstance(item["content"], str) or not item["content"].strip():
                raise ValueError("Java source must be nonempty text")
            if append_only and path.exists() and path.read_text() != item["content"]:
                raise ValueError(f"Cannot replace existing test: {relative}")
            seen.add(path)
            pending.append((path, item["content"]))
        return pending

    def write_sources(self, files: list[dict], target: str, *, append_only=False,
                      replace_tree=False, reason="source update") -> None:
        pending = self.validate_sources(files, target, append_only=append_only)
        changes = []
        if replace_tree:
            if target != "refactored":
                raise ValueError("Only a complete refactor can replace a source tree")
            retained = {path for path, _ in pending}
            for old in sorted((self.workspace / "java/src/refactored/java").rglob("*.java")):
                if old.resolve() not in retained:
                    changes.extend(difflib.unified_diff(
                        old.read_text().splitlines(True), [],
                        fromfile=str(old.relative_to(self.workspace)), tofile="/dev/null"))
                    old.unlink()
        for path, content in pending:
            before = path.read_text(encoding="utf-8") if path.exists() else ""
            changes.extend(difflib.unified_diff(before.splitlines(True), content.splitlines(True),
                                               fromfile=str(path.relative_to(self.workspace)),
                                               tofile=str(path.relative_to(self.workspace))))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        if changes:
            change = f"changes/{uuid4().hex}.diff"
            (self.directory / "changes").mkdir(exist_ok=True)
            (self.directory / change).write_text("".join(changes), encoding="utf-8")
            with (self.directory / "changelog.md").open("a", encoding="utf-8") as log:
                log.write(f"- {reason}: [{target} diff]({change})\n")

    def helper(self, name: str, *args: str) -> str:
        if name not in {"merge_cases", "review_cases", "materialize_junit"}:
            raise ValueError("Unknown testgen helper")
        command = [sys.executable, str(self.workspace / ".agents/testgen" / f"{name}.py"),
                   *map(str, args)]
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=60,
                                env=child_environment(), cwd=self.workspace)
        if result.returncode:
            raise ValueError(f"{name}: {result.stdout}\n{result.stderr}")
        return result.stdout
