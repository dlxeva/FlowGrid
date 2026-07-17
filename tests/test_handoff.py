"""Tests for flg handoff command."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from flg.cli import app

runner = CliRunner()


@pytest.fixture
def flg_project_with_patch(tmp_path):
    """Create a FLG project with a closeout patch."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    # Initialize project
    result = runner.invoke(app, ["init", "Handoff Test"])
    assert result.exit_code == 0
    
    # Create transcript
    transcript = tmp_path / "session.md"
    transcript.write_text("""# Session

We decided to focus on content marketing.
There's a risk that KOLs are too expensive.
Next step is to confirm budget.
""")
    
    # Generate closeout patch
    result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
    assert result.exit_code == 0
    
    yield tmp_path
    os.chdir(old_cwd)


def test_handoff_shows_project_info(flg_project_with_patch):
    """Test that handoff shows project information."""
    result = runner.invoke(app, ["handoff"])
    assert result.exit_code == 0
    assert "Handoff Test" in result.output
    assert "initialized" in result.output


def test_handoff_shows_pending_patches(flg_project_with_patch):
    """Test that handoff shows pending patches."""
    result = runner.invoke(app, ["handoff"])
    assert result.exit_code == 0
    assert "pending patch" in result.output.lower()


def test_handoff_excludes_rejected_patches(tmp_path):
    """Rejected patches remain auditable but are not active handoff state."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert runner.invoke(app, ["init", "Rejected Handoff Test"]).exit_code == 0
        transcript = tmp_path / "session.md"
        transcript.write_text("我们确认采用方案A。\n因为方案A更快。\n", encoding="utf-8")
        assert runner.invoke(app, ["closeout", "--transcript", str(transcript)]).exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        assert runner.invoke(app, ["patch", "discard", patch.name, "--reason", "test"]).exit_code == 0

        result = runner.invoke(app, ["handoff"])
        assert result.exit_code == 0
        assert "(no pending patches)" in result.output
        assert patch.name not in result.output
    finally:
        os.chdir(old_cwd)


def test_handoff_shows_pending_capture_without_patch(tmp_path):
    """A real-time inferred capture must survive agent handoff."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert runner.invoke(app, ["init", "Capture Handoff Test"]).exit_code == 0
        result = runner.invoke(
            app,
            [
                "capture",
                "add",
                "--claim",
                "Do not merge the conflicting branch.",
                "--rationale",
                "The replacement branch is clean and preserves current master work.",
                "--type",
                "decision",
                "--confidence",
                "inferred",
                "--source",
                "agent_summary",
                "--evidence",
                "PR state: conflicting versus clean replacement.",
            ],
        )
        assert result.exit_code == 0

        result = runner.invoke(app, ["handoff"])
        assert result.exit_code == 0
        assert "Do not merge the conflicting branch." in result.output
        assert "capture cap-" in result.output
        assert "PR state: conflicting versus clean replacement." in result.output
    finally:
        os.chdir(old_cwd)


def test_handoff_marks_missing_anchor_not_authoritative(tmp_path):
    """Handoff must flag missing anchor paths instead of treating them as current truth."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert runner.invoke(app, ["init", "Missing Anchor Test"]).exit_code == 0
        (tmp_path / "ANCHORS.md").write_text(
            """# Authoritative Anchors\n\n### Product\n\n- **File:** missing/README.md\n- **Role:** product truth\n- **Authority:** authoritative\n- **Provenance:** internal\n- **Lifecycle:** active\n""",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["handoff"])
        assert result.exit_code == 0
        assert "Status: missing" in result.output
        assert "Do not use it as current authority" in result.output
    finally:
        os.chdir(old_cwd)


def test_handoff_shows_risks(flg_project_with_patch):
    """Test that handoff shows risks from patches."""
    result = runner.invoke(app, ["handoff"])
    assert result.exit_code == 0
    assert "KOLs" in result.output or "risk" in result.output.lower()


def test_handoff_shows_candidate_decision_details(flg_project_with_patch):
    """Handoff should expose candidate decision detail fields."""
    result = runner.invoke(app, ["handoff"])
    assert result.exit_code == 0
    assert "Why" in result.output
    assert "Source excerpt" in result.output or "source_excerpt" in result.output.lower()


def test_handoff_shows_patch_metadata_and_next_actions(tmp_path):
    """Handoff should show patch metadata and specific next actions."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["init", "Metadata Test"])
        assert result.exit_code == 0

        transcript = tmp_path / "session.md"
        transcript.write_text("""# Session

We've decided to focus on content marketing.
Next step is to confirm budget allocation with finance.
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0

        result = runner.invoke(app, ["handoff"])
        assert result.exit_code == 0
        assert "source: flg closeout" in result.output
        assert "medium" in result.output
        assert "generated:" in result.output
        assert "confirm budget allocation with finance" in result.output.lower()
    finally:
        os.chdir(old_cwd)


