"""Tests for background capture processing."""

import json
import os
from datetime import datetime as RealDateTime

from typer.testing import CliRunner

from flg.cli import app
from flg.commands import capture as capture_command


runner = CliRunner()


def test_capture_ids_remain_unique_when_wall_clock_is_unchanged(monkeypatch):
    class FrozenDateTime:
        @classmethod
        def now(cls):
            return RealDateTime(2026, 8, 17, 14, 44, 8)

    monkeypatch.setattr(capture_command, "datetime", FrozenDateTime)

    assert capture_command._generate_id() != capture_command._generate_id()


def test_auto_confirm_keeps_inferred_capture_pending(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert runner.invoke(app, ["init", "Capture Background Test"]).exit_code == 0
        result = runner.invoke(
            app,
            [
                "capture",
                "add",
                "--claim",
                "Maybe use a smaller experiment",
                "--rationale",
                "It is cheaper and reversible",
            ],
        )
        assert result.exit_code == 0

        result = runner.invoke(app, ["capture", "review", "--auto-confirm"])

        assert result.exit_code == 0
        assert "Kept pending" in result.output
        assert "Maybe use a smaller experiment" not in (tmp_path / "DECISIONS.md").read_text()
    finally:
        os.chdir(old_cwd)


def test_auto_confirm_processes_explicitly_confirmed_capture(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert runner.invoke(app, ["init", "Capture Confirmed Test"]).exit_code == 0
        result = runner.invoke(
            app,
            [
                "capture",
                "add",
                "--claim",
                "Use the smaller experiment",
                "--rationale",
                "It is cheaper and reversible",
                "--confidence",
                "confirmed",
                "--evidence",
                "User: Use the smaller experiment because it is cheaper and reversible.",
                "--confirmation-event-id",
                "session-001-turn-4",
            ],
        )
        assert result.exit_code == 0

        result = runner.invoke(app, ["capture", "review", "--auto-confirm"])

        assert result.exit_code == 0
        assert "decision(s) written" in result.output
        ledger = (tmp_path / "DECISIONS.md").read_text()
        assert "Use the smaller experiment" in ledger
        assert "### 决策状态\nconfirmed" in ledger
        assert "capture_review: .flg/captures/" in ledger
        assert "未记录备选方案" not in ledger
        assert "选择了当前方案，放弃其他备选方案" not in ledger
        assert "待结合项目上下文补充" not in ledger
        assert "通过后续执行结果和项目反馈验证" not in ledger
    finally:
        os.chdir(old_cwd)


def test_short_attributed_owner_scope_uses_capture_draft_path(tmp_path):
    """A short owner contraction stays a source-attributed capture candidate."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert runner.invoke(app, ["init", "Chinese Scope Capture Test"]).exit_code == 0
        quote = "User: 我们主要做 Canvas Prompt 和 FlowGrid，其他我觉得意义不大。"
        result = runner.invoke(
            app,
            [
                "capture", "add",
                "--claim", "FlowGrid 是两条主要海外推进线之一",
                "--rationale", "Owner 明确收拢资源范围",
                "--type", "decision",
                "--confidence", "confirmed",
                "--evidence", quote,
                "--confirmation-event-id", "owner-scope-20260816-turn-1",
            ],
        )
        assert result.exit_code == 0
        capture = next((tmp_path / ".flg" / "captures").glob("cap-*.md"))
        raw = capture.read_text(encoding="utf-8")
        assert "source_actor: user" in raw
        assert "status: pending_review" in raw
        assert quote in raw
    finally:
        os.chdir(old_cwd)


def test_agent_summary_cannot_auto_confirm_even_if_it_claims_confirmed(tmp_path):
    """Agent-authored summaries cannot self-authorize formal project state."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert runner.invoke(app, ["init", "Capture Authority Test"]).exit_code == 0
        result = runner.invoke(
            app,
            [
                "capture", "add",
                "--claim", "Adopt plan A",
                "--rationale", "The agent prefers it",
                "--source", "agent_summary",
                "--confidence", "confirmed",
                "--evidence", "Assistant: Adopt plan A",
                "--confirmation-event-id", "agent-turn-1",
            ],
        )
        assert result.exit_code == 1
        assert "require user_text" in result.output
        assert "Adopt plan A" not in (tmp_path / "DECISIONS.md").read_text(encoding="utf-8")
    finally:
        os.chdir(old_cwd)


def test_import_biz_keeps_unmapped_speakers_pending(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert runner.invoke(app, ["init", "BIZ Handoff Test"]).exit_code == 0
        handoff = tmp_path / "biz-handoff.json"
        handoff.write_text(json.dumps({
            "schema_version": "1.0",
            "source": {"ref": "06-retro/meeting.md"},
            "judgments": [
                {
                    "claim": "Use the revised proposal structure",
                    "rationale": "The project owner explicitly requested it",
                    "status": "Confirmed",
                    "source_anchor": "Meeting 1, project owner, 24:10",
                    "actor": {
                        "role": "project_owner",
                        "role_basis": "explicit_source_metadata",
                    },
                },
                {
                    "claim": "Prioritize a new industry segment",
                    "rationale": "One participant proposed it",
                    "status": "Confirmed",
                    "source_anchor": "Meeting 1, speaker 2, 41:00",
                    "actor": {
                        "role": "participant",
                        "role_basis": "speaker_content_inference",
                    },
                },
            ],
        }), encoding="utf-8")

        result = runner.invoke(app, ["capture", "import-biz", "--input", str(handoff)])
        assert result.exit_code == 0
        assert "Imported 2 BIZ judgment candidate(s)." in result.output
        assert "1 eligible for background confirmation" in result.output
        assert "kept pending" in result.output

        result = runner.invoke(app, ["capture", "review", "--auto-confirm"])
        assert result.exit_code == 0
        decisions = (tmp_path / "DECISIONS.md").read_text(encoding="utf-8")
        assert "Use the revised proposal structure" in decisions
        assert "Prioritize a new industry segment" not in decisions

        captures = sorted((tmp_path / ".flg" / "captures").glob("cap-*.md"))
        pending_capture = next(path for path in captures if "Prioritize a new industry segment" in path.read_text(encoding="utf-8"))
        assert "confidence: inferred" in pending_capture.read_text(encoding="utf-8")
    finally:
        os.chdir(old_cwd)


def test_import_biz_rejects_invalid_package_without_partial_captures(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert runner.invoke(app, ["init", "BIZ Atomic Import Test"]).exit_code == 0
        handoff = tmp_path / "invalid-biz-handoff.json"
        handoff.write_text(json.dumps({
            "schema_version": "1.0",
            "source": {"ref": "06-retro/meeting.md"},
            "judgments": [
                {
                    "claim": "Valid first item",
                    "rationale": "It has an anchor",
                    "status": "Confirmed",
                    "source_anchor": "Meeting 1, owner, 10:00",
                },
                {
                    "claim": "Invalid second item",
                    "rationale": "It lacks an anchor",
                    "status": "Confirmed",
                },
            ],
        }), encoding="utf-8")

        result = runner.invoke(app, ["capture", "import-biz", "--input", str(handoff)])
        assert result.exit_code == 1
        captures_dir = tmp_path / ".flg" / "captures"
        assert not list(captures_dir.glob("cap-*.md"))
    finally:
        os.chdir(old_cwd)
