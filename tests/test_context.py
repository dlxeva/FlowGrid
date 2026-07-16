"""Tests for flg context command (Context Pack quality).

发现 19: template placeholder noise leaked into Recent Progress / Active
Constraints / Superseded Judgments sections.
发现 20: confirmed decisions (reviewed+accepted patches) showed up again
in Pending Judgments — redundant.
发现 25: rejected/discarded patches still appeared in Pending Judgments.
"""

import glob
import os
import os.path

from typer.testing import CliRunner

from flg.cli import app

runner = CliRunner()


def _init_and_get_context(tmp_path):
    """Init a project and return the context pack output."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Context Test"])
        result = runner.invoke(app, ["context", "--print"])
        return result
    finally:
        os.chdir(old_cwd)


def test_context_pack_excludes_template_noise(tmp_path):
    """Fresh project's context pack must NOT contain template boilerplate.

    Regression for 发现 19: Recent Progress and Active Constraints used to
    show init-template instructions like '记录重要文档的演化关系' and
    '适合运营机制、解决方案边界'.
    """
    result = _init_and_get_context(tmp_path)
    assert result.exit_code == 0
    output = result.output

    # Template instruction lines must not appear
    assert "记录重要文档的演化关系" not in output
    assert "适合运营机制" not in output
    assert "文档版本关系不再散落" not in output

    # Placeholder headings must not appear
    assert "[文档名称]" not in output
    assert "Constraint 001" not in output


def test_context_pack_excludes_superseded_template_items(tmp_path):
    """GOAL_EVOLUTION template items must not appear in Superseded Judgments.

    Regression for 发现 19: '(日期)' '(之前的目标)' etc. leaked through.
    """
    result = _init_and_get_context(tmp_path)
    assert result.exit_code == 0
    output = result.output

    assert "(之前的目标)" not in output
    assert "(现在的目标)" not in output
    assert "(触发变化的事件" not in output
    assert "{created_at}" not in output


def test_context_pack_excludes_superseded_formal_decisions(tmp_path):
    """Historical decisions remain indexed but must not drive current startup context."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Superseded Decision Test"])
        decisions = tmp_path / "DECISIONS.md"
        decisions.write_text(
            decisions.read_text(encoding="utf-8")
            + """\n\n## D-002 | Retired environment\n\n### 决策状态\nsuperseded\n\n### 最终决策\nUse the retired environment path.\n\n### 决策理由\nHistorical only.\n\n### 备选方案\nUse the current path.\n\n### 放弃理由\nThe current path replaced it.\n\n### 复盘入口\nNone.\n""",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["context", "--print"])
        assert result.exit_code == 0
        assert "Retired environment" not in result.output
    finally:
        os.chdir(old_cwd)


def test_context_pack_excludes_rejected_patches(tmp_path):
    """Rejected/discarded patches must NOT appear in Pending Judgments (发现 25)."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Rejected Patch Test"])

        # Generate a patch
        transcript = tmp_path / "session.md"
        transcript.write_text("""# Session

我们确认采用方案A。
因为方案A加载快。
放弃方案B，因为太重。
""", encoding="utf-8")
        runner.invoke(app, ["closeout", "--transcript", str(transcript), "--no-llm"])

        patch_file = glob.glob(str(tmp_path / ".flg" / "patches" / "closeout-*.patch.md"))[0]
        patch_name = os.path.basename(patch_file)

        # Discard it
        runner.invoke(app, ["patch", "discard", patch_name, "--reason", "test"])

        # Context pack should not show it in Pending Judgments
        result = runner.invoke(app, ["context", "--print"])
        assert result.exit_code == 0
        assert patch_name not in result.output or "Pending Judgments" not in result.output.split(patch_name)[0] if patch_name in result.output else True
        # The patch content should not appear as a pending judgment
        # (it may appear in the Sources Included list, which is fine)
        pending_section = result.output.split("## Pending Judgments")[1].split("##")[0] if "## Pending Judgments" in result.output else ""
        assert patch_name not in pending_section
    finally:
        os.chdir(old_cwd)


def test_context_pack_excludes_reviewed_accepted_patches(tmp_path):
    """Patches whose decisions were reviewed+accepted must NOT reappear in Pending (发现 20)."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Reviewed Patch Test"])

        transcript = tmp_path / "session.md"
        transcript.write_text("""# Session

我们确认采用方案A。
因为方案A加载快。
放弃方案B，因为太重。
""", encoding="utf-8")
        runner.invoke(app, ["closeout", "--transcript", str(transcript), "--no-llm"])

        patch_file = glob.glob(str(tmp_path / ".flg" / "patches" / "closeout-*.patch.md"))[0]
        patch_name = os.path.basename(patch_file)

        # Review and accept all
        runner.invoke(app, ["review", "--patch", patch_name, "--accept-all"])

        # Context pack should show the decision in Confirmed, NOT in Pending
        result = runner.invoke(app, ["context", "--print"])
        assert result.exit_code == 0
        output = result.output

        # Decision should be in Confirmed Decisions
        assert "方案A" in output

        # The patch should NOT appear in Pending Judgments section
        if "## Pending Judgments" in output:
            pending_section = output.split("## Pending Judgments")[1].split("##")[0]
            assert patch_name not in pending_section
    finally:
        os.chdir(old_cwd)


def test_context_pack_preserves_decision_alternatives(tmp_path):
    """Direct decisions keep their alternatives in the generated context."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Alternatives Test"])
        result = runner.invoke(
            app,
            [
                "decision",
                "add",
                "--decision",
                "Use the local path",
                "--rationale",
                "It is auditable",
                "--alternatives",
                "Use a hosted path, defer the decision",
            ],
        )
        assert result.exit_code == 0

        result = runner.invoke(app, ["context", "--print"])
        assert result.exit_code == 0
        assert "Alternatives considered: A. Use a hosted path、defer the decision" in result.output
    finally:
        os.chdir(old_cwd)
