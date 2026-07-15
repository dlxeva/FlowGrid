"""Tests for doctor and evidence index rebuilding."""

import json
import os

from typer.testing import CliRunner

from flg.cli import app

runner = CliRunner()


def _project(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    runner.invoke(app, ["init", "Integrity Test"])
    return old_cwd


def test_reindex_rebuilds_index_from_formal_ledger(tmp_path):
    old_cwd = _project(tmp_path)
    try:
        result = runner.invoke(
            app,
            [
                "decision",
                "add",
                "--decision",
                "Use the local ledger as source of truth",
                "--rationale",
                "It is inspectable and durable",
            ],
        )
        assert result.exit_code == 0
        index_path = tmp_path / ".flg" / "context" / "evidence_index.json"
        index_path.write_text(json.dumps({"version": 1, "items": {"D-999": {}}}), encoding="utf-8")

        result = runner.invoke(app, ["reindex"])
        assert result.exit_code == 0
        data = json.loads(index_path.read_text(encoding="utf-8"))
        assert "D-999" not in data["items"]
        assert any("local ledger as source of truth" in item["title"] for item in data["items"].values())
        assert data["rebuilt_from"] == "DECISIONS.md"
    finally:
        os.chdir(old_cwd)


def test_doctor_reports_index_drift_without_writing(tmp_path):
    old_cwd = _project(tmp_path)
    try:
        runner.invoke(
            app,
            [
                "decision",
                "add",
                "--decision",
                "Keep evidence local",
                "--rationale",
                "Local files are auditable",
            ],
        )
        index_path = tmp_path / ".flg" / "context" / "evidence_index.json"
        index_path.write_text(json.dumps({"version": 1, "items": {"D-999": {}}}), encoding="utf-8")
        before = index_path.read_text(encoding="utf-8")

        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "Needs attention" in result.output
        assert "orphan_index:" in result.output
        assert index_path.read_text(encoding="utf-8") == before
    finally:
        os.chdir(old_cwd)


def test_reindex_accepts_fullwidth_chinese_decision_separator(tmp_path):
    """Legacy Chinese ledgers using ｜ remain rebuildable."""
    old_cwd = _project(tmp_path)
    try:
        decisions = tmp_path / "DECISIONS.md"
        decisions.write_text(
            """# 决策日志

## D-001｜采用本地文件作为事实源

### 最终决策
采用本地文件作为事实源。

### 决策理由
文件可读、可审计、可迁移。

### 备选方案
A. 云端记忆

### 放弃理由
云端记忆不可见。

### 复盘入口
如果本地维护成本过高，重新评估。
""",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["reindex"])
        assert result.exit_code == 0
        data = json.loads((tmp_path / ".flg" / "context" / "evidence_index.json").read_text())
        assert "D-001" in data["items"]
        assert data["items"]["D-001"]["title"] == "采用本地文件作为事实源"
    finally:
        os.chdir(old_cwd)


def test_doctor_reports_legacy_decision_entries_instead_of_false_ok(tmp_path):
    """Legacy short-form decisions must be visible as migration work."""
    old_cwd = _project(tmp_path)
    try:
        (tmp_path / "DECISIONS.md").write_text(
            """# 决策日志

## D-001｜项目范围收窄

- **日期**：2026-06-28
- **决策**：一期只做核心试点。
- **依据**：先验证最小闭环。
- **可推翻条件**：客户明确扩大范围。
""",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "Needs attention" in result.output
        assert "Unparsed decision entries" in result.output
        assert "unparsed_decisions:" in result.output
        assert "D-001" in result.output
    finally:
        os.chdir(old_cwd)


def test_doctor_ignores_closed_patch_retained_for_audit(tmp_path):
    """Rejected patches retained in state history must not be reported as pending."""
    old_cwd = _project(tmp_path)
    try:
        patch_path = tmp_path / ".flg" / "patches" / "rejected.patch.md"
        patch_path.write_text(
            "patch_id: rejected\nstatus: rejected\n",
            encoding="utf-8",
        )
        state_path = tmp_path / ".flg" / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["pending_patches"].append(
            {
                "patch_id": "rejected",
                "path": str(patch_path),
                "status": "rejected",
            }
        )
        state_path.write_text(json.dumps(state), encoding="utf-8")

        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "closed_patches_in_pending_state" not in result.output
        assert "merged_pending:" not in result.output
    finally:
        os.chdir(old_cwd)


def test_doctor_reports_pending_state_when_patch_file_is_closed(tmp_path):
    """A pending state entry whose patch file is closed is a real inconsistency."""
    old_cwd = _project(tmp_path)
    try:
        patch_path = tmp_path / ".flg" / "patches" / "drifted.patch.md"
        patch_path.write_text(
            "patch_id: drifted\nstatus: merged\n",
            encoding="utf-8",
        )
        state_path = tmp_path / ".flg" / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["pending_patches"].append(
            {
                "patch_id": "drifted",
                "path": str(patch_path),
                "status": "pending_review",
            }
        )
        state_path.write_text(json.dumps(state), encoding="utf-8")

        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "Closed patches still pending" in result.output
        assert "merged_pending:" in result.output
        assert "drifted" in result.output
    finally:
        os.chdir(old_cwd)
