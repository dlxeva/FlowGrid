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
    assert (tmp_dir / "GOAL_EVOLUTION.md").exists()
    assert (tmp_dir / "CONSTRAINTS.md").exists()
    
    # Check .flg directory structure
    assert (tmp_dir / ".flg").is_dir()
    assert (tmp_dir / ".flg" / "CONTRACT.md").exists()
    assert (tmp_dir / ".flg" / "state.json").exists()
    assert (tmp_dir / ".flg" / "index.json").exists()
    assert (tmp_dir / ".flg" / "patches").is_dir()
    assert (tmp_dir / ".flg" / "sessions").is_dir()
    assert (tmp_dir / ".flg" / "memory").is_dir()
    assert ".flg/" in (tmp_dir / ".gitignore").read_text(encoding="utf-8")


def test_init_keeps_existing_gitignore_and_adds_flg_privacy_rule(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        (tmp_path / ".gitignore").write_text("dist/\n", encoding="utf-8")
        result = runner.invoke(app, ["init", "Gitignore Test"])
        assert result.exit_code == 0
        content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
        assert "dist/" in content
        assert ".flg/" in content
    finally:
        os.chdir(old_cwd)


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


def test_init_creates_goal_evolution_md(tmp_dir):
    """Test that flg init creates GOAL_EVOLUTION.md."""
    result = runner.invoke(app, ["init", "Test Project"])
    assert result.exit_code == 0
    path = tmp_dir / "GOAL_EVOLUTION.md"
    assert path.exists()
    content = path.read_text()
    assert "Goal Evolution" in content
    assert "Goal Shift" in content


def test_init_creates_constraints_md(tmp_dir):
    """Test that flg init creates CONSTRAINTS.md."""
    result = runner.invoke(app, ["init", "Test Project"])
    assert result.exit_code == 0
    path = tmp_dir / "CONSTRAINTS.md"
    assert path.exists()
    content = path.read_text()
    assert "Constraint Blocks" in content
    assert "If:" in content


def test_init_strategy_template_seeds_role_specific_content(tmp_dir):
    """Template init should seed role-specific framing and constraint hints."""
    result = runner.invoke(app, ["init", "Strategy Project", "--template", "strategy"])
    assert result.exit_code == 0

    framing_content = (tmp_dir / "FRAMING.md").read_text()
    constraints_content = (tmp_dir / "CONSTRAINTS.md").read_text()
    goal_evolution_content = (tmp_dir / "GOAL_EVOLUTION.md").read_text()

    assert "评审逻辑" in framing_content
    assert "strategy lead" in constraints_content
    assert "Clarify business goal" in goal_evolution_content


# --- 发现 8: --dir option + path display ---

def test_init_with_dir_option_creates_in_target(tmp_path):
    """--dir should create the project in the specified directory, not cwd.

    Regression for 发现 8: init used to always use cwd. Running
    `cd flg-repo && flg init NAME` polluted the flg source tree because
    the user expected the NAME argument to also determine the target dir.
    """
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        target = tmp_path / "my-project"
        result = runner.invoke(app, ["init", "Dir Test", "--dir", str(target)])
        assert result.exit_code == 0
        assert "FlowGrid project initialized" in result.output

        # Files must be in the target dir, NOT in cwd (tmp_path)
        assert (target / "PROJECT.md").exists()
        assert (target / ".flg" / "state.json").exists()
        # cwd should NOT have project files
        assert not (tmp_path / "PROJECT.md").exists()
    finally:
        os.chdir(old_cwd)


def test_init_with_dir_creates_missing_directory(tmp_path):
    """--dir should create the target directory if it does not exist."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        target = tmp_path / "nested" / "deep" / "project"
        result = runner.invoke(app, ["init", "Nested Test", "--dir", str(target)])
        assert result.exit_code == 0
        assert (target / "PROJECT.md").exists()
    finally:
        os.chdir(old_cwd)


def test_init_output_shows_creation_path(tmp_path):
    """Success output must show where files were created.

    Regression for 发现 9: init said 'success' without showing the path,
    so users couldn't tell if files landed in the right place.
    """
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["init", "Path Display Test"])
        assert result.exit_code == 0
        assert "Created in:" in result.output
        # Rich may truncate long paths in terminal output, so check the
        # path directory name appears rather than the full absolute path.
        assert tmp_path.name in result.output
    finally:
        os.chdir(old_cwd)


def test_init_existing_project_shows_location(tmp_path):
    """When init hits an existing FLG project, show its path."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "First"])
        result = runner.invoke(app, ["init", "Second"])
        assert result.exit_code == 0
        assert "already a FLG project" in result.output
        assert "Location:" in result.output
    finally:
        os.chdir(old_cwd)


# --- 发现 6: docs/ materials zone ---

def test_init_creates_docs_directory(tmp_dir):
    """init should create docs/ for project materials (发现 6)."""
    result = runner.invoke(app, ["init", "Docs Test"])
    assert result.exit_code == 0
    assert (tmp_dir / "docs").is_dir()


def test_init_creates_docs_readme(tmp_dir):
    """docs/README.md should exist as the materials index."""
    result = runner.invoke(app, ["init", "Docs README Test"])
    assert result.exit_code == 0
    readme = tmp_dir / "docs" / "README.md"
    assert readme.exists()
    content = readme.read_text()
    assert "素材" in content or "materials" in content.lower()
    assert "索引" in content or "index" in content.lower()


def test_init_english_language_generates_english_ledger(tmp_dir):
    result = runner.invoke(app, ["init", "English Project", "--language", "en"])
    assert result.exit_code == 0

    state = json.loads((tmp_dir / ".flg" / "state.json").read_text())
    assert state["language"] == "en"
    decisions = (tmp_dir / "DECISIONS.md").read_text()
    assert "### Decision Rationale" in decisions
    assert "### 决策理由" not in decisions

    result = runner.invoke(
        app,
        [
            "decision",
            "add",
            "--decision",
            "Keep the pilot narrow",
            "--rationale",
            "The evidence is still limited",
        ],
    )
    assert result.exit_code == 0
    decisions = (tmp_dir / "DECISIONS.md").read_text()
    assert "### Final Decision" in decisions
    assert "### Decision Rationale" in decisions
