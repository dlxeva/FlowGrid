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


def test_review_report_only_does_not_write_ledger(tmp_path):
    """Autonomous hosts can inspect candidates without bypassing approval."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Review Report Test"])
        transcript = tmp_path / "session.md"
        transcript.write_text(
            """# Session

We decided to use the smaller experiment because it is reversible and cheaper.
""",
            encoding="utf-8",
        )
        runner.invoke(app, ["closeout", "--transcript", str(transcript), "--no-llm"])
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))

        decisions_before = (tmp_path / "DECISIONS.md").read_text(encoding="utf-8")
        result = runner.invoke(app, ["review", "--patch", patch.name, "--report-only"])

        assert result.exit_code == 0
        assert "Report only" in result.output
        assert (tmp_path / "DECISIONS.md").read_text(encoding="utf-8") == decisions_before
        assert not (tmp_path / ".flg" / "context" / "evidence_index.json").exists()
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
Because lifecycle email has higher retention impact for our stage.
We ruled out paid ads because the budget is too tight this quarter.
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


def test_review_accept_all_skips_shell_decisions(tmp_path):
    """--accept-all must NOT write shell decisions (no reasoning/alternatives/reversal) into DECISIONS.md.

    Regression for 发现 14: closeout can extract priority-list items as candidate
    decisions. When all context fields are empty, --accept-all used to write
    empty 'D-0xx' entries into DECISIONS.md, polluting the ledger.
    """
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Shell Skip Test"])
        # Bare "不做" statements — triggers tradeoff keyword but has no decision context.
        transcript = tmp_path / "workplan.md"
        transcript.write_text("""# Session

这个功能本期不做，留到下个版本。
那个支付模块暂时也不做。
""", encoding="utf-8")
        runner.invoke(app, ["closeout", "--transcript", str(transcript)])

        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        result = runner.invoke(app, ["review", "--patch", patch.name, "--accept-all"])
        # exit_code 0 means it finished (may have skipped all shells)
        assert result.exit_code == 0
        assert "shell" in result.output.lower() or "skipped" in result.output.lower()

        decisions_content = (tmp_path / "DECISIONS.md").read_text(encoding="utf-8")
        # The shell decision content must NOT have been written into DECISIONS.md.
        # (The init template ships with a "## D-001 | 标题" placeholder, so we
        # check for the shell content rather than absence of any D- entry.)
        assert "这个功能本期不做" not in decisions_content
        assert "那个支付模块暂时也不做" not in decisions_content
    finally:
        os.chdir(old_cwd)


def test_review_accept_all_writes_rich_decisions(tmp_path):
    """--accept-all must still write decisions that HAVE real context.

    Ensures the shell gate doesn't over-block legitimate decisions.
    """
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Rich Accept Test"])
        transcript = tmp_path / "rich.md"
        transcript.write_text("""# Session

我们确认采用方案A。
因为方案A的ROI更高，预算也在可控范围内。
放弃方案B，因为成本太高不可控。
""", encoding="utf-8")
        runner.invoke(app, ["closeout", "--transcript", str(transcript)])

        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        result = runner.invoke(app, ["review", "--patch", patch.name, "--accept-all"])
        assert result.exit_code == 0
        assert "Accepted" in result.output

        decisions_content = (tmp_path / "DECISIONS.md").read_text(encoding="utf-8")
        assert "方案A" in decisions_content
    finally:
        os.chdir(old_cwd)
