"""Tests for explicit, file-backed decision relations."""

import json
import os

from typer.testing import CliRunner

from flg.cli import app
from flg.core.relations import (
    incoming_relations,
    parse_decision_relations,
)

runner = CliRunner()


def _project(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    result = runner.invoke(app, ["init", "Decision Relations Test"])
    assert result.exit_code == 0
    return old_cwd


def test_decision_add_records_relations_and_trace_reads_both_directions(tmp_path):
    old_cwd = _project(tmp_path)
    try:
        first = runner.invoke(
            app,
            [
                "decision",
                "add",
                "--decision",
                "Use a local ledger",
                "--rationale",
                "The project state must remain inspectable",
            ],
        )
        assert first.exit_code == 0

        second = runner.invoke(
            app,
            [
                "decision",
                "add",
                "--decision",
                "Add a derived relation view",
                "--rationale",
                "Agents need explicit links between judgments",
                "--supersedes",
                "d-1",
                "--supports",
                "D-001",
                "--conflicts-with",
                "D-001",
            ],
        )
        assert second.exit_code == 0

        ledger = (tmp_path / "DECISIONS.md").read_text(encoding="utf-8")
        graph = parse_decision_relations(ledger)
        assert graph["D-002"]["supersedes"] == ["D-001"]
        assert graph["D-002"]["supports"] == ["D-001"]
        assert graph["D-002"]["conflicts_with"] == ["D-001"]
        assert incoming_relations(graph, "D-001") == [
            ("supersedes", "D-002"),
            ("supports", "D-002"),
            ("conflicts_with", "D-002"),
        ]

        outgoing = runner.invoke(app, ["trace", "D-002"])
        assert outgoing.exit_code == 0
        assert "Decision Relations" in outgoing.output
        assert "outgoing" in outgoing.output
        assert "supersedes" in outgoing.output
        assert "D-001" in outgoing.output

        incoming = runner.invoke(app, ["trace", "D-001"])
        assert incoming.exit_code == 0
        assert "incoming" in incoming.output
        assert "D-002" in incoming.output
    finally:
        os.chdir(old_cwd)


def test_decision_add_rejects_unknown_relation_targets(tmp_path):
    old_cwd = _project(tmp_path)
    try:
        result = runner.invoke(
            app,
            [
                "decision",
                "add",
                "--decision",
                "Depend on an unknown judgment",
                "--rationale",
                "This should fail before writing",
                "--depends-on",
                "D-999",
            ],
        )
        assert result.exit_code == 1
        assert "Unknown decision relation target" in result.output
        assert "D-001 | Depend on an unknown judgment" not in (
            tmp_path / "DECISIONS.md"
        ).read_text(encoding="utf-8")
    finally:
        os.chdir(old_cwd)


def test_decision_add_without_source_does_not_invent_high_authority_evidence(tmp_path):
    old_cwd = _project(tmp_path)
    try:
        result = runner.invoke(
            app,
            [
                "decision",
                "add",
                "--decision",
                "Keep the project state local",
                "--rationale",
                "The ledger must remain inspectable",
            ],
        )
        assert result.exit_code == 0

        ledger = (tmp_path / "DECISIONS.md").read_text(encoding="utf-8")
        recorded = ledger.split("## D-001 | Keep the project state local", 1)[1]
        assert "直接写入命令；未提供来源摘录" in ledger
        assert recorded.count("未提供") == 1
        assert "### 备选方案" not in recorded
        assert "### 放弃理由" not in recorded
        assert "### 风险判断" not in recorded
        assert "### 后续验证" not in recorded
        assert "### 复盘入口" not in recorded
        assert "用户明确指令" not in ledger
        assert "通过后续执行结果和项目反馈验证" not in ledger

        index_path = tmp_path / ".flg" / "context" / "evidence_index.json"
        item = json.loads(index_path.read_text(encoding="utf-8"))["items"]["D-001"]
        assert item["authority"] == "medium"
        assert item["source_type"] == "direct_command"

        index_path.unlink()
        rebuilt = runner.invoke(app, ["reindex"])
        assert rebuilt.exit_code == 0
        rebuilt_item = json.loads(index_path.read_text(encoding="utf-8"))["items"]["D-001"]
        assert rebuilt_item["authority"] == "medium"
        assert rebuilt_item["source_type"] == "direct_command"
    finally:
        os.chdir(old_cwd)


def test_decision_add_with_source_keeps_explicit_confirmation_authority(tmp_path):
    old_cwd = _project(tmp_path)
    try:
        result = runner.invoke(
            app,
            [
                "decision",
                "add",
                "--decision",
                "Use the bounded pilot",
                "--rationale",
                "The owner selected it",
                "--evidence",
                "User: 定了，先做有边界的试点。",
            ],
        )
        assert result.exit_code == 0

        index_path = tmp_path / ".flg" / "context" / "evidence_index.json"
        item = json.loads(index_path.read_text(encoding="utf-8"))["items"]["D-001"]
        assert item["authority"] == "high"
        assert item["source_type"] == "user_confirmation"
        assert item["source_excerpt"] == "User: 定了，先做有边界的试点。"
    finally:
        os.chdir(old_cwd)


def test_doctor_and_trace_report_malformed_and_mixed_relations(tmp_path):
    old_cwd = _project(tmp_path)
    try:
        created = runner.invoke(
            app,
            [
                "decision",
                "add",
                "--decision",
                "Keep the formal ledger authoritative",
                "--rationale",
                "Derived views must remain rebuildable",
            ],
        )
        assert created.exit_code == 0

        decisions_path = tmp_path / "DECISIONS.md"
        ledger = decisions_path.read_text(encoding="utf-8")
        relation_block = """### 决策关系
- **替代决策:** none
- **支持决策:** D-001, D-99O
- **冲突决策:** D-001
- **依赖决策:** D-999

"""
        before_rationale, after_rationale = ledger.rsplit(
            "### 决策理由\n",
            1,
        )
        ledger = (
            before_rationale
            + relation_block
            + "### 决策理由\n"
            + after_rationale
        )
        decisions_path.write_text(ledger, encoding="utf-8")

        result = runner.invoke(app, ["doctor", "--strict"])
        assert result.exit_code == 1
        assert "decision_relations:" in result.output
        assert "unknown_target" in result.output
        assert "self_relation" in result.output
        assert "malformed_value" in result.output
        assert "D-99O" in result.output

        graph = parse_decision_relations(ledger)
        assert graph["D-001"]["supports"] == ["D-001"]

        trace = runner.invoke(app, ["trace", "D-001"])
        assert trace.exit_code == 0
        assert "malformed" in trace.output
        assert "D-001, D-99O" in trace.output
    finally:
        os.chdir(old_cwd)


def test_parser_accepts_english_and_chinese_relation_labels():
    content = """# Decision Log

## D-001 | First judgment

### Final Decision
Keep the ledger local.

### Decision Relations
- **Supersedes:** none
- **Supports:** none
- **Conflicts With:** none
- **Depends On:** none

## D-002 | Second judgment

### 最终决策
增加显式决策关系。

### 决策关系
- **替代决策:** D-001
- **支持决策:** D-001
- **冲突决策:** D-001
- **依赖决策:** D-001
"""
    graph = parse_decision_relations(content)
    assert graph["D-002"] == {
        "supersedes": ["D-001"],
        "supports": ["D-001"],
        "conflicts_with": ["D-001"],
        "depends_on": ["D-001"],
    }


def test_parser_accepts_only_explicit_legacy_conflict_labels():
    content = """# Decision Log

## D-001 | First judgment

## D-002 | English legacy label
- **Contradicts:** D-001

## D-003 | Chinese legacy label
- **矛盾决策:** D-001

## D-004 | Unrecognized wording
- **Conflicts:** D-001
"""
    graph = parse_decision_relations(content)
    assert graph["D-002"]["conflicts_with"] == ["D-001"]
    assert graph["D-003"]["conflicts_with"] == ["D-001"]
    assert graph["D-004"]["conflicts_with"] == []
