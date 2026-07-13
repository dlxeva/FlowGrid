"""Tests for flg closeout command."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from flg.cli import app

runner = CliRunner()


@pytest.fixture
def flg_project_with_demo(tmp_path):
    """Create a temporary FLG project with demo transcript."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    # Initialize project
    result = runner.invoke(app, ["init", "Test Project"])
    assert result.exit_code == 0
    
    # Create demo transcript
    demo_content = """# Session Transcript

## Discussion

We decided to focus on content marketing.
The goal is 1000 users in 6 weeks.
There's a risk that KOLs are too expensive.
Next step is to create a project plan.
We need to confirm the budget allocation.
"""
    transcript_path = tmp_path / "transcript.md"
    transcript_path.write_text(demo_content)
    
    yield tmp_path, transcript_path
    os.chdir(old_cwd)


def test_closeout_generates_patch(flg_project_with_demo):
    """Test that flg closeout generates a patch file."""
    project_dir, transcript = flg_project_with_demo
    
    result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
    assert result.exit_code == 0
    assert "Closeout patch generated" in result.output
    
    patches_dir = project_dir / ".flg" / "patches"
    patch_files = list(patches_dir.glob("closeout-*.patch.md"))
    assert len(patch_files) > 0, f"No closeout patch found in {list(patches_dir.iterdir())}"
    
    # Verify patch content
    patch_content = patch_files[0].read_text()
    assert "FLG Patch" in patch_content
    assert "flg closeout" in patch_content
    assert "pending_review" in patch_content


def test_closeout_extracts_decisions(flg_project_with_demo):
    """Test that flg closeout extracts decisions from transcript."""
    project_dir, transcript = flg_project_with_demo
    
    result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
    assert result.exit_code == 0
    
    patches_dir = project_dir / ".flg" / "patches"
    patch_files = list(patches_dir.glob("closeout-*.patch.md"))
    assert len(patch_files) > 0
    patch_content = patch_files[0].read_text()
    
    # Should find decision-related content
    assert "decided" in patch_content.lower() or "decision" in patch_content.lower()
    assert "**Related goals:**" in patch_content
    assert "**Affected actions:**" in patch_content


def test_closeout_extracts_risks(flg_project_with_demo):
    """Test that flg closeout extracts risks from transcript."""
    project_dir, transcript = flg_project_with_demo
    
    result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
    assert result.exit_code == 0
    
    patches_dir = project_dir / ".flg" / "patches"
    patch_files = list(patches_dir.glob("closeout-*.patch.md"))
    assert len(patch_files) > 0
    patch_content = patch_files[0].read_text()
    
    # Should find risk-related content
    assert "risk" in patch_content.lower()


def test_closeout_on_nonexistent_transcript(flg_project_with_demo):
    """Test that flg closeout fails on nonexistent transcript."""
    project_dir, _ = flg_project_with_demo
    
    result = runner.invoke(app, ["closeout", "--transcript", "nonexistent.md"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_closeout_rejects_structured_ledger_file(tmp_path):
    """Structured ledger files should be blocked as closeout input unless forced."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Guardrail Test"])
        result = runner.invoke(app, ["closeout", "--transcript", "PROGRESS.md"])
        assert result.exit_code == 1
        assert "structured ledger file" in result.output.lower()
        assert "--force" in result.output
    finally:
        os.chdir(old_cwd)


def test_closeout_force_allows_structured_ledger_file(tmp_path):
    """--force should allow explicit closeout on structured ledger files."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Force Test"])
        result = runner.invoke(app, ["closeout", "--transcript", "PROGRESS.md", "--force"])
        assert result.exit_code == 0
        assert "Closeout patch generated" in result.output
    finally:
        os.chdir(old_cwd)


def test_closeout_refreshes_snapshot(tmp_path):
    """Closeout should refresh SNAPSHOT.md with current state."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Snapshot Test"])
        # Create a transcript with decisions and risks
        transcript = tmp_path / "session.md"
        transcript.write_text("""# Session

我们确认了做A方案而不是B方案。不做C因为成本太高。
风险是时间不够，可能导致延期。

