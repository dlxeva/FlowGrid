"""Synthetic local-only contract tests; no real ledger or network writes."""
from copy import deepcopy
from datetime import datetime
import json

import pytest

from flg.core import capture_followup, task_continuity as tc
from flg.core.source_receipts import digest


def snapshot(root):
    return {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


def ref(root, path="goal.md", quote=None):
    result = {"path": path, "sha256": digest(quote if quote is not None else (root / path).read_bytes())}
    if quote is not None:
        result["quote"] = quote
    return result


@pytest.fixture
def root(tmp_path):
    (tmp_path / ".flg").mkdir()
    for path, text in {"goal.md": "User: keep the goal.\nOther context.\n",
                       "accept.md": "User: deliver artifact.bin.\nOther context.\n",
                       "request.md": "User: explicitly enable local continuity.\n",
                       "evidence.md": "Local inspection result.\n", "artifact.bin": "exact output\n",
                       ".flg/state.json": '{"untouched": true}', "SESSION.md": "open session\n"}.items():
        (tmp_path / path).write_text(text)
    return tmp_path


def configure(root, enabled=True):
    return tc.configure(root, {"enabled": enabled, "actor": "owner", "request_ref": ref(root, "request.md")})


def register(root, task_id="task-1", **extra):
    data = {"action": "register", "actor": "owner", "expected_revision": 0, "operation_id": "register",
            "owner": "owner", "goal_ref": ref(root), "acceptance_ref": ref(root, "accept.md"),
            "criteria": [{"id": "artifact", "path": "artifact.bin"}], **extra}
    return tc.apply(root, task_id, data)


def op(root, action, *, actor="owner", task_id="task-1", **extra):
    revision = tc.show(root, task_id)["revision"]
    data = {"action": action, "actor": actor, "expected_revision": revision,
            "operation_id": f"{action}-{revision}", **extra}
    return tc.apply(root, task_id, data)


def running(root):
    configure(root)
    register(root)
    op(root, "takeover", executor="worker", attempt_id="attempt-1")


def test_disabled_zero_writes(root):
    before = snapshot(root)
    assert tc.collect(root) == {"enabled": False, "tasks": [], "issues": []}
    assert tc.render_notice(root) == ""
    assert tc.show(root, "task-1")["enabled"] is False
    with pytest.raises(ValueError, match="disabled"):
        register(root)
    assert snapshot(root) == before


def test_complete_local_artifacts_preserves_sources_and_session(root):
    before = snapshot(root)
    running(root)
    task = tc.show(root, "task-1")
    assert task["status"] == "running" and task["revision"] == 2
    assert {k: task["active_attempt"][k] for k in ("attempt_id", "executor", "status")} == {
        "attempt_id": "attempt-1", "executor": "worker", "status": "running"}
    assert task["active_attempt"]["started_at"].endswith("+00:00")
    assert task["active_attempt"]["ended_at"] is None
    assert task["action_ref"] is None
    assert task["checks"]["project_action_permission"] is False
    op(root, "progress", actor="worker", attempt_id="attempt-1", evidence_refs=[ref(root, "evidence.md")])
    op(root, "complete", actor="worker", attempt_id="attempt-1", evidence_refs=[ref(root, "artifact.bin")])
    task = tc.show(root, "task-1")
    assert task["status"] == "completed" and task["completion_scope"] == "local_artifacts"
    assert task["active_attempt"] is None and task["attempts"][0]["status"] == "ended"
    for path, value in before.items():
        assert snapshot(root)[path] == value
    with pytest.raises(ValueError, match="Terminal"):
        op(root, "resume")
    configure(root, False)
    assert (root / ".flg/tasks/task-1.json").exists()
    assert tc.collect(root)["enabled"] is False


def test_disable_refuses_any_open_work(root):
    running(root)
    before = snapshot(root)
    with pytest.raises(ValueError, match="unresolved"):
        configure(root, False)
    assert snapshot(root) == before
    op(root, "pause")
    with pytest.raises(ValueError, match="unresolved"):
        configure(root, False)
    op(root, "cancel")
    configure(root, False)


@pytest.mark.parametrize("bad", [True, False, -1, 1.5, "0", None])
def test_revision_types(root, bad):
    configure(root)
    with pytest.raises(ValueError):
        tc.apply(root, "task-1", {"action": "pause", "actor": "owner", "expected_revision": bad, "operation_id": "bad"})


@pytest.mark.parametrize("ident", ["../escape", "/absolute", "a/b", "汉字", "a" * 81, ".", "a.json", "a\\b", ""])
def test_id_safety(root, ident):
    configure(root)
    with pytest.raises(ValueError):
        register(root, ident)


def test_unknown_keys_and_invalid_types(root):
    running(root)
    with pytest.raises(ValueError, match="keys"):
        op(root, "pause", surprise=True)
    for field, value in [("actor", []), ("operation_id", True), ("action", [])]:
        data = {"action": "pause", "actor": "owner", "expected_revision": 2, "operation_id": "bad", field: value}
        with pytest.raises(ValueError):
            tc.apply(root, "task-1", data)
    with pytest.raises(ValueError):
        op(root, "progress", actor="worker", attempt_id="attempt-1", evidence_refs=[])


def test_cas_identity_replay_even_after_intervening_ops(root):
    configure(root)
    first = register(root)
    payload = deepcopy(tc.show(root, "task-1")["events"][0]["payload"])
    op(root, "takeover", executor="worker", attempt_id="attempt-1")
    before = snapshot(root)
    assert tc.apply(root, "task-1", payload) == first
    assert snapshot(root) == before
    changed = {**payload, "actor": "other"}
    with pytest.raises(ValueError, match="conflict"):
        tc.apply(root, "task-1", changed)
    with pytest.raises(ValueError, match="CAS"):
        tc.apply(root, "task-1", {"action": "pause", "actor": "owner", "operation_id": "stale", "expected_revision": 1})
    with pytest.raises(ValueError, match="Owner"):
        op(root, "takeover", actor="worker", executor="worker", attempt_id="attempt-2")
    assert snapshot(root) == before


def test_old_attempt_fenced_and_attempt_ids_never_reused(root):
    running(root)
    op(root, "takeover", executor="next", attempt_id="attempt-2")
    task = tc.show(root, "task-1")
    assert task["attempts"][0]["status"] == "replaced"
    for actor, attempt in [("worker", "attempt-1"), ("next", "attempt-1"), ("worker", "attempt-2")]:
        with pytest.raises(ValueError, match="fence"):
            op(root, "complete", actor=actor, attempt_id=attempt, evidence_refs=[ref(root, "artifact.bin")])
    with pytest.raises(ValueError, match="reused"):
        op(root, "takeover", executor="next", attempt_id="attempt-1")


def test_explicit_task_key_no_goal_dedup_or_session_completion(root):
    configure(root)
    register(root)
    register(root, "task-2")
    (root / "SESSION.md").write_text("session ended\n")
    assert len(tc.collect(root)["tasks"]) == 2
    assert all(t["status"] == "ready" and t["active_attempt"] is None for t in tc.collect(root)["tasks"])
    with pytest.raises(ValueError, match="registered"):
        tc.apply(root, "unregistered", {"action": "pause", "actor": "owner", "expected_revision": 0, "operation_id": "unknown"})


def test_wait_pause_resume_recheck_are_explicit_and_read_stable(root):
    running(root)
    waiting = {"condition": "artifact inspected", "trigger": "new local evidence", "evidence_ref": ref(root, "evidence.md")}
    op(root, "wait", actor="worker", attempt_id="attempt-1", waiting=waiting)
    before = snapshot(root)
    for _ in range(3):
        task = tc.show(root, "task-1")
        assert task["status"] == "waiting" and task["waiting"] == waiting and task["active_attempt"] is None
        tc.collect(root)
        notice = tc.render_notice(root)
        assert all(x in notice for x in ["task-1", "revision=3", "status=waiting", "host-asserted", "local_artifacts", "artifact inspected"])
    assert snapshot(root) == before
    op(root, "pause")
    op(root, "resume")
    assert tc.show(root, "task-1")["status"] == "waiting"
    op(root, "recheck", evidence_refs=[ref(root, "artifact.bin")])
    assert tc.show(root, "task-1")["status"] == "ready"
    assert tc.show(root, "task-1")["active_attempt"] is None


def test_followup_is_source_of_facts_not_rewritten(root):
    folder = root / ".flg/captures"
    folder.mkdir()
    path = folder / "cap-dependency.md"
    path.write_text("---\nid: cap-dependency\nstatus: pending_review\nclaim: Check input\n---\n\nOriginal body\n")
    def disposition(state):
        data = {"schema_version": 1, "disposition": state, "reason": "local explicit review",
                "waiting_for": ["proof"], "review_trigger": "proof arrives",
                "refs": [{**ref(root, "evidence.md"), "quote": "Local inspection result."}]}
        capture_followup.record(root, "cap-dependency", data, digest(path.read_bytes()))
    disposition("awaiting_evidence")
    running(root)
    op(root, "wait", actor="worker", attempt_id="attempt-1", followup_id="cap-dependency")
    raw = path.read_bytes()
    with pytest.raises(ValueError, match="Unresolved followup"):
        op(root, "recheck", evidence_refs=[ref(root, "artifact.bin")])
    op(root, "pause")
    op(root, "resume")
    assert tc.show(root, "task-1")["status"] == "waiting" and path.read_bytes() == raw
    disposition("absorbed")
    raw = path.read_bytes()
    assert tc.show(root, "task-1")["status"] == "waiting"
    op(root, "recheck", evidence_refs=[ref(root, "artifact.bin")])
    assert tc.show(root, "task-1")["status"] == "ready" and path.read_bytes() == raw


@pytest.mark.parametrize("action", ["progress", "complete", "takeover"])
def test_source_drift_blocks_but_allows_pause_cancel(root, action):
    running(root)
    (root / "goal.md").write_text("Changed goal\n")
    before = snapshot(root)
    task = tc.show(root, "task-1")
    assert task["status"] == "running" and task["needs_recheck"] and task["issues"]
    extra = {"executor": "new", "attempt_id": "new"} if action == "takeover" else {
        "actor": "worker", "attempt_id": "attempt-1", "evidence_refs": [ref(root, "artifact.bin")]}
    with pytest.raises(ValueError, match="drift"):
        op(root, action, **extra)
    assert snapshot(root) == before
    op(root, "pause")
    with pytest.raises(ValueError, match="drift"):
        op(root, "resume")
    op(root, "cancel")


def test_drift_blocks_recheck_and_quote_scope_ignores_unrelated_edits(root):
    configure(root)
    register(root, goal_ref=ref(root, quote="User: keep the goal."),
             acceptance_ref=ref(root, "accept.md", "User: deliver artifact.bin."))
    (root / "goal.md").write_text("User: keep the goal.\nUnrelated edit.\n")
    assert not tc.show(root, "task-1")["needs_recheck"]
    op(root, "takeover", executor="worker", attempt_id="attempt-1")
    op(root, "wait", actor="worker", attempt_id="attempt-1",
       waiting={"condition": "wait", "trigger": "proof", "evidence_ref": ref(root, "evidence.md")})
    (root / "goal.md").write_text("User: keep the goal.\nUser: keep the goal.\n")
    with pytest.raises(ValueError, match="unique"):
        op(root, "recheck", evidence_refs=[ref(root, "artifact.bin")])


def test_rebind_no_scope_or_criteria_weakening_and_history_immutable(root):
    running(root)
    old = tc.show(root, "task-1")["events"]
    with pytest.raises(ValueError, match="keys"):
        op(root, "rebind", goal_ref=ref(root), acceptance_ref=ref(root, "accept.md"), criteria=[])
    with pytest.raises(ValueError, match="path and quote"):
        op(root, "rebind", goal_ref=ref(root, "accept.md"), acceptance_ref=ref(root, "accept.md"))
    with pytest.raises(ValueError, match="permission"):
        op(root, "rebind", goal_ref=ref(root), acceptance_ref=ref(root, "accept.md"), action_ref=ref(root))
    op(root, "rebind", goal_ref=ref(root), acceptance_ref=ref(root, "accept.md"))
    task = tc.show(root, "task-1")
    assert task["status"] == "blocked" and task["active_attempt"] is None and task["events"][:2] == old
    op(root, "recheck", evidence_refs=[ref(root, "artifact.bin")])
    (root / "accept.md").write_text("Weakened criteria.\n")
    with pytest.raises(ValueError, match="new task"):
        op(root, "rebind", goal_ref=ref(root), acceptance_ref=ref(root, "accept.md"))


@pytest.mark.parametrize("kind", ["missing", "stale", "quote", "wrong_path"])
def test_completion_requires_every_exact_artifact(root, kind):
    running(root)
    evidence = ref(root, "artifact.bin")
    if kind == "missing":
        (root / "artifact.bin").unlink()
    elif kind == "stale":
        (root / "artifact.bin").write_bytes(b"new bytes")
    elif kind == "quote":
        evidence = ref(root, "artifact.bin", "exact output")
    else:
        evidence = ref(root, "evidence.md")
    with pytest.raises((ValueError, OSError)):
        op(root, "complete", actor="worker", attempt_id="attempt-1", evidence_refs=[evidence])
    assert tc.show(root, "task-1")["status"] == "running"


@pytest.mark.parametrize("path", ["../outside", "/tmp/outside", "a\\b", ".flg/state.json", "https://example.com/file"])
def test_criteria_paths_and_formal_effects_rejected(root, path):
    configure(root)
    with pytest.raises(ValueError):
        register(root, criteria=[{"id": "a", "path": path}])
    with pytest.raises(ValueError, match="formal approval"):
        register(root, criteria=[{"id": "approve", "path": "artifact.bin", "formal_approval": True}])


@pytest.mark.parametrize("target", [".flg", ".flg/tasks", ".flg/tasks/task-1.json", ".flg/task-continuity.json", "goal.md"])
def test_symlink_fail_closed_display_and_mutation(root, tmp_path_factory, target):
    running(root)
    path = root / target
    destination = tmp_path_factory.mktemp("symlink") / "original"
    path.rename(destination)
    path.symlink_to(destination, target_is_directory=destination.is_dir())
    report = tc.collect(root)
    assert report["enabled"] is True and report["issues"]
    assert "needs_recheck" in tc.render_notice(root)
    with pytest.raises(ValueError, match="Symlinked"):
        tc.apply(root, "task-1", {"action": "pause", "actor": "owner", "expected_revision": 2, "operation_id": "pause"})


@pytest.mark.parametrize("target,content", [(".flg/task-continuity.json", "{}"),
                                            (".flg/task-continuity.json", '{"schema_version":99}'),
                                            (".flg/tasks/task-1.json", "not json"),
                                            (".flg/tasks/task-1.json", '{"schema_version":99}')])
def test_corruption_visible_without_crashing_unrelated_views(root, target, content):
    running(root)
    (root / target).write_text(content)
    before = snapshot(root)
    report = tc.collect(root)
    assert report["enabled"] is True and report["issues"] and report["needs_recheck"]
    task = tc.show(root, "task-1")
    assert task["needs_recheck"] and task["checks"]["executable"] is False
    assert "needs_recheck" in tc.render_notice(root)
    assert snapshot(root) == before
    with pytest.raises(ValueError):
        op(root, "pause")


def test_absent_config_keeps_unrelated_legacy_store_disabled(root):
    running(root)
    (root / tc.CONFIG).unlink()
    (root / ".flg/tasks/legacy.txt").write_text("Unrelated legacy contents")
    before = snapshot(root)
    assert tc.collect(root) == {"enabled": False, "tasks": [], "issues": []}
    assert tc.render_notice(root) == ""
    assert snapshot(root) == before
    with pytest.raises(ValueError, match="migration"):
        configure(root)


def test_atomic_failure_preserves_task_and_retry_succeeds(root, monkeypatch):
    running(root)
    before = snapshot(root)
    original = tc.atomic_write_text
    def fail(path, content):
        raise OSError("synthetic atomic replace failure")
    monkeypatch.setattr(tc, "atomic_write_text", fail)
    with pytest.raises(OSError, match="synthetic"):
        op(root, "pause")
    assert snapshot(root) == before and not (root / ".flg/.operation.lock").exists()
    monkeypatch.setattr(tc, "atomic_write_text", original)
    op(root, "pause")
    assert tc.show(root, "task-1")["revision"] == 3


def test_interrupt_requires_owner_and_attempt_then_explicit_recheck(root):
    running(root)
    with pytest.raises(ValueError):
        op(root, "interrupt", actor="worker", attempt_id="attempt-1")
    op(root, "interrupt", attempt_id="attempt-1")
    assert tc.show(root, "task-1")["status"] == "blocked"
    op(root, "recheck", evidence_refs=[ref(root, "evidence.md")])
    assert tc.show(root, "task-1")["active_attempt"] is None


@pytest.mark.parametrize("action", ["progress", "recheck", "complete"])
def test_explicit_evidence_refresh_allows_artifact_iteration(root, action):
    running(root)
    op(root, "progress", actor="worker", attempt_id="attempt-1", evidence_refs=[ref(root, "artifact.bin")])
    if action == "recheck":
        op(root, "interrupt", attempt_id="attempt-1")
    original = tc.show(root, "task-1")["events"]
    old_ref = ref(root, "artifact.bin")
    (root / "artifact.bin").write_bytes(b"revised draft version B")
    assert tc.show(root, "task-1")["needs_recheck"]
    extra = {} if action == "recheck" else {"actor": "worker", "attempt_id": "attempt-1"}
    # Unrelated observations must not silently clear old drift.
    with pytest.raises(ValueError, match="drift"):
        op(root, action, evidence_refs=[ref(root, "evidence.md")], **extra)
    result = op(root, action, evidence_refs=[ref(root, "artifact.bin")], **extra)
    task = tc.show(root, "task-1")
    assert not task["needs_recheck"]
    assert task["events"][:len(original)] == original
    assert task["events"][2]["payload"]["evidence_refs"] == [old_ref]
    assert task["evidence_refs"] == [ref(root, "artifact.bin")]
    assert result["status"] == {"progress": "running", "recheck": "ready", "complete": "completed"}[action]


def test_evidence_refresh_cannot_implicitly_refresh_goal_or_wait(root):
    running(root)
    old_goal = ref(root)
    (root / "goal.md").write_text("Changed authoritative goal")
    with pytest.raises(ValueError, match="drift"):
        op(root, "progress", actor="worker", attempt_id="attempt-1", evidence_refs=[ref(root)])
    assert tc.show(root, "task-1")["goal_ref"] == old_goal


def test_timestamps_and_replay_are_immutable(root):
    running(root)
    task = tc.show(root, "task-1")
    event = deepcopy(task["events"][-1])
    receipt = deepcopy(task["operations"][event["operation_id"]]["result"])
    assert datetime.fromisoformat(event["recorded_at"]).utcoffset() is not None
    op(root, "pause")
    before = snapshot(root)
    assert tc.apply(root, "task-1", event["payload"]) == receipt
    assert snapshot(root) == before
    task = tc.show(root, "task-1")
    assert task["events"][1] == event
    attempt = task["attempts"][0]
    assert datetime.fromisoformat(attempt["ended_at"]) >= datetime.fromisoformat(attempt["started_at"])


def test_configure_rechecks_request_inside_lock(root, monkeypatch):
    from contextlib import contextmanager
    real_lock = tc.project_operation_lock
    @contextmanager
    def lock(root):
        with real_lock(root):
            (root / "request.md").write_text("authorization changed before lock acquisition")
            yield
    monkeypatch.setattr(tc, "project_operation_lock", lock)
    with pytest.raises(ValueError, match="drift"):
        configure(root)
    assert not (root / tc.CONFIG).exists()


def test_notice_budget_and_omitted_counts(root):
    configure(root)
    for number in range(8):
        register(root, f"task-{number}")
    (root / "goal.md").write_text("Drift makes every task need recheck")
    before = snapshot(root)
    notice = tc.render_notice(root)
    assert notice.endswith("\n\n")
    assert "4 tasks omitted" in notice and "5 issues omitted" in notice
    assert "flg task list / flg task show" in notice
    assert len(notice) <= 4 * 321 + 3 * 241 + 300
    assert snapshot(root) == before


def test_real_atomic_replace_failure_no_partial_record(root, monkeypatch):
    from flg.core import operations
    running(root)
    before = snapshot(root)
    def fail(source, target):
        raise OSError("replace failed")
    monkeypatch.setattr(operations.os, "replace", fail)
    with pytest.raises(OSError, match="replace failed"):
        op(root, "pause")
    assert snapshot(root) == before
    assert sorted(p.name for p in (root / ".flg/tasks").iterdir()) == ["task-1.json"]


def test_disabled_corruption_not_hidden_and_config_failure_no_optin(root, monkeypatch):
    configure(root)
    register(root)
    op(root, "cancel")
    configure(root, False)
    (root / ".flg/tasks/task-1.json").write_text("corrupt")
    assert tc.collect(root)["enabled"] is True and tc.collect(root)["issues"]


def test_task_count_bound_does_not_commit_inaccessible_task(root, monkeypatch):
    configure(root)
    monkeypatch.setattr(tc, "MAX_TASKS", 2)
    register(root)
    register(root, "task-2")
    with pytest.raises(ValueError, match="limit"):
        register(root, "task-3")
    assert not (root / ".flg/tasks/task-3.json").exists()
    assert len(tc.collect(root)["tasks"]) == 2


def reviewed_followup(root, state):
    folder = root / ".flg/captures"
    folder.mkdir(exist_ok=True)
    path = folder / "cap-source.md"
    if not path.exists():
        path.write_text("---\nid: cap-source\nstatus: pending_review\nclaim: Dependency\n---\n\nSource body\n")
    capture_followup.record(root, "cap-source", {
        "schema_version": 1, "disposition": state, "reason": "explicit local review",
        "waiting_for": ["new material"], "review_trigger": "material arrives",
        "refs": [{**ref(root, "artifact.bin"), "quote": "exact output"}]}, digest(path.read_bytes()))
    return path


def test_closed_followup_never_hides_independent_local_wait(root):
    followup = reviewed_followup(root, "absorbed")
    followup_bytes = followup.read_bytes()
    configure(root)
    register(root, followup_id="cap-source")
    op(root, "takeover", executor="worker", attempt_id="a1")
    op(root, "wait", actor="worker", attempt_id="a1", waiting={
        "condition": "independent inspection", "trigger": "inspection result", "evidence_ref": ref(root, "evidence.md")})
    op(root, "pause")
    op(root, "resume")
    task = tc.show(root, "task-1")
    assert task["status"] == "waiting" and task["waiting"] is not None
    with pytest.raises(ValueError, match="ready/running"):
        op(root, "takeover", executor="worker", attempt_id="a2")
    with pytest.raises(ValueError, match="Running"):
        op(root, "complete", actor="worker", attempt_id="a1", evidence_refs=[ref(root, "artifact.bin")])
    op(root, "recheck", evidence_refs=[ref(root, "evidence.md")])
    assert tc.show(root, "task-1")["status"] == "ready"
    assert followup.read_bytes() == followup_bytes


@pytest.mark.parametrize("followup_state", [None, "awaiting_evidence", "absorbed"])
def test_explicit_same_path_wait_observation_refresh(root, followup_state):
    followup = reviewed_followup(root, "absorbed") if followup_state else None
    configure(root)
    register(root, **({"followup_id": "cap-source"} if followup else {}))
    op(root, "takeover", executor="worker", attempt_id="a1")
    old_wait = {"condition": "input checked", "trigger": "new input revision", "evidence_ref": ref(root, "evidence.md")}
    op(root, "wait", actor="worker", attempt_id="a1", waiting=old_wait)
    if followup_state == "awaiting_evidence":
        reviewed_followup(root, "awaiting_evidence")
    followup_bytes = followup.read_bytes() if followup else None
    history = tc.show(root, "task-1")["events"]
    (root / "evidence.md").write_text("new input revision B")
    assert tc.show(root, "task-1")["needs_recheck"]
    with pytest.raises(ValueError, match="drift"):
        op(root, "recheck", evidence_refs=[ref(root, "artifact.bin")])
    if followup_state == "awaiting_evidence":
        with pytest.raises(ValueError, match="Unresolved followup"):
            op(root, "recheck", evidence_refs=[ref(root, "evidence.md")])
        assert tc.show(root, "task-1")["waiting"] == old_wait
    else:
        op(root, "recheck", evidence_refs=[ref(root, "evidence.md")])
        task = tc.show(root, "task-1")
        assert task["status"] == "ready" and task["waiting"] is None
        assert task["events"][:len(history)] == history
        assert task["events"][2]["payload"]["waiting"] == old_wait
    if followup:
        assert followup.read_bytes() == followup_bytes


def test_registration_open_followup_stays_waiting_until_owner_recheck(root):
    reviewed_followup(root, "awaiting_evidence")
    configure(root)
    register(root, followup_id="cap-source")
    assert tc.show(root, "task-1")["status"] == "waiting"
    with pytest.raises(ValueError, match="ready/running"):
        op(root, "takeover", executor="worker", attempt_id="a1")
    reviewed_followup(root, "absorbed")
    assert tc.show(root, "task-1")["status"] == "waiting"
    op(root, "recheck", evidence_refs=[ref(root, "evidence.md")])
    op(root, "takeover", executor="worker", attempt_id="a1")
    assert tc.show(root, "task-1")["status"] == "running"


def test_ready_task_with_reopened_followup_never_advertises_executor_work(root):
    reviewed_followup(root, "absorbed")
    configure(root)
    register(root, followup_id="cap-source")
    reviewed_followup(root, "awaiting_evidence")
    before = snapshot(root)
    task = tc.show(root, "task-1")
    assert task["status"] == "ready" and task["needs_recheck"]
    assert "recheck" in task["next_safe_action"] and "owner takeover" not in task["next_safe_action"]
    with pytest.raises(ValueError, match="Unresolved"):
        op(root, "takeover", executor="worker", attempt_id="a1")
    assert snapshot(root) == before
    op(root, "pause")
    op(root, "resume")
    assert tc.show(root, "task-1")["status"] == "waiting"
    op(root, "cancel")


def test_notice_prioritizes_active_tasks_over_sorted_terminal_history(root):
    configure(root)
    for index in range(5):
        task_id = f"history-{index}"
        register(root, task_id)
        op(root, "cancel", task_id=task_id)
    assert "No active tasks; 5 historical tasks" in tc.render_notice(root)
    register(root, "zzz-active")
    notice = tc.render_notice(root)
    assert "zzz-active" in notice and "5 historical tasks omitted" in notice
    assert len(tc.collect(root)["tasks"]) == 6


@pytest.mark.parametrize("reader", ["collect", "render_notice"])
@pytest.mark.parametrize("boundary", ["after_ids", "after_first_show"])
@pytest.mark.parametrize("change", ["disable", "disable_enable", "corrupt_config", "corrupt_task"])
def test_collect_config_race_is_read_only_and_fail_closed(root, monkeypatch, reader, boundary, change):
    configure(root)
    for ident in ("task-1", "task-2"):
        register(root, ident)
        op(root, "cancel", task_id=ident)
    original = tc._task_ids if boundary == "after_ids" else tc.show
    after_change = None
    changed = False

    def interleaved_read(*args):
        nonlocal after_change, changed
        result = original(*args)
        if not changed:
            # Deterministic scheduling at a read boundary, without sleeps.
            # These config transitions use the same API as another process.
            changed = True
            if change in {"disable", "disable_enable"}:
                configure(root, False)
                if change == "disable_enable":
                    configure(root, True)
            else:
                target = tc.CONFIG if change == "corrupt_config" else ".flg/tasks/task-2.json"
                (root / target).write_text("corrupt")
            after_change = snapshot(root)
        return result

    monkeypatch.setattr(tc, "_task_ids" if boundary == "after_ids" else "show", interleaved_read)
    result = getattr(tc, reader)(root)
    assert changed and snapshot(root) == after_change
    assert not (root / ".flg/.operation.lock").exists()
    if reader == "collect":
        assert result["enabled"] is True and result["needs_recheck"] and result["issues"]
        if change != "corrupt_task":
            assert result["tasks"] == []  # Never expose a mixed-config partial list.
        else:
            corrupt = next(task for task in result["tasks"] if task["task_id"] == "task-2")
            assert corrupt["status"] == "unknown" and corrupt["checks"]["executable"] is False
    else:
        assert "needs_recheck" in result and "No active tasks" not in result


@pytest.mark.parametrize("path", [".flg", ".FLG", ".flg/state.json", ".FLG/state.json",
                                 ".FlG/state.json", ".fLg/tasks/task-1.json", ".flG/nested/output.bin",
                                 ".flg.", ".flg ", ".FLG. /state.json", ".flg./state.json",
                                 ".flg /state.json", ".FlG...   /nested/output.bin"])
def test_internal_artifact_paths_rejected_on_every_filesystem(root, path):
    configure(root)
    before = snapshot(root)
    # No existence check or case-insensitive-filesystem skip: this is a
    # portable namespace rule even when the differently cased path is absent.
    with pytest.raises(ValueError, match="Internal task/ledger"):
        register(root, criteria=[{"id": "internal", "path": path}])
    assert snapshot(root) == before


@pytest.mark.parametrize("path", [".flg-output.bin", "outputs/.FLG/artifact.bin"])
def test_internal_artifact_rule_does_not_reserve_unrelated_paths(root, path):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"local deliverable")
    configure(root)
    register(root, criteria=[{"id": "artifact", "path": path}])
    op(root, "takeover", executor="worker", attempt_id="attempt-1")
    result = op(root, "complete", actor="worker", attempt_id="attempt-1", evidence_refs=[ref(root, path)])
    assert result["status"] == "completed"


