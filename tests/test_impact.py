"""Tests for read-only decision impact analysis."""

import os

from typer.testing import CliRunner

from flg.cli import app
from flg.core.impact import analyze_impact
from flg.core.relations import parse_decision_relations

runner = CliRunner()


def test_impact_follows_supersession_and_dependents_but_not_unrelated():
    content = """# Decision Log

## D-037 | Keep Core bounded

## D-039 | Keep project continuity positioning

## D-044 | Keep Core and experiments separate

## D-047 | Start an independent memory branch

### Decision Relations
- **Supersedes:** D-037
- **Supports:** none
- **Conflicts With:** none
- **Depends On:** none

## D-048 | Select the branch base

### Decision Relations
- **Supersedes:** none
- **Supports:** D-044
- **Conflicts With:** none
- **Depends On:** D-047
"""
    graph = parse_decision_relations(content)
    impact = analyze_impact(graph, "D-047")
    affected = {item.decision_id for item in impact}

    assert affected == {"D-037", "D-048"}
    assert "D-039" not in affected
    assert "D-044" not in affected


def test_cli_impact_is_read_only_and_surfaces_owner_gate(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        created = runner.invoke(app, ["init", "Impact Test"])
        assert created.exit_code == 0

        decisions = tmp_path / "DECISIONS.md"
        decisions.write_text(
            """# Decision Log

## D-001 | Keep the old route

## D-002 | Adopt the new route

### Decision Relations
- **Supersedes:** D-001
- **Supports:** none
- **Conflicts With:** none
- **Depends On:** none

## D-003 | Select the implementation

### Decision Relations
- **Supersedes:** none
- **Supports:** none
- **Conflicts With:** none
- **Depends On:** D-002
""",
            encoding="utf-8",
        )
        before = decisions.read_text(encoding="utf-8")

        result = runner.invoke(app, ["impact", "D-002"])

        assert result.exit_code == 0
        assert "D-001" in result.output
        assert "D-003" in result.output
        assert "revalidation_required" in result.output
        assert "Owner gate" in result.output
        assert decisions.read_text(encoding="utf-8") == before
    finally:
        os.chdir(old_cwd)
