"""Synthetic host continuation: no private project data or runtime activation."""
import json
import os
from pathlib import Path
import subprocess
import sys

from typer.testing import CliRunner

from flg.cli import app
from flg.commands.context import build_context_pack
from flg.commands.handoff import generate_handoff_summary
from flg.core.source_receipts import digest
from flg.core.task_continuity import show


runner = CliRunner()


def declare_work(root):
    (root / "work.md").write_text("## Current Action\n- Review the local draft.\n", encoding="utf-8")
    path = root / ".flg/state.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["work_source"] = {"schema_version": "1", "path": "work.md"}
    path.write_text(json.dumps(state), encoding="utf-8")


def ref(root, name):
    return {"path": name, "sha256": digest((root / name).read_bytes())}


def command(root, args, payload=None):
    if payload is not None:
        (root / "host-request.json").write_text(json.dumps(payload), encoding="utf-8")
        args = [*args, "--input", "host-request.json"]
    return runner.invoke(app, args)


def setup(root, monkeypatch):
    monkeypatch.chdir(root)
    assert runner.invoke(app, ["init", "Synthetic continuation"]).exit_code == 0
    declare_work(root)
    (root / "request.md").write_text("User: Register T17 for local draft continuation only.\n", encoding="utf-8")
    (root / "goal.md").write_text("Produce the local research draft.\n", encoding="utf-8")
    (root / "acceptance.md").write_text("Deliver draft.md for later human review; no formal approval.\n", encoding="utf-8")
    enabled = command(root, ["task", "enable"], {"actor": "owner", "request_ref": ref(root, "request.md")})
    assert enabled.exit_code == 0, enabled.output
    request = {"action": "register", "expected_revision": 0, "operation_id": "register-1",
               "actor": "owner", "owner": "owner", "goal_ref": ref(root, "goal.md"),
               "acceptance_ref": ref(root, "acceptance.md"), "criteria": [{"id": "draft", "path": "draft.md"}]}
    registered = command(root, ["task", "apply", "T17"], request)
    assert registered.exit_code == 0, registered.output


def operation(root, action, actor="owner", **fields):
    return {"action": action, "expected_revision": show(root, "T17")["revision"],
            "operation_id": f"{action}-{show(root, 'T17')['revision']}", "actor": actor, **fields}


def apply_ok(root, payload):
    result = command(root, ["task", "apply", "T17"], payload)
    assert result.exit_code == 0, result.output
    return result


def test_disabled_project_views_do_not_create_task_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["init", "Legacy unchanged"]).exit_code == 0
    declare_work(tmp_path)
    baseline_doctor = runner.invoke(app, ["doctor", "--strict"])
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = command(tmp_path, ["task", "list"])
    assert result.exit_code == 0 and json.loads(result.output)["enabled"] is False
    for mode in ("resume", "manifest", "work"):
        content, metadata = build_context_pack(tmp_path, mode=mode)
        assert ".flg/tasks/" not in metadata["sources_included"]
        assert "Local task continuation" not in content
    assert "Local task continuation" not in generate_handoff_summary(tmp_path)
    assert runner.invoke(app, ["status"]).exit_code == 0
    doctor = runner.invoke(app, ["doctor", "--strict"])
    assert (doctor.exit_code, doctor.output) == (baseline_doctor.exit_code, baseline_doctor.output)
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after


