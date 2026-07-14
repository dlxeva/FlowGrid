"""Tests for doctor and evidence index rebuilding."""

import json
import os

from typer.testing import CliRunner

from flg.cli import app

runner = CliRunner()


def _project(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    runner.invoke(app, ["init", "Integrity Test"])
    return old_cwd


def test_reindex_rebuilds_index_from_formal_ledger(tmp_path):
    old_cwd = _project(tmp_path)
    try:
        result = runner.invoke(
            app,
            [
                "decision",
                "add",
                "--decision",
                "Use the local ledger as source of truth",
                "--rationale",
                "It is inspectable and durable",
            ],
        )
        assert result.exit_code == 0
        index_path = tmp_path / ".flg" / "context" / "evidence_index.json"
        index_path.write_text(json.dumps({"version": 1, "items": {"D-999": {}}}), encoding="utf-8")

        result = runner.invoke(app, ["reindex"])
        assert result.exit_code == 0
        data = json.loads(index_path.read_text(encoding="utf-8"))
        assert "D-999" not in data["items"]
        assert any("local ledger as source of truth" in item["title"] for item in data["items"].values())
        assert data["rebuilt_from"] == "DECISIONS.md"
    finally:
        os.chdir(old_cwd)


def test_doctor_reports_index_drift_without_writing(tmp_path):
    old_cwd = _project(tmp_path)
    try:
        runner.invoke(
            app,
            [
                "decision",
                "add",
                "--decision",
                "Keep evidence local",
                "--rationale",
                "Local files are auditable",
            ],
        )
        index_path = tmp_path / ".flg" / "context" / "evidence_index.json"
        index_path.write_text(json.dumps({"version": 1, "items": {"D-999": {}}}), encoding="utf-8")
        before = index_path.read_text(encoding="utf-8")

        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "Needs attention" in result.output
        assert "orphan_index:" in result.output
        assert index_path.read_text(encoding="utf-8") == before
    finally:
        os.chdir(old_cwd)
