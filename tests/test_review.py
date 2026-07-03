"""Tests for flg review command."""

import os

from typer.testing import CliRunner

from flg.cli import app

runner = CliRunner()


def test_review_accept_all_writes_decisions(tmp_path):
    """review should append accepted candidate decisions to DECISIONS.md."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["init", "Review Test"])
        assert result.exit_code == 0

        transcript = tmp_path / "session.md"
        transcript.write_text("""# Session

We decided to focus on content marketing.
Because paid ads are too expensive for this phase.
Next step is to confirm budget allocation.
""", encoding="utf-8")

        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0

        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        result = runner.invoke(app, ["review", "--patch", patch.name, "--accept-all"])
        assert result.exit_code == 0
        assert "Accepted" in result.output

        decisions_content = (tmp_path / "DECISIONS.md").read_text(encoding="utf-8")
        assert "content marketing" in decisions_content
        assert "paid ads are too expensive" in decisions_content
    finally:
        os.chdir(old_cwd)


def test_review_marks_patch_state(tmp_path):
    """review should record decision review status in state.json."""
    import json

    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Review State Test"])
        transcript = tmp_path / "session.md"
        transcript.write_text("""# Session

We decided to focus on lifecycle email.
""", encoding="utf-8")
        runner.invoke(app, ["closeout", "--transcript", str(transcript)])

        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        result = runner.invoke(app, ["review", "--patch", patch.name, "--accept-all"])
        assert result.exit_code == 0

        state = json.loads((tmp_path / ".flg" / "state.json").read_text(encoding="utf-8"))
        reviewed = [p for p in state["pending_patches"] if p["patch_id"] in patch.name]
        assert reviewed
        assert reviewed[0]["decision_review_status"] == "accepted"
        assert "decision_reviewed_at" in reviewed[0]
    finally:
        os.chdir(old_cwd)
