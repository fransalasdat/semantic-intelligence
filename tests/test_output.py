from pathlib import Path
from unittest.mock import patch

import pytest

from semantic_intelligence.output import write_output


def windows_lock():
    error = PermissionError("temporary Windows sharing lock")
    error.winerror = 32
    return error


def test_transient_windows_lock_is_retried_without_losing_existing_file(tmp_path):
    destination = tmp_path / "report.json"
    destination.write_text("old", encoding="utf-8")
    import os
    original = os.replace
    calls = 0
    def replace(source, target):
        nonlocal calls
        calls += 1
        assert destination.read_text(encoding="utf-8") == "old"
        if calls == 1:
            raise windows_lock()
        original(source, target)
    with patch("semantic_intelligence.output.os.replace", side_effect=replace), patch("semantic_intelligence.output.time.sleep"):
        write_output("new", destination, tmp_path / "input")
    assert calls == 2
    assert destination.read_text(encoding="utf-8") == "new"


def test_permanent_lock_preserves_old_file_and_cleans_temporary_file(tmp_path):
    destination = tmp_path / "report.json"
    destination.write_text("old", encoding="utf-8")
    with patch("semantic_intelligence.output.os.replace", side_effect=windows_lock()) as replace, patch("semantic_intelligence.output.time.sleep"):
        with pytest.raises(PermissionError):
            write_output("new", destination, tmp_path / "input")
    assert replace.call_count == 6
    assert destination.read_text(encoding="utf-8") == "old"
    assert list(tmp_path.glob("*.tmp")) == []


def test_other_permission_errors_are_not_retried(tmp_path):
    with patch("semantic_intelligence.output.os.replace", side_effect=PermissionError("denied")) as replace, patch("semantic_intelligence.output.time.sleep") as sleep:
        with pytest.raises(PermissionError):
            write_output("new", tmp_path / "report.json", tmp_path / "input")
    assert replace.call_count == 1
    sleep.assert_not_called()
