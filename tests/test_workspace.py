from pathlib import Path

import pytest

from harness.workspace import RunWorkspace


ROOT = Path(__file__).resolve().parents[1]


def test_workspace_copies_inputs_without_editing_repository(tmp_path):
    run = RunWorkspace.create(ROOT, tmp_path / "run", "seasonswitch")
    source = "java/src/original/java/cse4392/SeasonSwitch.java"
    assert (run.workspace / source).read_bytes() == (ROOT / source).read_bytes()
    run.write_sources([{"path": source, "content": "changed"}], "original")
    assert (run.workspace / source).read_text() == "changed"
    assert "class SeasonSwitch" in (ROOT / source).read_text()


@pytest.mark.parametrize("path", ["../escape.java", "/tmp/escape.java", "java/pom.xml",
                                  "java/src/test/java/Bad.java"])
def test_model_source_writes_cannot_escape_their_target(tmp_path, path):
    run = RunWorkspace.create(ROOT, tmp_path / "run", "seasonswitch")
    with pytest.raises(ValueError):
        run.write_sources([{"path": path, "content": "bad"}], "refactored")


def test_invalid_source_batch_writes_nothing(tmp_path):
    run = RunWorkspace.create(ROOT, tmp_path / "run", "seasonswitch")
    target = "java/src/refactored/java/Good.java"
    with pytest.raises(ValueError):
        run.write_sources([{"path": target, "content": "good"},
                           {"path": "../../bad.java", "content": "bad"}], "refactored")
    assert not (run.workspace / target).exists()


def test_supplemental_tests_cannot_replace_existing_tests(tmp_path):
    run = RunWorkspace.create(ROOT, tmp_path / "run", "seasonswitch")
    files = [{"path": "java/src/test/java/ExtraTest.java", "content": "original assertions"}]
    run.write_sources(files, "test", append_only=True)
    with pytest.raises(ValueError, match="existing"):
        run.write_sources([{**files[0], "content": "weakened"}], "test", append_only=True)
