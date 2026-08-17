"""Regression tests for selecting the checkout under test in smoke runs."""

import os
from pathlib import Path

from scripts import smoke_test


def test_source_tree_fallback_preserves_dependency_pythonpath(monkeypatch, tmp_path):
    """The source checkout must win without hiding dependencies from subprocesses."""
    monkeypatch.setattr(smoke_test, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(smoke_test.sys, "executable", "/usr/bin/python3")
    monkeypatch.setenv("PYTHONPATH", "/tmp/dependency-site")

    command, environment, mode = smoke_test.resolve_flg_command()

    assert command == ["/usr/bin/python3", "-m", "flg.cli"]
    assert environment == {
        "PYTHONPATH": os.pathsep.join(
            (str(tmp_path / "src"), "/tmp/dependency-site")
        )
    }
    assert mode == "repository source tree"


def test_forced_source_tree_ignores_sibling_console_script(monkeypatch, tmp_path):
    monkeypatch.setattr(smoke_test, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(smoke_test.sys, "executable", "/venv/bin/python")
    monkeypatch.setenv("FLOWGRID_SMOKE_SOURCE", "1")
    monkeypatch.setenv("PYTHONPATH", "/tmp/dependency-site")

    command, environment, mode = smoke_test.resolve_flg_command()

    assert command == ["/venv/bin/python", "-m", "flg.cli"]
    assert environment == {
        "PYTHONPATH": os.pathsep.join(
            (str(tmp_path / "src"), "/tmp/dependency-site")
        )
    }
    assert mode == "forced repository source tree"