def test_new_process_resume_takeover_and_local_completion(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    protected = {name: (tmp_path / name).read_bytes() for name in
                 ("PROJECT.md", "DECISIONS.md", "SNAPSHOT.md", "PROGRESS.md", ".flg/state.json")}
    apply_ok(tmp_path, operation(tmp_path, "takeover", executor="agent-a", attempt_id="attempt-a"))
    (tmp_path / "session.md").write_text("User: Continue the draft later.\n", encoding="utf-8")
    saved = runner.invoke(app, ["session", "save", "session.md", "--name", "first-session"])
    assert saved.exit_code == 0, saved.output
    assert show(tmp_path, "T17")["status"] == "running"

    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    result = subprocess.run([sys.executable, "-c", "from flg.cli import app; app()", "task", "show", "T17"],
                            cwd=tmp_path, env=env, text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["task_id"] == "T17"
    old = operation(tmp_path, "progress", actor="agent-a", attempt_id="attempt-a",
                    evidence_refs=[ref(tmp_path, "goal.md")])
    apply_ok(tmp_path, operation(tmp_path, "takeover", executor="agent-b", attempt_id="attempt-b"))
    rejected = command(tmp_path, ["task", "apply", "T17"], old)
    assert rejected.exit_code == 2
    # A stale worker cannot regain write access by merely refreshing revision.
    old.update(expected_revision=show(tmp_path, "T17")["revision"])
    assert command(tmp_path, ["task", "apply", "T17"], old).exit_code == 2

    missing = operation(tmp_path, "complete", actor="agent-b", attempt_id="attempt-b",
                        evidence_refs=[ref(tmp_path, "goal.md")])
    assert command(tmp_path, ["task", "apply", "T17"], missing).exit_code == 2
    (tmp_path / "draft.md").write_text("Draft for later review.\n", encoding="utf-8")
    complete = operation(tmp_path, "complete", actor="agent-b", attempt_id="attempt-b",
                         evidence_refs=[ref(tmp_path, "draft.md")])
    apply_ok(tmp_path, complete)
    state = show(tmp_path, "T17")
    assert state["status"] == "completed"
    first = (tmp_path / ".flg/tasks/T17.json").read_bytes()
    apply_ok(tmp_path, complete)
    assert (tmp_path / ".flg/tasks/T17.json").read_bytes() == first
    for name, raw in protected.items():
        assert (tmp_path / name).read_bytes() == raw


def test_waiting_projection_read_repetition_and_cancel(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    apply_ok(tmp_path, operation(tmp_path, "takeover", executor="agent", attempt_id="a1"))
    apply_ok(tmp_path, operation(tmp_path, "wait", actor="agent", attempt_id="a1",
                                waiting={"condition": "Need reviewed input", "trigger": "Owner reviews new input",
                                         "evidence_ref": ref(tmp_path, "request.md")}))
    taskfile = tmp_path / ".flg/tasks/T17.json"
    raw, mtime = taskfile.read_bytes(), taskfile.stat().st_mtime_ns
    for _ in range(2):
        for mode in ("resume", "manifest", "work"):
            content, metadata = build_context_pack(tmp_path, mode=mode, budget=4000)
            assert "T17" in content and "waiting" in content
            assert ".flg/tasks/" in metadata["sources_included"]
            assert ".flg/processing-receipts.json" not in metadata["sources_included"]
        assert "T17" in generate_handoff_summary(tmp_path)
        assert "T17" in runner.invoke(app, ["status"]).output
    assert taskfile.read_bytes() == raw and taskfile.stat().st_mtime_ns == mtime
    apply_ok(tmp_path, operation(tmp_path, "cancel"))
    (tmp_path / "new-input.md").write_text("New input after cancellation.\n", encoding="utf-8")
    assert show(tmp_path, "T17")["status"] == "cancelled"
    assert command(tmp_path, ["task", "apply", "T17"], operation(tmp_path, "resume")).exit_code == 2


def test_source_drift_doctor_and_read_views_preserve_state(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    (tmp_path / "goal.md").write_text("Changed goal; needs owner review.\n", encoding="utf-8")
    taskfile = tmp_path / ".flg/tasks/T17.json"
    raw = taskfile.read_bytes()
    result = runner.invoke(app, ["doctor", "--strict"])
    assert result.exit_code == 1 and "Task continuity" in result.output
    for mode in ("resume", "manifest", "work"):
        content, _ = build_context_pack(tmp_path, mode=mode, budget=4000)
        assert "T17" in content and "needs_recheck" in content
    assert taskfile.read_bytes() == raw
    denied = command(tmp_path, ["task", "apply", "T17"], operation(tmp_path, "takeover", executor="agent", attempt_id="a1"))
    assert denied.exit_code == 2
    # Drift must not trap an owner in active work or prevent cancellation.
    apply_ok(tmp_path, operation(tmp_path, "cancel"))


def test_cli_input_paths_and_conflicting_enable_fail_without_writes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["init", "Safe inputs"]).exit_code == 0
    assert runner.invoke(app, ["task", "enable", "--input", "../outside.json"]).exit_code == 2
    result = command(tmp_path, ["task", "enable"], {"enabled": False})
    assert result.exit_code == 2 and not (tmp_path / ".flg/task-continuity.json").exists()


def test_unconfigured_legacy_task_folder_does_not_opt_project_in(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["init", "Legacy task folder"]).exit_code == 0
    folder = tmp_path / ".flg/tasks"
    folder.mkdir()
    legacy = folder / "unrelated-legacy-notes.md"
    legacy.write_text("Old project notes, not continuity records.\n", encoding="utf-8")
    before = legacy.read_bytes()
    listed = command(tmp_path, ["task", "list"])
    assert listed.exit_code == 0 and json.loads(listed.output)["enabled"] is False
    assert "Task continuity" not in runner.invoke(app, ["status"]).output
    assert legacy.read_bytes() == before
    assert not (tmp_path / ".flg/task-continuity.json").exists()


def test_bounded_task_notice_retains_existing_context(tmp_path, monkeypatch):
    from flg.core.task_continuity import render_notice
    setup(tmp_path, monkeypatch)
    _, baseline_metadata = build_context_pack(tmp_path, mode="resume", budget=4000)
    for index in range(15):
        payload = {"action": "register", "expected_revision": 0, "operation_id": f"new-{index}",
                   "actor": "owner", "owner": "owner", "goal_ref": ref(tmp_path, "goal.md"),
                   "acceptance_ref": ref(tmp_path, "acceptance.md"),
                   "criteria": [{"id": "draft", "path": "draft.md"}]}
        result = command(tmp_path, ["task", "apply", f"TASK-{index:02}"], payload)
        assert result.exit_code == 0, result.output
    notice = render_notice(tmp_path)
    assert len(notice) < 2500 and "omitted" in notice
    content, metadata = build_context_pack(tmp_path, mode="resume", budget=4000)
    assert "## Current Action" in content
    assert metadata["current_action"] == baseline_metadata["current_action"]
    work_content, _ = build_context_pack(tmp_path, mode="work", budget=4000)
    assert "Review the local draft" in work_content
    assert metadata["chars"] <= 16000


def test_unsupported_formal_approval_and_external_effects_are_rejected(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    raw = (tmp_path / ".flg/tasks/T17.json").read_bytes()
    for action in ("approve", "publish", "permit", "retry_external"):
        result = command(tmp_path, ["task", "apply", "T17"], operation(tmp_path, action))
        assert result.exit_code == 2
    assert (tmp_path / ".flg/tasks/T17.json").read_bytes() == raw
