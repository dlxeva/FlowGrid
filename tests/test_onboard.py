"""Tests for flg onboard command."""

import os
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from flg.cli import app
from flg.commands.onboard import detect_hosts, check_skill_installed, install_skill

runner = CliRunner()


def test_onboard_env_check_on_fresh_dir(tmp_path):
    """Onboard on a directory with no FLG project should report it."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["onboard", "--skip-demo", "--yes"])
        assert result.exit_code == 0
        assert "Environment Check" in result.output
        assert "FLG version" in result.output
        assert "not an FLG project" in result.output
    finally:
        os.chdir(old_cwd)


def test_onboard_env_check_on_existing_project(tmp_path):
    """Onboard on an existing FLG project should detect it."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Existing Project"])
        result = runner.invoke(app, ["onboard", "--skip-demo", "--yes"])
        assert result.exit_code == 0
        assert "FLG project detected" in result.output
    finally:
        os.chdir(old_cwd)


def test_onboard_demo_full_loop(tmp_path):
    """The guided demo should produce DECISIONS.md content and a context pack."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["onboard", "--yes"])
        assert result.exit_code == 0
        assert "Demo complete" in result.output

        # The demo should have created project files
        assert (tmp_path / "DECISIONS.md").exists()
        assert (tmp_path / ".flg" / "context" / "startup.md").exists()

        # DECISIONS.md should have at least the template D-001 placeholder
        decisions = (tmp_path / "DECISIONS.md").read_text(encoding="utf-8")
        assert "## D-" in decisions
    finally:
        os.chdir(old_cwd)


def test_onboard_skip_demo(tmp_path):
    """--skip-demo should skip Phase 2 entirely."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["onboard", "--skip-demo", "--yes"])
        assert result.exit_code == 0
        assert "Skipping demo" in result.output
        # No project should have been created
        assert not (tmp_path / ".flg").exists()
    finally:
        os.chdir(old_cwd)


def test_detect_hosts_returns_installed_hosts(tmp_path):
    """detect_hosts should detect a host without relying on the developer machine."""
    (tmp_path / ".codex" / "skills").mkdir(parents=True)

    with patch("flg.commands.onboard.Path.home", return_value=tmp_path):
        hosts = detect_hosts()

    assert [host["name"] for host in hosts] == ["codex"]
    assert hosts[0]["skill_installed"] is False


def test_install_skill_creates_symlink(tmp_path):
    """install_skill should create a symlink from target to source."""
    # Create a fake skill source
    skill_source = tmp_path / "skill-source" / "flowgrid-operator"
    skill_source.mkdir(parents=True)
    (skill_source / "SKILL.md").write_text("# Fake skill", encoding="utf-8")

    # Create a fake host skills dir
    host_skills = tmp_path / "host" / "skills"

    result = install_skill(host_skills, skill_source)
    assert result is True

    target = host_skills / "flowgrid-operator"
    assert target.is_symlink() or target.is_dir()
    assert (target / "SKILL.md").exists()


def test_install_skill_already_installed(tmp_path):
    """install_skill should return True if skill already exists."""
    skill_source = tmp_path / "skill-source" / "flowgrid-operator"
    skill_source.mkdir(parents=True)
    (skill_source / "SKILL.md").write_text("# Fake skill", encoding="utf-8")

    host_skills = tmp_path / "host" / "skills"
    host_skills.mkdir(parents=True)
    # Pre-create the target
    target = host_skills / "flowgrid-operator"
    target.mkdir()
    (target / "SKILL.md").write_text("# Already here", encoding="utf-8")

    result = install_skill(host_skills, skill_source)
    assert result is True  # already installed, returns True


def test_check_skill_installed(tmp_path):
    """check_skill_installed should detect existing skill."""
    skill_path = tmp_path / "flowgrid-operator"
    assert check_skill_installed(skill_path) is False

    skill_path.mkdir()
    assert check_skill_installed(skill_path) is True