def test_handoff_on_non_flg_project(tmp_path):
    """Test that handoff fails on non-FLG project."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    result = runner.invoke(app, ["handoff"])
    assert result.exit_code == 1
    assert "Not a FLG project" in result.output
    
    os.chdir(old_cwd)


# --- Goal 3 v0.1.7: FRAMING-aware handoff ---

def test_handoff_extracts_goal_from_framing(tmp_path):
    """v0.1.7: When SNAPSHOT.md has no Current Core Goal, fall back to FRAMING.md Goals field."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["init", "Goal Test"])
        assert result.exit_code == 0

        # Write FRAMING.md with all 10 fields filled including a clear Goals section
        framing_path = tmp_path / "FRAMING.md"
        framing_path.write_text("""# Problem Definition

## Problem Statement

Real problem statement here.

## Requirements

### Explicit Requirements

Explicit requirements.

### Real Needs Hypothesis

Real needs hypothesis.

## Goals

- Ship v1 with Timeline-aware Context Compiler
- Validate Prompt Package quality
- Lock Spec v2.1

## Non-Goals

- No full SaaS

## User Objects

Creative workers.

## Review Objects

Blind eval judges.

## Success Criteria

Score 80+ vs Baseline.

## Constraints

Solo project.

## Open Questions

- How to align voice with canvas events?
- What is the optimal compression rate?

---
""", encoding="utf-8")

        result = runner.invoke(app, ["handoff"])
        assert result.exit_code == 0
        # Should pull from FRAMING.md Goals, not "(not defined)"
        assert "Ship v1 with Timeline-aware" in result.output
    finally:
        os.chdir(old_cwd)


def test_handoff_shows_framing_open_questions(tmp_path):
    """v0.1.7: Handoff should expose FRAMING.md Open Questions even when no patches exist."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["init", "Question Test"])
        assert result.exit_code == 0

        framing_path = tmp_path / "FRAMING.md"
        framing_path.write_text("""# Problem Definition

## Problem Statement

Real problem.

## Requirements

### Explicit Requirements

Reqs.

### Real Needs Hypothesis

Needs.

## Goals

- Goal 1

## Non-Goals

- None

## User Objects

Users.

## Review Objects

Reviewers.

## Success Criteria

Criteria.

## Constraints

Constraints.

## Open Questions

- How to validate alignment quality?
- What is the failure mode budget?

---
""", encoding="utf-8")

        result = runner.invoke(app, ["handoff"])
        assert result.exit_code == 0
        assert "How to validate alignment quality?" in result.output
        assert "What is the failure mode budget?" in result.output
    finally:
        os.chdir(old_cwd)


def test_handoff_next_actions_reflect_framing_complete(tmp_path):
    """v0.1.7: When FRAMING.md is fully filled, Next Actions should NOT say 'fill in FRAMING.md'."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["init", "Complete Framing Test"])
        assert result.exit_code == 0

        # Fill all 10 fields with non-placeholder content
        framing_path = tmp_path / "FRAMING.md"
        framing_path.write_text("""# Problem Definition

## Problem Statement

Real problem statement.

## Requirements

### Explicit Requirements

Real explicit requirements.

### Real Needs Hypothesis

Real needs.

## Goals

- Top goal 1
- Top goal 2

## Non-Goals

- Out of scope item.

## User Objects

- End users: marketers.

## Review Objects

- Reviewers: panel.

## Success Criteria

- Specific metric.

## Constraints

- Budget: solo.

## Open Questions

- Open question 1.

---
""", encoding="utf-8")

        result = runner.invoke(app, ["handoff"])
        assert result.exit_code == 0
        # Old behavior would say "Review and fill in FRAMING.md"
        # New behavior should acknowledge FRAMING is complete
        assert "Review and fill in FRAMING.md" not in result.output
        # Should suggest session work
        assert "FRAMING.md is complete" in result.output or "closeout" in result.output.lower()
    finally:
        os.chdir(old_cwd)


# --- Phase 2: Decision context in handoff ---

def test_handoff_shows_decision_context(flg_project_with_patch):
    """Handoff should expose Why/Rejected/Reversal fields from closeout patches."""
    result = runner.invoke(app, ["handoff"])
    assert result.exit_code == 0
    # The new Phase 1 closeout output includes bold-label fields
    # At minimum, "Why" should appear (either from bold-label or from why_this_is_a_decision)
    assert "Why" in result.output


def test_handoff_backward_compatible(tmp_path):
    """Old-format patches (without bold-label fields) should still be parsed correctly."""
    from flg.commands.handoff import parse_patch_for_handoff

    old_format_patch = """# FLG Patch

patch_id: closeout-20260101-001
project: Old Format Project
generated_at: 2026-01-01T00:00:00
source_command: flg closeout
risk_level: medium
status: pending_review

---

## 1. Session Summary

- Summary line

## 2. Candidate Decisions

### Candidate Decision 1: Focus on content marketing

status: pending_review
confidence: high
decision_type: explicit_confirmation
why_this_is_a_decision: Explicit confirmation detected: 'confirmed'
source_excerpt: > We decided to focus on content marketing.
suggested_action: needs_review

## 3. Suggested Next Actions

- Confirm budget
"""
    info = parse_patch_for_handoff(old_format_patch)
    assert len(info["decisions"]) == 1
    d = info["decisions"][0]
    assert d["status"] == "pending_review"
    assert d["confidence"] == "high"
    assert d["type"] == "explicit_confirmation"
    # Old-style why_this_is_a_decision still populates why
    assert "Explicit confirmation" in d["why"]
    assert d["excerpt"] == "We decided to focus on content marketing."
    assert d["action"] == "needs_review"
    # New fields should be empty strings (not missing)
    assert d["what_decided"] == ""
    assert d["alternatives"] == ""
    assert d["rejected"] == ""
    assert d["reversal"] == ""