下一步：完成原型。
""", encoding="utf-8")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0
        
        # Verify SNAPSHOT.md was refreshed
        snapshot_path = tmp_path / "SNAPSHOT.md"
        assert snapshot_path.exists()
        content = snapshot_path.read_text(encoding="utf-8")
        assert "Current Stage" in content
        assert "Current Core Goal" in content
        assert "Current Core Judgments" in content
        assert "Confirmed" in content
        assert "Current Risks" in content
        assert "Next Highest Priority Action" in content
        # Should contain the decision content
        assert "A方案" in content
    finally:
        os.chdir(old_cwd)


def test_closeout_on_non_flg_project(tmp_path):
    """Test that flg closeout fails on non-FLG project."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    # Create a dummy transcript
    transcript = tmp_path / "transcript.md"
    transcript.write_text("# Test")
    
    result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
    assert result.exit_code == 1
    assert "Not a FLG project" in result.output
    
    os.chdir(old_cwd)


def test_closeout_updates_state(flg_project_with_demo):
    """Test that flg closeout updates state.json."""
    import json
    project_dir, transcript = flg_project_with_demo
    
    result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
    assert result.exit_code == 0
    
    state_path = project_dir / ".flg" / "state.json"
    state = json.loads(state_path.read_text())
    
    assert len(state["pending_patches"]) > 0
    assert "closeout" in state["pending_patches"][0]["patch_id"]
    assert state["pending_patches"][0]["source_command"] == "flg closeout"


def test_closeout_does_not_treat_plain_discussion_as_decision(tmp_path):
    """Ordinary brainstorming should not become candidate decisions."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Noise Test"])
        transcript = tmp_path / "discussion.md"
        transcript.write_text("""# Session

Maybe we could explore a PR angle.
This is just an idea for discussion.
We should think more before choosing anything.
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()
        assert "(no candidate decisions extracted)" in content
    finally:
        os.chdir(old_cwd)


def test_closeout_detects_tradeoff_decision(tmp_path):
    """Explicit sequencing trade-offs should be captured as decisions."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Tradeoff Test"])
        transcript = tmp_path / "tradeoff.md"
        transcript.write_text("""# Session

先做 landing page，paid media 延后到下一阶段。
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()
        assert "tradeoff" in content
        assert "先做 landing page" in content
    finally:
        os.chdir(old_cwd)


def test_closeout_routes_plain_question_to_open_questions(tmp_path):
    """Questions should land in open questions, not risks."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Question Test"])
        transcript = tmp_path / "questions.md"
        transcript.write_text("""# Session

Do we have enough customer evidence for this angle?
Should we confirm the budget split before the next review?
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()
        assert "Do we have enough customer evidence" in content
        assert "Should we confirm the budget split" in content
        assert "(none identified)" in content or "type:" not in content.split("## 4. Risks", 1)[1].split("## 5. Open Questions", 1)[0]
    finally:
        os.chdir(old_cwd)


def test_closeout_concise_limits_candidate_decisions(tmp_path):
    """Concise mode should cap candidate decisions at 5."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Concise Test"])
        transcript = tmp_path / "many-decisions.md"
        transcript.write_text("""# Session

We decided alpha.
We decided beta.
We decided gamma.
We decided delta.
We decided epsilon.
We decided zeta.
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript), "--mode", "concise"])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()
        assert content.count("### Candidate Decision") == 5
    finally:
        os.chdir(old_cwd)


# --- Goal 2: next-action quality tests ---

def test_next_actions_exclude_broad_goals(tmp_path):
    """Broad goals and aspirations must NOT appear as next actions."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Goal Filter Test"])
        transcript = tmp_path / "goals.md"
        transcript.write_text("""# Session

We need to generate awareness and get 1000 trial users in the first month.
The goal is 1000 users in 6 weeks.
We should focus on improving our market share.
提升品牌知名度和获取更多线索。
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()
        next_section = content.split("## 3. Suggested Next Actions")[1].split("## 4.")[0]
        # None of the broad goals should appear
        assert "1000" not in next_section
        assert "generate awareness" not in next_section
        assert "improve our market share" not in next_section
        assert "品牌知名度" not in next_section
    finally:
        os.chdir(old_cwd)


def test_next_actions_exclude_questions(tmp_path):
    """Questions must NOT appear as next actions (they belong in open questions)."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Question Filter Test"])
        transcript = tmp_path / "questions.md"
        transcript.write_text("""# Session

Should we confirm the budget split before the next review?
What about the review criteria?
Next step should we define the user personas?
我们接下来要不要确认预算分配？
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()
        next_section = content.split("## 3. Suggested Next Actions")[1].split("## 4.")[0]
        # Questions should not leak into next actions
        assert "Should we confirm" not in next_section
        assert "What about" not in next_section
        assert "要不要确认" not in next_section
    finally:
        os.chdir(old_cwd)


