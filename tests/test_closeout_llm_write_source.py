"""JSON result attribution requires a complete quote in the supplied source."""

import json

import pytest
from typer.testing import CliRunner

from flg.cli import app
from flg.commands.handoff import parse_patch_for_handoff
from flg.commands.review import _has_user_attribution

runner = CliRunner()


@pytest.mark.parametrize("excerpt", [
    "User: We decided to keep the ledger local because privacy matters.",
    "用户：确认只在本地保存，因为资料需要保密。",
    "User: " + ("A complete source statement must retain every character. " * 5).rstrip(),
])
def test_llm_write_keeps_verified_user_quote(tmp_path, monkeypatch, excerpt):
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["init", "Attribution test"]).exit_code == 0
    transcript = tmp_path / "raw.md"
    transcript.write_text(f"# Raw session\n\n{excerpt}\n\nAssistant: I will prepare a candidate.\n")
    result_json = tmp_path / "result.json"
    result_json.write_text(json.dumps([{
        "what": "Keep the ledger local", "why": "Privacy matters",
        "source_excerpt": excerpt, "source_actor": "assistant",
    }]))
    result = runner.invoke(app, ["closeout", "--llm-write", str(result_json), "--transcript", str(transcript)])
    assert result.exit_code == 0, result.output
    content = next((tmp_path / ".flg/patches").glob("closeout-hermes-*.patch.md")).read_text()
    decision = parse_patch_for_handoff(content)["decisions"][0]
    assert decision["excerpt"] == excerpt
    assert f"source_excerpt: > {excerpt}\n" in content
    assert decision["source_actor"] == "user"
    assert _has_user_attribution(decision)
    assert "status: pending_review" in content
    # Generating an auditable candidate never writes the formal decision log.
    assert "Keep the ledger local" not in (tmp_path / "DECISIONS.md").read_text()


@pytest.mark.parametrize("raw,excerpt,provide_transcript", [
    ("User: Approved the local plan.", "User: Approved a different plan.", True),
    ("Assistant: Approved the local plan.", "Assistant: Approved the local plan.", True),
    ("Approved the local plan.", "Approved the local plan.", True),
    ("User: Approved the local plan.", "User: Approved the local plan.", False),
    ("User: Approved the local plan.", None, True),
    ("User: Approved the local plan.", {"quote": "User: Approved the local plan."}, True),
    ("Assistant: A proposal mentions User: Approved the local plan.", "User: Approved the local plan.", True),
    ("User: Approved the local plan. Additional conditions apply.", "User: Approved the local plan.", True),
    ("User: Approved the local plan.\nOnly if the privacy check passes.", "User: Approved the local plan.", True),
    ("User: Approved the local plan.\nAssistant: Expand the scope.", "User: Approved the local plan.\nAssistant: Expand the scope.", True),
    ("User: Approved the local plan. Assistant: Expand the scope.", "User: Approved the local plan. Assistant: Expand the scope.", True),
    ("User:\nApproved the local plan.", "User:\nApproved the local plan.", True),
    ("## Agent Summary\nUser: Approved the local plan.", "User: Approved the local plan.", True),
    ("```text\nUser: Approved the local plan.\n```", "User: Approved the local plan.", True),
])
def test_llm_write_does_not_trust_unverified_or_cross_actor_source(tmp_path, monkeypatch, raw, excerpt, provide_transcript):
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["init", "Unverified attribution test"]).exit_code == 0
    transcript = tmp_path / "raw.md"
    transcript.write_text(raw)
    result_json = tmp_path / "result.json"
    result_json.write_text(json.dumps([{
        # Even a labelled generated title must not become the source fallback.
        "what": "User: Approved the local plan.", "why": "A plausible generated reason",
        "source_excerpt": excerpt, "source_actor": "user",
    }]))
    args = ["closeout", "--llm-write", str(result_json)]
    if provide_transcript:
        args += ["--transcript", str(transcript)]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    content = next((tmp_path / ".flg/patches").glob("closeout-hermes-*.patch.md")).read_text()
    decision = parse_patch_for_handoff(content)["decisions"][0]
    assert decision["source_actor"] == "unknown"
    assert decision["excerpt"] == "(source excerpt not verified against raw transcript)"
    assert not _has_user_attribution(decision)
    assert "status: pending_review" in content