def test_unconfigured_root_alias_is_read_only_and_notice_free(tmp_path, monkeypatch):
    from typer.testing import CliRunner
    from flg.cli import app
    from flg.commands.context import build_context_pack
    from flg.commands.handoff import generate_handoff_summary

    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    assert CliRunner().invoke(app, ["init", "Synthetic legacy project"]).exit_code == 0
    alias = tmp_path / "project-alias"
    alias.symlink_to(project, target_is_directory=True)
    # An unrelated legacy task folder must stay outside this opt-in feature.
    (project / ".flg/tasks").mkdir()
    (project / ".flg/tasks/legacy.txt").write_text("unrelated legacy data")
    before = snapshot(project)
    directory_times = {p: p.stat().st_mtime_ns for p in [project, *project.rglob("*")] if p.is_dir()}
    alias_time = alias.lstat().st_mtime_ns

    for path in (project, alias):
        assert tc.collect(path) == {"enabled": False, "tasks": [], "issues": []}
        assert tc.show(path, "task-1") == {
            "enabled": False, "task_id": "task-1", "issues": [], "checks": {"executable": False}}
        assert tc.render_notice(path) == ""
        content, metadata = build_context_pack(path, mode="manifest")
        assert "Task continuity" not in content
        assert ".flg/tasks/" not in metadata["sources_included"]
        assert "Task continuity" not in generate_handoff_summary(path)
    assert snapshot(project) == before
    assert {p: p.stat().st_mtime_ns for p in directory_times} == directory_times
    assert alias.lstat().st_mtime_ns == alias_time