def test_next_actions_exclude_section_headers(tmp_path):
    """Section headers like '### Next Steps' must NOT appear as next actions."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Header Filter Test"])
        transcript = tmp_path / "headers.md"
        transcript.write_text("""# Session

### Next Steps
## Next Steps

We need to confirm the budget allocation.
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()
        next_section = content.split("## 3. Suggested Next Actions")[1].split("## 4.")[0]
        # Headers should not appear
        assert "### Next Steps" not in next_section
        # But the concrete action should
        assert "confirm the budget allocation" in next_section
    finally:
        os.chdir(old_cwd)


def test_next_actions_keep_concrete_actions(tmp_path):
    """Concrete, executable actions MUST be extracted as next actions."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Concrete Action Test"])
        transcript = tmp_path / "concrete.md"
        transcript.write_text("""# Session

Next step is to create a detailed project plan.
We need to confirm the budget allocation with the client.
Schedule a call with the client to clarify the USP.
Draft a timeline with milestones for the campaign.
同步项目状态到共享文档。
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()
        next_section = content.split("## 3. Suggested Next Actions")[1].split("## 4.")[0]
        # All concrete actions should be captured
        assert "create a detailed project plan" in next_section
        assert "confirm the budget allocation" in next_section
        assert "Schedule a call" in next_section
        assert "Draft a timeline" in next_section
        assert "同步项目状态" in next_section
    finally:
        os.chdir(old_cwd)


def test_next_actions_exclude_vague_do_that(tmp_path):
    """Vague 'do that/this/it' should not be next actions."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Vague Filter Test"])
        transcript = tmp_path / "vague.md"
        transcript.write_text("""# Session

Yes, we need to do that.
They said we want to do a launch campaign but haven't specified what that means.
The client wants to do an AI product launch.
We need to create the project plan by Friday.
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()
        next_section = content.split("## 3. Suggested Next Actions")[1].split("## 4.")[0]
        # Vague items should be excluded
        assert "do that" not in next_section
        assert "want to do a launch" not in next_section
        assert "wants to do an AI" not in next_section
        # But the concrete one should survive
        assert "create the project plan" in next_section
    finally:
        os.chdir(old_cwd)


def test_risk_recall_real_risks_surface(tmp_path):
    """Real risks (KOL cancel, delay, budget, positioning) must be detected."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Risk Recall Test"])
        transcript = tmp_path / "risks.md"
        transcript.write_text("""# Session

There's a risk that the KOLs might cancel last minute.
This could delay the whole launch timeline.
Budget might not be enough if we need to pay higher rates.
The product positioning still isn't clear — this might affect how we write the copy.
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript), "--mode", "full"])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()
        risk_section = content.split("## 4. Risks")[1].split("## 5.")[0]
        # All 4 real risks should surface
        assert "cancel" in risk_section.lower()
        assert "delay" in risk_section.lower()
        assert "budget" in risk_section.lower()
        assert "positioning" in risk_section.lower()
    finally:
        os.chdir(old_cwd)


