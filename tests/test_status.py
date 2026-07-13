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


def test_status_does_not_warn_on_merged_patches(tmp_path):
    """Merged/rejected/superseded patches must NOT trigger the 'pending' warning.

    Regression for 发现 16/4: status used to scan .flg/patches/ and warn
    '⚠ pending patches' for ANY patch file, even after it was merged or
    rejected. Only pending_review patches should trigger the warning.
    """
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        flg_dir = tmp_path / ".flg"
        patches_dir = flg_dir / "patches"
        patches_dir.mkdir(parents=True)
        legacy_state = {
            "project_name": "Merged Patch Project",
            "created": "2026-07-01",
            "updated": "2026-07-02",
            "phase": "execution",
            "version": "0.1.0",
            "pending_patches": [
                {
                    "patch_id": "closeout-20260701-merged",
                    "risk_level": "medium",
                    "source_command": "flg closeout",
                    "created_at": "2026-07-01",
                    "status": "merged",
                },
                {
                    "patch_id": "frame-20260701-rejected",
                    "risk_level": "low",
                    "source_command": "flg frame",
                    "created_at": "2026-07-01",
                    "status": "rejected",
                },
            ],
        }
        (flg_dir / "state.json").write_text(json.dumps(legacy_state, ensure_ascii=False), encoding="utf-8")
        (flg_dir / "CONTRACT.md").write_text("# Contract", encoding="utf-8")

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        # No pending_review patches → must NOT show the ⚠ warning
        assert "⚠" not in result.output
        assert "No pending patches needing review" in result.output
        # Closed patches shown as audit summary
        assert "merged" in result.output.lower()
        assert "rejected" in result.output.lower()
    finally:
        os.chdir(old_cwd)


def test_status_warns_on_pending_review_patches(tmp_path):
    """pending_review patches must still trigger the warning."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        flg_dir = tmp_path / ".flg"
        patches_dir = flg_dir / "patches"
        patches_dir.mkdir(parents=True)
        legacy_state = {
            "project_name": "Pending Review Project",
            "created": "2026-07-01",
            "updated": "2026-07-02",
            "phase": "execution",
            "version": "0.1.0",
            "pending_patches": [
                {
                    "patch_id": "closeout-20260702-pending",
                    "risk_level": "medium",
                    "source_command": "flg closeout",
                    "created_at": "2026-07-02",
                    "status": "pending_review",
                },
            ],
        }
        (flg_dir / "state.json").write_text(json.dumps(legacy_state, ensure_ascii=False), encoding="utf-8")
        (flg_dir / "CONTRACT.md").write_text("# Contract", encoding="utf-8")

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        # Warning must trigger for pending_review patches
        assert "⚠" in result.output
        assert "1 pending patch" in result.output
        assert "pending_review" in result.output
    finally:
        os.chdir(old_cwd)