def test_root_alias_reads_match_but_writes_remain_rejected(root, tmp_path_factory):
    running(root)
    alias = tmp_path_factory.mktemp("root-alias") / "project"
    alias.symlink_to(root, target_is_directory=True)
    before = snapshot(root)
    assert tc.show(alias, "task-1") == tc.show(root, "task-1")
    assert tc.collect(alias) == tc.collect(root)
    assert tc.render_notice(alias) == tc.render_notice(root)
    with pytest.raises(ValueError, match="Symlinked project roots"):
        configure(alias)
    with pytest.raises(ValueError, match="Symlinked project roots"):
        tc.apply(alias, "task-1", {"action": "pause", "actor": "owner", "expected_revision": 2,
                                  "operation_id": "alias-write"})
    assert snapshot(root) == before


@pytest.mark.parametrize("target", [".flg", ".flg/tasks", ".flg/task-continuity.json",
                                   ".flg/tasks/task-1.json", "goal.md", "artifact.bin"])
def test_root_alias_does_not_allow_symlinked_subpaths(root, tmp_path_factory, target):
    running(root)
    outside = tmp_path_factory.mktemp("alias-boundary")
    alias = outside / "project"
    alias.symlink_to(root, target_is_directory=True)
    path = root / target
    destination = outside / "retained"
    path.rename(destination)
    path.symlink_to(destination, target_is_directory=destination.is_dir())
    for report in (tc.collect(alias), tc.show(alias, "task-1")):
        assert report["enabled"] is True and report["needs_recheck"] and report["issues"]
        assert "Symlinked source/state paths" in str(report["issues"])
    assert tc.show(alias, "task-1")["checks"]["executable"] is False
    assert "needs_recheck" in tc.render_notice(alias)


@pytest.mark.parametrize("kind", ["missing", "loop"])
def test_unresolvable_root_alias_is_fail_closed(tmp_path, kind):
    alias = tmp_path / "alias"
    alias.symlink_to(tmp_path / "missing" if kind == "missing" else alias)
    before = alias.lstat().st_mtime_ns
    for report in (tc.collect(alias), tc.show(alias, "task-1")):
        assert report["enabled"] is True and report["needs_recheck"] and report["issues"]
    assert "needs_recheck" in tc.render_notice(alias)
    assert list(tmp_path.iterdir()) == [alias] and alias.lstat().st_mtime_ns == before