def test_risk_with_confirmed_not_extracted_as_decision(tmp_path):
    """A risk sentence containing 'confirmed' must appear as a risk, NOT as a candidate decision.

    Regression test for: 'KOLs we confirmed might cancel' was previously
    misclassified as a decision because of the keyword 'confirmed'.
    """
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Confirmed Risk Test"])
        transcript = tmp_path / "confirmed_risk.md"
        transcript.write_text("""# Session

KOLs we confirmed might cancel last minute.
We confirmed the venue booking for the launch event.
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript), "--mode", "full"])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()

        # The risk sentence must NOT appear in decisions
        decision_section = content.split("## 2. Candidate Decisions")[1].split("## 3.")[0]
        assert "KOLs we confirmed might cancel" not in decision_section

        # The risk sentence MUST appear in risks
        risk_section = content.split("## 4. Risks")[1].split("## 5.")[0]
        assert "confirmed might cancel" in risk_section.lower() or "cancel" in risk_section.lower()

        # The real decision ("We confirmed the venue booking") should still be captured
        assert "confirmed the venue booking" in decision_section
    finally:
        os.chdir(old_cwd)


def test_risk_no_false_alarm_on_trivial_matters(tmp_path):
    """Trivial matters (colors, printers, tone) must NOT surface as risks."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "False Alarm Test"])
        transcript = tmp_path / "trivial.md"
        transcript.write_text("""# Session

Some team members prefer blue, others prefer green for the landing page.
The printer is running low on paper for internal printouts.
We discussed whether the blog tone should be formal or casual. Not a big deal.
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()
        risk_section = content.split("## 4. Risks")[1].split("## 5.")[0]
        assert "(none identified)" in risk_section
    finally:
        os.chdir(old_cwd)


# --- Goal 3: decision context enrichment tests ---

def test_decision_context_reasoning_extracted(tmp_path):
    """When a decision contains '因为', reasoning should be extracted."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Reasoning Test"])
        transcript = tmp_path / "reasoning.md"
        transcript.write_text("""# Session

我们确认采用方案A。
因为方案A的ROI更高，预算也在可控范围内。
方案B虽然更灵活，但成本太高。
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()

        # reasoning field should be populated, not '(not detected in context)'
        decision_section = content.split("## 2. Candidate Decisions")[1].split("## 3.")[0]
        assert "**Why:**" in decision_section
        assert "ROI更高" in decision_section or "因为" in decision_section
        assert "(not detected in context)" not in decision_section.split("**Why:**")[1].split("\n")[0]
    finally:
        os.chdir(old_cwd)


def test_decision_context_rejection_extracted(tmp_path):
    """When conversation mentions '放弃A选B', rejection should be extracted."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Rejection Test"])
        transcript = tmp_path / "rejection.md"
        transcript.write_text("""# Session

我们确认采用方案A。
放弃方案B，因为成本太高不可控。
方案C也被排除了，缺乏技术支持。
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()

        decision_section = content.split("## 2. Candidate Decisions")[1].split("## 3.")[0]
        assert "**Alternatives mentioned:**" in decision_section
        # Should contain either the rejection sentence
        assert "放弃" in decision_section or "排除" in decision_section
    finally:
        os.chdir(old_cwd)


def test_decision_context_reversal_extracted(tmp_path):
    """When conversation mentions '如果X就回退', reversal conditions should be extracted."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Reversal Test"])
        transcript = tmp_path / "reversal.md"
        transcript.write_text("""# Session

我们确认采用方案A。
如果方案A在三个月内达不到预期效果，就回退到方案B重新评估。
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()

        decision_section = content.split("## 2. Candidate Decisions")[1].split("## 3.")[0]
        assert "**Could reverse if:**" in decision_section
        assert "回退" in decision_section or "方案B" in decision_section
    finally:
        os.chdir(old_cwd)


def test_closeout_extracts_rationale(tmp_path):
    """Transcript containing thinking-process markers should produce rationale excerpts."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Rationale Test"])
        transcript = tmp_path / "rationale.md"
        transcript.write_text("""# Session

我在想这个方案到底靠不靠谱。
一方面成本可控，另一方面效果不确定。
I'm torn between using KOLs or doing organic growth first.
纠结了很久，最后还是决定先做内容营销。
换个角度想，也许可以两者结合。
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()
        assert "Rationale Excerpts" in content
        assert "我在想" in content
        assert "I'm torn between" in content
        assert "纠结" in content
    finally:
        os.chdir(old_cwd)


def test_closeout_lessons_learned_trigger(tmp_path):
    """Transcript containing '回头看' should trigger lessons learned reminder."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Lessons Test"])
        transcript = tmp_path / "lessons.md"
        transcript.write_text("""# Session

回头看，当初选择方案A是对的，验证了ROI更高的判断。
这个项目学到很多，下次会更早做用户调研。
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()
        assert "Lessons Learned Trigger" in content
        assert "检测到经验回收信号" in content
        assert "回头看" in content
    finally:
        os.chdir(old_cwd)


def test_closeout_no_lessons_trigger(tmp_path):
    """Ordinary transcript without reflection signals should not trigger lessons learned."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "No Lessons Test"])
        transcript = tmp_path / "ordinary.md"
        transcript.write_text("""# Session

We discussed the marketing strategy.
The budget is tight this quarter.
Next step is to create a project plan.
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()
        assert "Lessons Learned Trigger" in content
        lessons_section = content.split("## 9. Lessons Learned Trigger")[1].split("## 10.")[0]
        assert "(none identified)" in lessons_section
    finally:
        os.chdir(old_cwd)


def test_closeout_extracts_goal_evolution_signals(tmp_path):
    """Goal shifts should surface in the dedicated goal evolution section."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Goal Shift Test"])
        transcript = tmp_path / "goal_shift.md"
        transcript.write_text("""# Session

本轮目标变化：从做完整平台改成先做可续接的判断协议。
The goal is now to validate continuity instead of multi-agent relay.
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()
        goal_section = content.split("## 6. Goal Evolution Signals")[1].split("## 7.")[0]
        assert "目标变化" in goal_section or "goal is now" in goal_section.lower()
    finally:
        os.chdir(old_cwd)


# --- Shell decision detection (发现 14) ---

def test_closeout_flags_shell_decision_low_confidence(tmp_path):
    """A candidate decision with no reasoning/alternatives/reversal must be flagged low_confidence.

    Regression for 发现 14: closeout's trade-off trigger words ('优先','边界'...)
    fire on work-plan priority lists that carry no real decision context.
    These shells should stay in the patch but be marked so review can block them.
    """
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Shell Flag Test"])
        # "优先" triggers tradeoff detection, but the sentence is a bare
        # priority list item with no why/alternatives/reversal anywhere nearby.
        transcript = tmp_path / "workplan.md"
        transcript.write_text("""# Session

第一优先级：完成落地页。
第二优先级：对接支付。
""", encoding="utf-8")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()

        decision_section = content.split("## 2. Candidate Decisions")[1].split("## 3.")[0]
        assert "low_confidence_shell" in decision_section
        assert "confidence: low" in decision_section
        assert "needs_review_blocked_accept_all" in decision_section
    finally:
        os.chdir(old_cwd)


def test_closeout_does_not_flag_rich_decision_as_shell(tmp_path):
    """A decision with reasoning extracted must NOT be flagged as shell."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Rich Decision Test"])
        transcript = tmp_path / "rich.md"
        transcript.write_text("""# Session

我们确认采用方案A。
因为方案A的ROI更高，预算也在可控范围内。
放弃方案B，因为成本太高不可控。
""")
        result = runner.invoke(app, ["closeout", "--transcript", str(transcript)])
        assert result.exit_code == 0
        patch = next((tmp_path / ".flg" / "patches").glob("closeout-*.patch.md"))
        content = patch.read_text()

        decision_section = content.split("## 2. Candidate Decisions")[1].split("## 3.")[0]
        assert "low_confidence_shell" not in decision_section
    finally:
        os.chdir(old_cwd)


