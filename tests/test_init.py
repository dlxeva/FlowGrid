"""Tests for flg init command."""

import json
import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from flg import __version__
from flg.cli import app

runner = CliRunner()


@pytest.fixture
def tmp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        yield Path(tmpdir)
        os.chdir(old_cwd)


def test_init_creates_project_structure(tmp_dir):
    """Test that flg init creates the expected project structure."""
    result = runner.invoke(app, ["init", "Test Project"])
    assert result.exit_code == 0
    assert "FlowGrid project initialized" in result.output
    
    # Check core files exist
    assert (tmp_dir / "PROJECT.md").exists()
    assert (tmp_dir / "FRAMING.md").exists()
    assert (tmp_dir / "DECISIONS.md").exists()
    assert (tmp_dir / "SNAPSHOT.md").exists()
    assert (tmp_dir / "PROGRESS.md").exists()
    
    # Check .flg directory structure
    assert (tmp_dir / ".flg").is_dir()
    assert (tmp_dir / ".flg" / "CONTRACT.md").exists()
    assert (tmp_dir / ".flg" / "state.json").exists()
    assert (tmp_dir / ".flg" / "index.json").exists()
    assert (tmp_dir / ".flg" / "patches").is_dir()
    assert (tmp_dir / ".flg" / "sessions").is_dir()
    assert (tmp_dir / ".flg" / "memory").is_dir()


def test_init_creates_valid_state(tmp_dir):
    """Test that flg init creates a valid state.json."""
    runner.invoke(app, ["init", "Test Project"])
    
    state_path = tmp_dir / ".flg" / "state.json"
    state = json.loads(state_path.read_text())
    
    assert state["project_name"] == "Test Project"
    assert state["flg_version"] == __version__
    assert state["current_stage"] == "initialized"
    assert state["pending_patches"] == []


def test_init_with_options(tmp_dir):
    """Test flg init with various options."""
    result = runner.invoke(app, [
        "init", "Client Project",
        "--type", "proposal",
        "--client", "Acme Corp",
        "--background", "Urgent launch campaign"
    ])
    assert result.exit_code == 0
    
    project_content = (tmp_dir / "PROJECT.md").read_text()
    assert "Client Project" in project_content
    assert "Acme Corp" in project_content


def test_init_does_not_overwrite_existing(tmp_dir):
    """Test that flg init does not overwrite existing files."""
    # First init
    runner.invoke(app, ["init", "First Project"])
    
    # Get original PROJECT.md content
    original = (tmp_dir / "PROJECT.md").read_text()
    
    # Second init
    result = runner.invoke(app, ["init", "Second Project"])
    assert result.exit_code == 0
    assert "already a FLG project" in result.output
    
    # Verify PROJECT.md not changed
    current = (tmp_dir / "PROJECT.md").read_text()
    assert current == original


def test_init_allows_directory_with_stray_flg_folder(tmp_path):
    """A stray .flg directory alone should not block project initialization."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        (tmp_path / ".flg" / "patches").mkdir(parents=True)
        result = runner.invoke(app, ["init", "Recovered Project"])
        assert result.exit_code == 0
        assert "FlowGrid project initialized" in result.output
        assert (tmp_path / ".flg" / "CONTRACT.md").exists()
        assert (tmp_path / ".flg" / "state.json").exists()
    finally:
        os.chdir(old_cwd)


def test_init_creates_rationale_dir(tmp_dir):
    """Test that flg init creates the rationale/ directory."""
    result = runner.invoke(app, ["init", "Test Project"])
    assert result.exit_code == 0
    assert (tmp_dir / "rationale").is_dir()


def test_init_creates_rationale_trail(tmp_dir):
    """Test that flg init creates RATIONALE_TRAIL.md."""
    result = runner.invoke(app, ["init", "Test Project"])
    assert result.exit_code == 0
    rationale_path = tmp_dir / "RATIONALE_TRAIL.md"
    assert rationale_path.exists()
    content = rationale_path.read_text()
    assert "Rationale Trail" in content
    assert "思考过程" in content


def test_init_creates_lessons_learned(tmp_dir):
    """Test that flg init creates LESSONS_LEARNED.md."""
    result = runner.invoke(app, ["init", "Test Project"])
    assert result.exit_code == 0
    lessons_path = tmp_dir / "LESSONS_LEARNED.md"
    assert lessons_path.exists()
    content = lessons_path.read_text()
    assert "Lessons Learned" in content
    assert "可复用经验" in content


def test_init_creates_anchors_md(tmp_dir):
    """Test that flg init creates ANCHORS.md."""
    result = runner.invoke(app, ["init", "Test Project"])
    assert result.exit_code == 0
    anchors_path = tmp_dir / "ANCHORS.md"
    assert anchors_path.exists()
    content = anchors_path.read_text()
    assert "Authoritative Anchors" in content
    assert "权威锚点" in content
    assert "authoritative" in content
    assert "Provenance" in content
    assert "Lifecycle" in content
