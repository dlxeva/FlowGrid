"""Tests for flg frame command."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from flg.cli import app

runner = CliRunner()


@pytest.fixture
def flg_project(tmp_path):
    """Create a temporary FLG project for testing."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    # Initialize project
    result = runner.invoke(app, ["init", "Test Project"])
    assert result.exit_code == 0
    
    yield tmp_path
    os.chdir(old_cwd)


def test_frame_detects_missing_fields(flg_project):
    """Test that flg frame detects missing fields in FRAMING.md."""
    result = runner.invoke(app, ["frame"])
    assert result.exit_code == 0
    # Should detect missing fields and generate patch
    assert "missing" in result.output.lower() or "patch" in result.output.lower()


def test_frame_generates_patch(flg_project):
    """Test that flg frame generates a patch file."""
    result = runner.invoke(app, ["frame"])
    assert result.exit_code == 0
    
    patches_dir = flg_project / ".flg" / "patches"
    patch_files = list(patches_dir.glob("frame-*.patch.md"))
    assert len(patch_files) > 0, f"No frame patch found in {list(patches_dir.iterdir())}"
    
    # Verify patch content
    patch_content = patch_files[0].read_text()
    assert "FLG Patch" in patch_content
    assert "flg frame" in patch_content
    assert "pending_review" in patch_content


def test_frame_on_non_flg_project(tmp_path):
    """Test that flg frame fails on non-FLG project."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    result = runner.invoke(app, ["frame"])
    assert result.exit_code == 1
    assert "Not a FLG project" in result.output
    
    os.chdir(old_cwd)


def test_frame_with_complete_framing(flg_project):
    """Test flg frame when FRAMING.md is complete."""
    # Fill in FRAMING.md with real content
    framing_path = flg_project / "FRAMING.md"
    content = framing_path.read_text()
    
    # Replace placeholders with real content
    content = content.replace("(to be defined)", "Real content here")
    content = content.replace("(to be filled)", "Real content here")
    content = content.replace("(to be hypothesized)", "Real hypothesis")
    content = content.replace("(to be identified)", "- Question 1")
    content = content.replace("(none yet)", "- Risk 1")
    
    framing_path.write_text(content)
    
    result = runner.invoke(app, ["frame"])
    assert result.exit_code == 0
    # Should either say complete or generate a lighter patch