def test_closeout_llm_write_flags_shell_decision(tmp_path):
    """--llm-write (Hermes/LLM JSON) path must also flag shell decisions.

    Regression: the shell gate was first added only to the keyword path.
    The LLM and Hermes paths (_do_llm_closeout / _finalize_llm_result)
    build candidate decisions without going through extract_decisions, so
    they need the same is_shell_decision check applied at patch-build time.
    """
    import json

    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "LLM Shell Test"])
        transcript = tmp_path / "session.md"
        transcript.write_text("# Session\n\nSome context.\n", encoding="utf-8")

        # JSON with a shell decision (empty why/rejected/reverse_condition)
        # and a rich decision (all fields filled).
        llm_result = [
            {
                "id": "D-HERMES-001",
                "what": "第一优先级：完成落地页",
                "type": "tradeoff",
                "confidence": "high",
                "why": "",
                "rejected": "",
                "reverse_condition": "",
            },
            {
                "id": "D-HERMES-002",
                "what": "采用方案A",
                "type": "confirmation",
                "confidence": "high",
                "why": "方案A ROI更高",
                "rejected": "方案B成本太高",
                "reverse_condition": "如果三个月无效果则回退",
            },
        ]
        json_path = tmp_path / "llm-result.json"
        json_path.write_text(json.dumps(llm_result, ensure_ascii=False), encoding="utf-8")

        result = runner.invoke(app, ["closeout", "--llm-write", str(json_path), "--transcript", str(transcript)])
        assert result.exit_code == 0

        patch = next((tmp_path / ".flg" / "patches").glob("closeout-hermes-*.patch.md"))
        content = patch.read_text()

        # Shell decision should be flagged
        assert "low_confidence_shell" in content
        assert "needs_review_blocked_accept_all" in content
        # Rich decision should NOT be flagged
        # Count: exactly one shell flag (the rich one must not trigger it)
        assert content.count("low_confidence_shell") == 1
    finally:
        os.chdir(old_cwd)
