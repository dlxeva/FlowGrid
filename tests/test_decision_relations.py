"""Tests for explicit, file-backed decision relations."""

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
            ],
        )
        assert second.exit_code == 0

        ledger = (tmp_path / "DECISIONS.md").read_text(encoding="utf-8")
        graph = parse_decision_relations(ledger)
        assert graph["D-002"]["supersedes"] == ["D-001"]
        assert graph["D-002"]["supports"] == ["D-001"]
        assert incoming_relations(graph, "D-001") == [
            ("supersedes", "D-002"),
            ("supports", "D-002"),
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


def test_doctor_reports_unknown_and_self_relations(tmp_path):
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
- **支持决策:** none
- **冲突决策:** D-001
- **依赖决策:** D-999

"""
        ledger = ledger.replace(
            "### 决策理由\n",
            relation_block + "### 决策理由\n",
            1,
        )
        decisions_path.write_text(ledger, encoding="utf-8")

        result = runner.invoke(app, ["doctor", "--strict"])
        assert result.exit_code == 1
        assert "decision_relations:" in result.output
        assert "unknown_target" in result.output
        assert "self_relation" in result.output
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
- **Contradicts:** none
- **Depends On:** none

## D-002 | Second judgment

### 最终决策
增加显式决策关系。

### 决策关系
- **替代决策:** D-001
- **支持决策:** D-001
- **冲突决策:** none
- **依赖决策:** D-001
"""
    graph = parse_decision_relations(content)
    assert graph["D-002"] == {
        "supersedes": ["D-001"],
        "supports": ["D-001"],
        "contradicts": [],
        "depends_on": ["D-001"],
    }
