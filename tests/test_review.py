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

User: We decided to focus on content marketing.
User: Because paid ads are too expensive for this phase.
User: Next step is to confirm budget allocation.
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

User: We decided to focus on lifecycle email.
User: Because lifecycle email has higher retention impact for our stage.
User: We ruled out paid ads because the budget is too tight this quarter.
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


def test_review_autonomous_skips_assistant_narration_shell_candidate(tmp_path):
    """A role-labelled assistant proposal may remain a shell, never a decision.

    The real Relationship Fable Lab replay contained an assistant's proposal,
    not a user-confirmed judgment. Keyword extraction can preserve it as an
    auditable low-confidence candidate, but background review and merge must
    keep it out of DECISIONS.md and clear the pending-patch state.
    """
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Assistant Narration Test"])
        transcript = tmp_path / "host-transcript.md"
        transcript.write_text(
            """# Host transcript

User: Continue.

Assistant: 有，而且我建议把这件事从“找对标号”改成“建立选题证据链”。
""",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript), "--no-llm"])
        assert result.exit_code == 0

        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        patch_content = patch.read_text(encoding="utf-8")
        assert "Assistant: 有，而且我建议" in patch_content
        assert "low_confidence_shell" in patch_content

        result = runner.invoke(app, ["review", "--patch", patch.name, "--autonomous"])
        assert result.exit_code == 0
        assert "shell decision" in result.output

        result = runner.invoke(app, ["merge", "--patch", patch.name, "--yes"])
        assert result.exit_code == 0

        decisions_content = (tmp_path / "DECISIONS.md").read_text(encoding="utf-8")
        assert "建立选题证据链" not in decisions_content

        result = runner.invoke(app, ["status"])
        assert "No pending patches needing review" in result.output
    finally:
        os.chdir(old_cwd)


def test_review_autonomous_skips_rich_assistant_proposal(tmp_path):
    """A well-reasoned Assistant proposal still lacks authority to become a user decision."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Assistant Authority Test"])
        transcript = tmp_path / "host-transcript.md"
        transcript.write_text(
            "Assistant: We decided to use the enterprise plan because it has audit logs.\n"
            "Assistant: We rejected the starter plan because it lacks role controls.\n"
            "Assistant: If the team stays under two people, we can revisit this.\n",
            encoding="utf-8",
        )
        runner.invoke(app, ["closeout", "--transcript", str(transcript), "--no-llm"])
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))

        result = runner.invoke(app, ["review", "--patch", patch.name, "--autonomous"])
        assert result.exit_code == 0
        assert "no explicit user-authored source" in result.output
        assert "enterprise plan" not in (tmp_path / "DECISIONS.md").read_text(encoding="utf-8")
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

用户：我们确认采用方案A。
用户：因为方案A的ROI更高，预算也在可控范围内。
用户：放弃方案B，因为成本太高不可控。
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


def test_review_autonomous_records_medium_authority(tmp_path):
    """Background adoption must not be recorded as a high-authority review."""
    import json

    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Autonomous Authority Test"])
        transcript = tmp_path / "rich.md"
        transcript.write_text("""# Session

用户：我们确认采用方案A。
用户：因为方案A的ROI更高，预算也在可控范围内。
用户：放弃方案B，因为成本太高不可控。
""", encoding="utf-8")
        runner.invoke(app, ["closeout", "--transcript", str(transcript)])

        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        result = runner.invoke(app, ["review", "--patch", patch.name, "--autonomous"])
        assert result.exit_code == 0
        assert "Accepted" in result.output

        index = json.loads((tmp_path / ".flg" / "context" / "evidence_index.json").read_text(encoding="utf-8"))
        item = next(iter(index["items"].values()))
        assert item["authority"] == "medium"
        assert item["source_type"] == "closeout_patch"
    finally:
        os.chdir(old_cwd)
