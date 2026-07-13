"""Tests for flg patch lifecycle commands (supersede / discard).

发现 2: stale patches had no official retirement path. Users had to
hand-edit state.json. These tests verify the new `flg patch supersede`
and `flg patch discard` commands update both state.json and the patch
file's status line, and that `flg status` then stops warning about them.
"""

import glob
import json
import os
import os.path

from typer.testing import CliRunner

from flg.cli import app

runner = CliRunner()


def _make_project_with_patch(tmp_path, project_name="Patch Lifecycle Test"):
    """Init a project and generate a closeout patch, return (patch_filename, patch_id)."""
    runner.invoke(app, ["init", project_name])

    transcript = tmp_path / "session.md"
    transcript.write_text("""# Session

我们确认采用方案A。
因为方案A的ROI更高。
放弃方案B，因为成本太高。
""", encoding="utf-8")
    runner.invoke(app, ["closeout", "--transcript", str(transcript), "--no-llm"])

    patch_files = glob.glob(str(tmp_path / ".flg" / "patches" / "closeout-*.patch.md"))
    assert patch_files, "No closeout patch was generated"
    patch_path = patch_files[0]

    # Extract patch_id from file content
    content = open(patch_path, encoding="utf-8").read()
    patch_id = None
    for line in content.split("\n"):
        if line.startswith("patch_id:"):
            patch_id = line.split(":", 1)[1].strip()
            break

    return os.path.basename(patch_path), patch_id


def test_patch_supersede_updates_state_and_file(tmp_path):
    """`flg patch supersede` must update state.json status and patch file status line."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        patch_filename, patch_id = _make_project_with_patch(tmp_path)

        result = runner.invoke(app, ["patch", "supersede", patch_filename, "--reason", "replaced by newer frame"])
        assert result.exit_code == 0
        assert "superseded" in result.output

        # state.json should reflect superseded
        state = json.loads((tmp_path / ".flg" / "state.json").read_text(encoding="utf-8"))
        patch_entry = next(p for p in state["pending_patches"] if p["patch_id"] == patch_id)
        assert patch_entry["status"] == "superseded"
        assert "superseded_at" in patch_entry

        # patch file should have updated status line + lifecycle note
        content = (tmp_path / ".flg" / "patches" / patch_filename).read_text(encoding="utf-8")
        assert "status: superseded" in content
        assert "Lifecycle Note" in content
        assert "replaced by newer frame" in content
    finally:
        os.chdir(old_cwd)


def test_patch_discard_updates_state_and_file(tmp_path):
    """`flg patch discard` must update state.json status and patch file status line."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        patch_filename, patch_id = _make_project_with_patch(tmp_path)

        result = runner.invoke(app, ["patch", "discard", patch_filename, "--reason", "false positive"])
        assert result.exit_code == 0
        assert "rejected" in result.output

        state = json.loads((tmp_path / ".flg" / "state.json").read_text(encoding="utf-8"))
        patch_entry = next(p for p in state["pending_patches"] if p["patch_id"] == patch_id)
        assert patch_entry["status"] == "rejected"

        content = (tmp_path / ".flg" / "patches" / patch_filename).read_text(encoding="utf-8")
        assert "status: rejected" in content
        assert "false positive" in content
    finally:
        os.chdir(old_cwd)


def test_patch_supersede_then_status_no_warning(tmp_path):
    """After superseding, `flg status` must NOT warn about the patch (发现 16/4 integration)."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        patch_filename, _ = _make_project_with_patch(tmp_path)

        # Before supersede: status should warn
        result = runner.invoke(app, ["status"])
        assert "⚠" in result.output

        # Supersede it
        runner.invoke(app, ["patch", "supersede", patch_filename])

        # After supersede: status should NOT warn
        result = runner.invoke(app, ["status"])
        assert "⚠" not in result.output
        assert "No pending patches needing review" in result.output
        assert "superseded" in result.output.lower()
    finally:
        os.chdir(old_cwd)


def test_patch_supersede_by_patch_id(tmp_path):
    """supersede should work with patch_id, not just filename."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        _, patch_id = _make_project_with_patch(tmp_path)

        result = runner.invoke(app, ["patch", "supersede", patch_id])
        assert result.exit_code == 0
        assert "superseded" in result.output
    finally:
        os.chdir(old_cwd)


def test_patch_supersede_nonexistent_fails(tmp_path):
    """supersede on a nonexistent patch should fail cleanly."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "No Patch Test"])
        result = runner.invoke(app, ["patch", "supersede", "nonexistent-patch"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()
    finally:
        os.chdir(old_cwd)
