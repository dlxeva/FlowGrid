"""Tests for flg merge command."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from flg.cli import app

runner = CliRunner()


@pytest.fixture
def flg_project_with_patch(tmp_path):
    """Create a FLG project with a closeout patch."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    # Initialize project
    result = runner.invoke(app, ["init", "Merge Test"])
    assert result.exit_code == 0
    
    # Create transcript
    transcript = tmp_path / "session.md"
    transcript.write_text("""# Session

We decided to focus on content marketing.
There's a risk that KOLs are too expensive.
Next step is to confirm budget.
""")
    
    # Generate closeout patch
    result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
    assert result.exit_code == 0
    
    yield tmp_path
    os.chdir(old_cwd)


def test_merge_dry_run(flg_project_with_patch):
    """Test that merge --dry-run doesn't modify files."""
    patches_dir = flg_project_with_patch / ".flg" / "patches"
    patch_files = list(patches_dir.glob("closeout-*.patch.md"))
    assert len(patch_files) > 0
    
    # Get original PROGRESS.md
    progress_before = (flg_project_with_patch / "PROGRESS.md").read_text()
    
    # Run merge --dry-run
    result = runner.invoke(app, ["merge", "--patch", patch_files[0].name, "--dry-run"])
    assert result.exit_code == 0
    assert "Dry run" in result.output
    
    # Verify no changes
    progress_after = (flg_project_with_patch / "PROGRESS.md").read_text()
    assert progress_before == progress_after


def test_merge_updates_progress(flg_project_with_patch):
    """Test that merge appends to PROGRESS.md."""
    patches_dir = flg_project_with_patch / ".flg" / "patches"
    patch_files = list(patches_dir.glob("closeout-*.patch.md"))
    assert len(patch_files) > 0
    
    # Run merge (auto-confirm)
    result = runner.invoke(app, ["merge", "--patch", patch_files[0].name], input="y\n")
    assert result.exit_code == 0
    assert "Merge complete" in result.output
    
    # Verify PROGRESS.md updated
    progress_content = (flg_project_with_patch / "PROGRESS.md").read_text()
    assert "Session Progress" in progress_content


def test_merge_updates_snapshot(flg_project_with_patch):
    """Test that merge updates SNAPSHOT.md with risks."""
    patches_dir = flg_project_with_patch / ".flg" / "patches"
    patch_files = list(patches_dir.glob("closeout-*.patch.md"))
    assert len(patch_files) > 0
    
    # Run merge
    result = runner.invoke(app, ["merge", "--patch", patch_files[0].name], input="y\n")
    assert result.exit_code == 0
    
    # Verify SNAPSHOT.md updated
    snapshot_content = (flg_project_with_patch / "SNAPSHOT.md").read_text()
    assert "KOLs" in snapshot_content or "risk" in snapshot_content.lower()


def test_merge_creates_log(flg_project_with_patch):
    """Test that merge creates a merge log."""
    patches_dir = flg_project_with_patch / ".flg" / "patches"
    patch_files = list(patches_dir.glob("closeout-*.patch.md"))
    assert len(patch_files) > 0
    
    # Run merge
    result = runner.invoke(app, ["merge", "--patch", patch_files[0].name], input="y\n")
    assert result.exit_code == 0
    
    # Verify merge log created
    merge_logs_dir = flg_project_with_patch / ".flg" / "merge_logs"
    assert merge_logs_dir.exists()
    log_files = list(merge_logs_dir.glob("*.md"))
    assert len(log_files) > 0


def test_merge_on_nonexistent_patch(flg_project_with_patch):
    """Test that merge fails on nonexistent patch."""
    result = runner.invoke(app, ["merge", "--patch", "nonexistent.patch.md"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_merge_on_non_flg_project(tmp_path):
    """Test that merge fails on non-FLG project."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    result = runner.invoke(app, ["merge", "--patch", "test.patch.md"])
    assert result.exit_code == 1
    assert "Not a FLG project" in result.output
    
    os.chdir(old_cwd)
