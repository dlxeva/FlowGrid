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

    patch_content = patch_files[0].read_text(encoding="utf-8")
    assert "status: merged" in patch_content
    assert "Merged into formal project state" in patch_content

    handoff = runner.invoke(app, ["handoff"])
    assert handoff.exit_code == 0
    assert "(no pending patches)" in handoff.output


def test_merge_autonomous_skips_interactive_prompt(flg_project_with_patch):
    """AI hosts can complete routine ledger maintenance without a user prompt."""
    patches_dir = flg_project_with_patch / ".flg" / "patches"
    patch_file = next(patches_dir.glob("closeout-*.patch.md"))

    result = runner.invoke(app, ["merge", "--patch", patch_file.name, "--yes"])

    assert result.exit_code == 0
    assert "Merge complete" in result.output
    assert "Proceed with merge?" not in result.output


def test_merge_autonomous_skips_interactive_prompt(flg_project_with_patch):
    """AI hosts can complete routine ledger maintenance without a user prompt."""
    patches_dir = flg_project_with_patch / ".flg" / "patches"
    patch_file = next(patches_dir.glob("closeout-*.patch.md"))

    result = runner.invoke(app, ["merge", "--patch", patch_file.name, "--yes"])

    assert result.exit_code == 0
    assert "Merge complete" in result.output
    assert "Proceed with merge?" not in result.output


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


def test_merge_rejects_closed_patch(flg_project_with_patch):
    """A rejected patch is audit history, never mergeable formal state."""
    patch = next((flg_project_with_patch / ".flg" / "patches").glob("closeout-*.patch.md"))
    result = runner.invoke(app, ["patch", "discard", patch.name, "--reason", "not applicable"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["merge", "--patch", patch.name, "--yes"])
    assert result.exit_code == 1
    assert "closed" in result.output.lower()


def test_merge_on_non_flg_project(tmp_path):
    """Test that merge fails on non-FLG project."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    result = runner.invoke(app, ["merge", "--patch", "test.patch.md"])
    assert result.exit_code == 1
    assert "Not a FLG project" in result.output
    
    os.chdir(old_cwd)


def test_merge_does_not_rewarn_after_review(tmp_path):
    """If candidate decisions were already accepted via review, merge should not warn again."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["init", "Merge Review Test"])
        assert result.exit_code == 0

        transcript = tmp_path / "session.md"
        transcript.write_text("""# Session

User: We decided to focus on content marketing.
User: Because content marketing has higher long-term ROI for our stage.
User: We ruled out paid ads because the budget is too tight this quarter.
User: There is a risk that KOLs are too expensive.
User: Next step is to confirm budget.
""", encoding="utf-8")

        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0

        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        result = runner.invoke(app, ["review", "--patch", patch.name, "--accept-all"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["merge", "--patch", patch.name], input="y\n")
        assert result.exit_code == 0
        assert "already accepted via flg review" in result.output
        assert "Please review and add to DECISIONS.md manually" not in result.output
    finally:
        os.chdir(old_cwd)


def test_background_merge_does_not_promote_candidate_risks_or_actions(tmp_path):
    """Candidate risks/actions stay in the patch until a separate confirmation path exists."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Snapshot Boundary Test"])
        transcript = tmp_path / "session.md"
        transcript.write_text(
            "User: We decided to use the smaller experiment because it is reversible.\n"
            "User: The risk is that the timeline will slip.\n"
            "Assistant: Next step is to buy a six-month vendor contract.\n",
            encoding="utf-8",
        )
        runner.invoke(app, ["closeout", "--transcript", str(transcript), "--no-llm"])
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        runner.invoke(app, ["review", "--patch", patch.name, "--autonomous"])
        result = runner.invoke(app, ["merge", "--patch", patch.name, "--yes"])
        assert result.exit_code == 0

        snapshot = (tmp_path / "SNAPSHOT.md").read_text(encoding="utf-8")
        assert "timeline will slip" not in snapshot
        assert "six-month vendor contract" not in snapshot
    finally:
        os.chdir(old_cwd)