def test_handoff_parses_new_bold_label_fields(tmp_path):
    """New-format patches with bold-label fields should be fully parsed."""
    from flg.commands.handoff import parse_patch_for_handoff

    new_format_patch = """# FLG Patch

patch_id: closeout-20260628-001
project: New Format Project
generated_at: 2026-06-28T10:00:00
source_command: flg closeout
risk_level: medium
status: pending_review

---

## 2. Candidate Decisions

### Candidate Decision 1: Use content marketing

status: pending_review
confidence: high
decision_type: explicit_confirmation
why_this_is_a_decision: Explicit confirmation detected: 'decided'
**What was decided:** Focus on content marketing for Q3
**Why:** KOL budget is too high, content has better ROI
**Alternatives mentioned:** KOL partnerships; paid ads
**Rejected because:** Budget constraints and uncertain ROI
**Could reverse if:** KOL costs drop below 5000 per campaign
source_excerpt: > We decided to focus on content marketing.
suggested_action: needs_review

## 3. Suggested Next Actions

- Confirm budget
"""
    info = parse_patch_for_handoff(new_format_patch)
    assert len(info["decisions"]) == 1
    d = info["decisions"][0]
    assert d["what_decided"] == "Focus on content marketing for Q3"
    # **Why:** overrides why_this_is_a_decision
    assert d["why"] == "KOL budget is too high, content has better ROI"
    assert d["alternatives"] == "KOL partnerships; paid ads"
    assert d["rejected"] == "Budget constraints and uncertain ROI"
    assert d["reversal"] == "KOL costs drop below 5000 per campaign"
    assert d["excerpt"] == "We decided to focus on content marketing."


def test_handoff_shows_anchors_section(flg_project_with_patch):
    """Test that handoff shows the Authoritative Anchors section."""
    result = runner.invoke(app, ["handoff"])
    assert result.exit_code == 0
    assert "Authoritative Anchors" in result.output


def test_handoff_shows_anchors_when_defined(tmp_path):
    """Test that handoff displays anchor entries when ANCHORS.md has content."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        # Initialize project
        runner.invoke(app, ["init", "Anchor Test"])
        
        # Write a real anchor entry
        anchors_path = tmp_path / "ANCHORS.md"
        anchors_path.write_text("""# Authoritative Anchors

> 定义当前项目的权威锚点文件。

## Anchors

### 实施边界

- **File:** docs/technical_baseline.html
- **Role:** 技术基线
- **Authority:** authoritative
- **Provenance:** internal
- **Lifecycle:** active
- **Updated:** 2026-07-03
- **Notes:** 一期真实交付边界的技术基线

### 预算口径

- **File:** docs/budget_v2.docx
- **Role:** 预算口径
- **Authority:** working
- **Provenance:** internal
- **Lifecycle:** active
- **Updated:** 2026-07-03
- **Notes:** 100万口径下的预算测算
""")
        
        # Run handoff
        result = runner.invoke(app, ["handoff"])
        assert result.exit_code == 0
        assert "实施边界" in result.output
        assert "技术基线" in result.output
        assert "docs/technical_baseline.html" in result.output
        assert "预算口径" in result.output
        assert "Provenance" in result.output
        assert "Lifecycle" in result.output
    finally:
        os.chdir(old_cwd)


def test_handoff_anchors_empty_when_no_entries(tmp_path):
    """Test that handoff shows placeholder when ANCHORS.md has no entries."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        # Initialize project
        runner.invoke(app, ["init", "Empty Anchor Test"])
        
        # Run handoff
        result = runner.invoke(app, ["handoff"])
        assert result.exit_code == 0
        assert "no anchors defined" in result.output
    finally:
        os.chdir(old_cwd)


def test_export_handoff_creates_pack(tmp_path):
    """export-handoff should write a resumable handoff pack including new state files."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["init", "Export Test", "--template", "solution"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["export-handoff"])
        assert result.exit_code == 0
        assert "Handoff pack exported" in result.output

        export_dir = tmp_path / ".flg" / "exports"
        pack_files = list(export_dir.glob("handoff-pack-*.md"))
        assert pack_files
        content = pack_files[0].read_text(encoding="utf-8")
        assert "FlowGrid Handoff Pack" in content
        assert "Goal Evolution" in content
        assert "Constraints" in content
        assert "Authoritative Anchors" in content
    finally:
        os.chdir(old_cwd)
