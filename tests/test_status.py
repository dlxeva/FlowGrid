"""Tests for flg status command."""

import json
import os

from typer.testing import CliRunner

from flg.cli import app

runner = CliRunner()


def test_status_reads_legacy_state_schema(tmp_path):
    """Status should work on legacy skill-written state files via compatibility reader."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        flg_dir = tmp_path / ".flg"
        flg_dir.mkdir()
        legacy_state = {
            "project_name": "Legacy Status Project",
            "created": "2026-07-01",
            "updated": "2026-07-02",
            "phase": "legacy-phase",
            "version": "0.1.0",
            "pending_patches": [],
        }
        (flg_dir / "state.json").write_text(json.dumps(legacy_state, ensure_ascii=False), encoding="utf-8")
        (flg_dir / "CONTRACT.md").write_text("# Contract", encoding="utf-8")

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "Legacy Status Project" in result.output
        assert "legacy-phase" in result.output
        assert "0.1.0" in result.output
    finally:
        os.chdir(old_cwd)
