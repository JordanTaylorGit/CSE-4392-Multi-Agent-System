
import pytest

from harness.build import read_reports


def reports(tmp_path, *, covered=3, missed=0, tests=1, failures=0, skipped=0):
    (tmp_path / "surefire").mkdir()
    (tmp_path / "surefire/TEST-Example.xml").write_text(
        f'<testsuite tests="{tests}" failures="{failures}" errors="0" skipped="{skipped}"/>')
    (tmp_path / "jacoco.xml").write_text(
        '<report><package name="x"><class name="X"><method name="testable">'
        f'<counter type="BRANCH" covered="{covered}" missed="{missed}"/>'
        '</method><method name="main"><counter type="BRANCH" covered="0" missed="8"/>'
        '</method><counter type="BRANCH" covered="3" missed="8"/>'
        '</class></package><counter type="BRANCH" covered="3" missed="8"/></report>')


def test_counts_branches_once_and_reports_main_exclusion(tmp_path):
    reports(tmp_path)
    result = read_reports(tmp_path, 0)
    assert result["covered"] == 3
    assert result["missed"] == 0
    assert result["excluded_main_branches"] == 8
    assert result["passed"] is True
    assert result["complete"] is True


@pytest.mark.parametrize("kwargs", [{"tests": 0}, {"failures": 1}, {"skipped": 1},
                                   {"covered": 0}, {"covered": 100000, "missed": 1}])
def test_empty_failed_skipped_or_incomplete_reports_never_pass_coverage(tmp_path, kwargs):
    reports(tmp_path, **kwargs)
    assert read_reports(tmp_path, 0)["complete"] is False


def test_missing_reports_fail_closed(tmp_path):
    result = read_reports(tmp_path, 0)
    assert result["passed"] is False
    assert result["complete"] is False


def test_process_failure_is_not_overridden_by_passing_xml(tmp_path):
    reports(tmp_path)
    assert read_reports(tmp_path, 1)["passed"] is False
