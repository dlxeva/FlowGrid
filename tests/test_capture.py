"""Tests for background capture processing."""

import os

from typer.testing import CliRunner

from flg.cli import app


runner = CliRunner()


def test_auto_confirm_keeps_inferred_capture_pending(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert runner.invoke(app, ["init", "Capture Background Test"]).exit_code == 0
        result = runner.invoke(
            app,
            [
                "capture",
                "add",
                "--claim",
                "Maybe use a smaller experiment",
                "--rationale",
                "It is cheaper and reversible",
            ],
        )
        assert result.exit_code == 0

        result = runner.invoke(app, ["capture", "review", "--auto-confirm"])

        assert result.exit_code == 0
        assert "Kept pending" in result.output
        assert "Maybe use a smaller experiment" not in (tmp_path / "DECISIONS.md").read_text()
    finally:
        os.chdir(old_cwd)


def test_auto_confirm_processes_explicitly_confirmed_capture(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert runner.invoke(app, ["init", "Capture Confirmed Test"]).exit_code == 0
        result = runner.invoke(
            app,
            [
                "capture",
                "add",
                "--claim",
                "Use the smaller experiment",
                "--rationale",
                "It is cheaper and reversible",
                "--confidence",
                "confirmed",
            ],
        )
        assert result.exit_code == 0

        result = runner.invoke(app, ["capture", "review", "--auto-confirm"])

        assert result.exit_code == 0
        assert "decision(s) written" in result.output
        assert "Use the smaller experiment" in (tmp_path / "DECISIONS.md").read_text()
    finally:
        os.chdir(old_cwd)
