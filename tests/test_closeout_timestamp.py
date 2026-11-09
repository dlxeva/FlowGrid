"""Closeout records completion only after a patch is written and registered."""

import importlib
import json
from datetime import datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from flg.cli import app
from flg.core.state import load_state, update_state

closeout = importlib.import_module("flg.commands.closeout")
runner = CliRunner()
PREVIOUS_CLOSEOUT = "2000-01-01T00:00:00"
PATCH_MODES = ["keyword", "llm", "llm-empty", "llm-write", "llm-fallback"]


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["init", "Timestamp regression"]).exit_code == 0
    update_state(tmp_path, last_closeout_at=PREVIOUS_CLOSEOUT, private_extension={"keep": True})
    transcript = tmp_path / "session.md"
    transcript.write_text("User: We decided to keep the ledger local because privacy matters.\n")
    result_json = tmp_path / "result.json"
    result_json.write_text(json.dumps([{"what": "Keep the ledger local", "why": "Privacy"}]))
    # All LLM paths are synthetic; no request can leave the process.
    monkeypatch.setattr(closeout, "is_llm_available", lambda *args: True)
    monkeypatch.setattr(closeout, "is_local_endpoint", lambda *args: True)
    monkeypatch.setattr(closeout, "get_llm_config", lambda: {"model": "test-model"})
    monkeypatch.setattr(closeout, "call_llm", lambda *args, **kwargs: "synthetic response")
    monkeypatch.setattr(closeout, "parse_llm_response", lambda response: [{
        "content": "Keep the ledger local", "reasoning": "Privacy",
    }])
    return tmp_path, transcript, result_json


def invoke_mode(project, monkeypatch, mode):
    root, transcript, result_json = project
    if mode == "llm-write":
        return runner.invoke(app, ["closeout", "--llm-write", str(result_json)])
    if mode == "llm-empty":
        monkeypatch.setattr(closeout, "parse_llm_response", lambda response: [])
    if mode == "llm-fallback":
        def fail_llm(*args, **kwargs):
            raise RuntimeError("synthetic provider failure")
        monkeypatch.setattr(closeout, "call_llm", fail_llm)
    extraction_args = ["--no-llm"] if mode == "keyword" else ["--llm", "local"]
    return runner.invoke(app, ["closeout", "--transcript", str(transcript), *extraction_args])


@pytest.mark.parametrize("mode", PATCH_MODES)
def test_successful_closeout_updates_timestamp_and_preserves_registered_patch(project, monkeypatch, mode):
    started = datetime.now()
    result = invoke_mode(project, monkeypatch, mode)
    assert result.exit_code == 0, result.output
    state = load_state(project[0])
    completed = datetime.fromisoformat(state["last_closeout_at"])
    assert started.replace(microsecond=0) <= completed <= datetime.now()
    assert state["private_extension"] == {"keep": True}
    assert len(state["pending_patches"]) == 1
    assert Path(state["pending_patches"][0]["path"]).is_file()


@pytest.mark.parametrize("mode", PATCH_MODES)
@pytest.mark.parametrize("failure_point", ["create_patch", "add_pending_patch"])
def test_failed_closeout_keeps_previous_timestamp(project, monkeypatch, mode, failure_point):
    def fail(*args, **kwargs):
        raise OSError("synthetic persistence failure")
    monkeypatch.setattr(closeout, failure_point, fail)
    result = invoke_mode(project, monkeypatch, mode)
    assert result.exit_code != 0
    assert isinstance(result.exception, OSError)
    state = load_state(project[0])
    assert state["last_closeout_at"] == PREVIOUS_CLOSEOUT
    assert not state["pending_patches"]
    assert "✓" not in result.output


@pytest.mark.parametrize("mode", ["prompt", "hermes", "llm-write-empty"])
def test_preparation_without_patch_keeps_previous_timestamp(project, mode):
    root, transcript, result_json = project
    if mode == "llm-write-empty":
        result_json.write_text("[]")
        args = ["--llm-write", str(result_json)]
    else:
        args = ["--transcript", str(transcript)]
        args += ["--prompt"] if mode == "prompt" else ["--llm", "hermes"]
    result = runner.invoke(app, ["closeout", *args])
    assert result.exit_code == 0, result.output
    state = load_state(root)
    assert state["last_closeout_at"] == PREVIOUS_CLOSEOUT
    assert not state["pending_patches"]


@pytest.mark.parametrize("mode", PATCH_MODES)
def test_timestamp_persistence_failure_does_not_report_success(project, monkeypatch, mode):
    def fail(*args, **kwargs):
        raise OSError("synthetic timestamp persistence failure")
    monkeypatch.setattr(closeout, "update_state", fail)
    result = invoke_mode(project, monkeypatch, mode)
    assert result.exit_code != 0
    assert isinstance(result.exception, OSError)
    assert "✓" not in result.output
    state = load_state(project[0])
    assert state["last_closeout_at"] == PREVIOUS_CLOSEOUT
    # A completed patch remains recoverable even if its timestamp write fails.
    assert len(state["pending_patches"]) == 1
    assert Path(state["pending_patches"][0]["path"]).is_file()
