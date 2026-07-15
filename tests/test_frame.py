"""Tests for flg frame command."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from flg.cli import app

runner = CliRunner()


@pytest.fixture
def flg_project(tmp_path):
    """Create a temporary FLG project for testing."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    # Initialize project
    result = runner.invoke(app, ["init", "Test Project"])
    assert result.exit_code == 0
    
    yield tmp_path
    os.chdir(old_cwd)


def test_frame_detects_missing_fields(flg_project):
    """Test that flg frame detects missing fields in FRAMING.md."""
    result = runner.invoke(app, ["frame"])
    assert result.exit_code == 0
    # Should detect missing fields and generate patch
    assert "missing" in result.output.lower() or "patch" in result.output.lower()


def test_frame_generates_patch(flg_project):
    """Test that flg frame generates a patch file."""
    result = runner.invoke(app, ["frame"])
    assert result.exit_code == 0
    
    patches_dir = flg_project / ".flg" / "patches"
    patch_files = list(patches_dir.glob("frame-*.patch.md"))
    assert len(patch_files) > 0, f"No frame patch found in {list(patches_dir.iterdir())}"
    
    # Verify patch content
    patch_content = patch_files[0].read_text()
    assert "FLG Patch" in patch_content
    assert "flg frame" in patch_content
    assert "pending_review" in patch_content


def test_frame_on_non_flg_project(tmp_path):
    """Test that flg frame fails on non-FLG project."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    result = runner.invoke(app, ["frame"])
    assert result.exit_code == 1
    assert "Not a FLG project" in result.output
    
    os.chdir(old_cwd)


def test_frame_with_complete_framing(flg_project):
    """Test flg frame when FRAMING.md is complete."""
    # Fill in FRAMING.md with real content
    framing_path = flg_project / "FRAMING.md"
    content = framing_path.read_text()

    # Replace placeholders with real content
    content = content.replace("(to be defined)", "Real content here")
    content = content.replace("(to be filled)", "Real content here")
    content = content.replace("(to be hypothesized)", "Real hypothesis")
    content = content.replace("(to be identified)", "- Question 1")
    content = content.replace("(none yet)", "- Risk 1")

    framing_path.write_text(content)

    result = runner.invoke(app, ["frame"])
    assert result.exit_code == 0
    # Should either say complete or generate a lighter patch


def test_frame_accepts_h2_for_requirements_subfields(flg_project):
    """Explicit Requirements / Real Needs Hypothesis written as H2 (##) must be detected as filled.

    Regression for 发现 1: these two fields ship as H3 (###) in the default
    template, but users naturally write them as H2. frame used to false-positive
    '0/10 fields filled' on a complete Chinese FRAMING.md that used H2.
    """
    framing_path = flg_project / "FRAMING.md"
    # Rewrite FRAMING.md using H2 for ALL fields (the user-natural style).
    content = """# Problem Definition

## Problem Statement

Real problem description here.

## Explicit Requirements

Client asked for X, Y, Z.

## Real Needs Hypothesis

The real need is likely faster onboarding.

## Goals

- Goal one

## Non-Goals

- Out of scope: feature Q

## User Objects

End user is the ops team.

## Review Objects

CTO reviews the final deliverable.

## Success Criteria

Metric: 50% reduction in onboarding time.

## Constraints

Budget is 50k, timeline is 8 weeks.

## Open Questions

- Which stack to use?
"""
    framing_path.write_text(content, encoding="utf-8")

    result = runner.invoke(app, ["frame"])
    assert result.exit_code == 0
    # With all fields filled (using H2), frame should report complete —
    # NOT report Explicit Requirements / Real Needs Hypothesis as missing.
    assert "complete" in result.output.lower() or "0 missing" in result.output.lower()


def test_frame_warns_when_evidence_basis_is_secondary(flg_project):
    """Complete framing should still warn when its evidence is only secondary."""
    framing_path = flg_project / "FRAMING.md"
    content = framing_path.read_text(encoding="utf-8")
    content = content.replace("(to be defined)", "Real content here")
    content = content.replace("(to be filled)", "Real content here")
    content = content.replace("(to be hypothesized)", "Real hypothesis")
    content = content.replace("(to be identified)", "- Question 1")
    content = content.replace("(none yet)", "- Risk 1")
    content = content.replace("(direct / verified / secondary / speculative)", "secondary")
    framing_path.write_text(content, encoding="utf-8")

    result = runner.invoke(app, ["frame"])

    assert result.exit_code == 0
    assert "secondary evidence" in result.output.lower()


def test_frame_accepts_direct_evidence_basis(flg_project):
    """Direct evidence should be reported without a low-confidence warning."""
    framing_path = flg_project / "FRAMING.md"
    content = framing_path.read_text(encoding="utf-8")
    content = content.replace("(to be defined)", "Real content here")
    content = content.replace("(to be filled)", "Real content here")
    content = content.replace("(to be hypothesized)", "Real hypothesis")
    content = content.replace("(to be identified)", "- Question 1")
    content = content.replace("(none yet)", "- Risk 1")
    content = content.replace("(direct / verified / secondary / speculative)", "direct")
    framing_path.write_text(content, encoding="utf-8")

    result = runner.invoke(app, ["frame"])

    assert result.exit_code == 0
    assert "evidence basis: direct" in result.output.lower()
