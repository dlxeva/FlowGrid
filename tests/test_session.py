"""Tests for raw session archiving."""

import os

from typer.testing import CliRunner

from flg.cli import app

runner = CliRunner()


def test_session_save_archives_raw_transcript(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Session Test"])
        source = tmp_path / "raw-chat.md"
        source.write_text("User: We chose the local-first path.\n", encoding="utf-8")

        result = runner.invoke(app, ["session", "save", str(source), "--name", "session-001"])
        assert result.exit_code == 0
        archived = tmp_path / ".flg" / "sessions" / "session-001.md"
        assert archived.exists()
        assert archived.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    finally:
        os.chdir(old_cwd)


def test_session_save_rejects_structured_ledger(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Session Guard Test"])
        result = runner.invoke(app, ["session", "save", "DECISIONS.md"])
        assert result.exit_code != 0
        assert "structured ledger" in result.output
    finally:
        os.chdir(old_cwd)


def test_closeout_archives_external_transcript(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Automatic Archive Test"])
        source = tmp_path / "outside" / "raw-chat.md"
        source.parent.mkdir()
        source.write_text("We decided to keep the pilot narrow because evidence is limited.\n", encoding="utf-8")

        result = runner.invoke(app, ["closeout", "--transcript", str(source), "--no-llm"])
        assert result.exit_code == 0
        archives = list((tmp_path / ".flg" / "sessions").glob("*.md"))
        assert len(archives) == 1
        assert archives[0].read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        assert str(archives[0]) in patch.read_text(encoding="utf-8")
    finally:
        os.chdir(old_cwd)
