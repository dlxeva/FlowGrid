"""Opt-in, local-artifact task continuation. Actors are host assertions only.

Reading never grants execution or approval authority. All supported task writes
serialize through the project lock and atomically replace one task record.
Writers outside this API, distributed leases and semantic approval are out of
scope. No referenced file, followup, session or formal ledger is ever written.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from . import capture_followup
from .operations import atomic_write_text, project_operation_lock
from .source_receipts import (checked_path, digest, nonempty, parse_json,
                              read_bytes, relative, require, valid_hash)

CONFIG = ".flg/task-continuity.json"
STATES = {"ready", "running", "waiting", "blocked", "paused", "completed", "cancelled"}
TERMINAL = {"completed", "cancelled"}
MAX_BYTES = 2 * 1024 * 1024
MAX_TASKS = 100
MAX_OPERATIONS = 1000
ERRORS = (ValueError, OSError, UnicodeError, TypeError, KeyError)
COMMON = {"action", "expected_revision", "operation_id", "actor"}
FIELDS = {
    "register": {"owner", "goal_ref", "acceptance_ref", "criteria", "followup_id", "action_ref"},
    "takeover": {"executor", "attempt_id"},
    "progress": {"attempt_id", "evidence_refs"},
    "wait": {"attempt_id", "followup_id", "waiting"},
    "recheck": {"evidence_refs"},
    "pause": set(), "cancel": set(), "resume": set(),
    "rebind": {"goal_ref", "acceptance_ref", "action_ref"},
    "complete": {"attempt_id", "evidence_refs"},
    "interrupt": {"attempt_id"},
}


def _id(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", value),
            "Invalid task/operation/attempt ID (ASCII, max 80)")
    return value


def _text(value):
    require(nonempty(value) and len(value) <= 500, "Expected bounded nonempty text")
    return value


def _now():
    return datetime.now(timezone.utc).isoformat()


def _timestamp(value):
    require(isinstance(value, str), "Expected timezone-aware audit timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Expected timezone-aware audit timestamp") from exc
    require(parsed.utcoffset() is not None, "Expected timezone-aware audit timestamp")


def _load(root, path):
    target = checked_path(root, path)
    require(target.stat().st_size <= MAX_BYTES, "Task/config exceeds size limit")
    raw = read_bytes(root, path)
    require(len(raw) <= MAX_BYTES, "Task/config exceeds size limit")
    return parse_json(raw)


def _save(root, path, data):
    content = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    require(len(content.encode("utf-8")) <= MAX_BYTES, "Task/config exceeds size limit")
    atomic_write_text(checked_path(root, path), content)


def _ref_shape(root, ref):
    require(isinstance(ref, dict) and set(ref) in ({"path", "sha256"}, {"path", "sha256", "quote"}),
            "Reference requires path/sha256 and optional quote only")
    checked_path(root, ref["path"])
    require(valid_hash(ref["sha256"]), "Reference SHA-256 required")
    if "quote" in ref:
        require(nonempty(ref["quote"]) and len(ref["quote"].encode("utf-8")) <= 32000,
                "Expected bounded nonempty exact quote")


def _check_ref(root, ref):
    _ref_shape(root, ref)
    raw = read_bytes(root, ref["path"])
    if "quote" in ref:
        text, quote = raw.decode("utf-8"), ref["quote"]
        start = text.find(quote)
        require(start >= 0 and text.find(quote, start + 1) < 0, "Reference quote missing or not unique")
        raw = quote.encode("utf-8")
    require(digest(raw) == ref["sha256"], "Reference hash drift: explicit source review/rebind required")


def _refs(root, refs, *, fresh=False, nonempty_list=False):
    require(isinstance(refs, list) and len(refs) <= 50 and (refs or not nonempty_list),
            "evidence_refs must be a bounded nonempty list")
    for ref in refs:
        (_check_ref if fresh else _ref_shape)(root, ref)


def _config(root):
    path = checked_path(root, CONFIG)
    if not path.exists():
        # Existing projects may use .flg/tasks for unrelated legacy data.
        # Manual deletion of the config is outside this API's guarantees.
        return {"enabled": False}
    data = _load(root, CONFIG)
    require(set(data) == {"schema_version", "enabled", "actor", "request_ref", "history"}, "Invalid config schema")
    require(type(data["schema_version"]) is int and data["schema_version"] == 1, "Unsupported config schema")
    require(type(data["enabled"]) is bool, "enabled must be bool")
    _text(data["actor"])
    _ref_shape(root, data["request_ref"])
    require(isinstance(data["history"], list) and 1 <= len(data["history"]) <= MAX_OPERATIONS,
            "Invalid configuration history")
    for event in data["history"]:
        require(isinstance(event, dict) and set(event) == {"enabled", "actor", "request_ref"}
                and type(event["enabled"]) is bool, "Invalid configuration event")
        _text(event["actor"])
        _ref_shape(root, event["request_ref"])
    require(data["history"][-1] == {k: data[k] for k in ("enabled", "actor", "request_ref")},
            "Config/history mismatch")
    if not data["enabled"]:
        for ident in _task_ids(root):
            task = _read_task(root, ident)
            require(task["status"] in TERMINAL, "Disabled config contains unresolved work")
    return data


def _criteria(root, criteria):
    require(isinstance(criteria, list) and 1 <= len(criteria) <= 50, "Nonempty local-artifact criteria required")
    ids, paths = set(), set()
    for criterion in criteria:
        require(isinstance(criterion, dict) and set(criterion) == {"id", "path"},
                "Only local artifact id/path criteria supported; no formal approval or remote effects")
        ident = _id(criterion["id"])
        path = relative(criterion["path"])
        checked_path(root, path)
        # Reserve the namespace on every platform, including case aliases and
        # Win32's trailing-dot/space aliases; none may certify ledger state.
        require(path.split("/", 1)[0].rstrip(" .").casefold() != ".flg",
                "Internal task/ledger paths cannot be completion artifacts")
        require(ident not in ids and path not in paths, "Duplicate criterion ID/path")
        ids.add(ident)
        paths.add(path)


def _task_path(ident):
    return f".flg/tasks/{_id(ident)}.json"


def _validate(root, data, ident):
    require(set(data) == {"schema_version", "task_id", "status", "revision", "owner", "goal_ref",
                         "acceptance_ref", "action_ref", "criteria", "followup_id", "waiting",
                         "evidence_refs", "active_attempt", "attempts", "events", "operations",
                         "completion_scope"}, "Invalid task record schema")
    require(type(data["schema_version"]) is int and data["schema_version"] == 1, "Unsupported task schema")
    require(data["task_id"] == ident and isinstance(data["status"], str) and data["status"] in STATES,
            "Invalid task ID/status")
    revision = data["revision"]
    require(type(revision) is int and 1 <= revision <= MAX_OPERATIONS, "Invalid revision")
    _text(data["owner"])
    for key in ("goal_ref", "acceptance_ref"):
        _ref_shape(root, data[key])
    if data["action_ref"] is not None:
        _ref_shape(root, data["action_ref"])
    _criteria(root, data["criteria"])
    _refs(root, data["evidence_refs"])
    if data["followup_id"] is not None:
        capture_followup._id(data["followup_id"])
    if data["waiting"] is not None:
        _waiting_shape(root, data["waiting"])
    require(isinstance(data["attempts"], list) and len(data["attempts"]) <= revision, "Invalid attempts")
    seen = set()
    running = []
    for attempt in data["attempts"]:
        require(isinstance(attempt, dict) and set(attempt) == {"attempt_id", "executor", "status", "started_at", "ended_at"}, "Invalid attempt")
        aid = _id(attempt["attempt_id"])
        _text(attempt["executor"])
        require(aid not in seen and attempt["status"] in {"running", "ended", "replaced"}, "Invalid attempt history")
        _timestamp(attempt["started_at"])
        if attempt["status"] == "running":
            require(attempt["ended_at"] is None, "Running attempt cannot have ended_at")
        else:
            _timestamp(attempt["ended_at"])
            require(datetime.fromisoformat(attempt["ended_at"]) >= datetime.fromisoformat(attempt["started_at"]),
                    "Attempt ended before it started")
        seen.add(aid)
        if attempt["status"] == "running":
            running.append(attempt)
    require((data["status"] == "running") == bool(running) and len(running) <= 1
            and data["active_attempt"] == (running[0] if running else None), "Invalid active attempt")
    require(data["completion_scope"] == ("local_artifacts" if data["status"] == "completed" else None),
            "Invalid completion scope")
    require(isinstance(data["events"], list) and isinstance(data["operations"], dict)
            and len(data["events"]) == len(data["operations"]) == revision, "Invalid event/receipt history")
    for index, event in enumerate(data["events"], 1):
        require(isinstance(event, dict) and set(event) == {"revision", "operation_id", "payload", "status", "recorded_at"}
                and type(event["revision"]) is int and event["revision"] == index,
                "Invalid event revision")
        _timestamp(event["recorded_at"])
        op = _id(event["operation_id"])
        _request(event["payload"])
        require(event["payload"]["operation_id"] == op and event["payload"]["expected_revision"] == index - 1,
                "Event identity mismatch")
        require(isinstance(event["status"], str) and event["status"] in STATES, "Invalid event status")
        receipt = data["operations"].get(op)
        require(isinstance(receipt, dict) and set(receipt) == {"payload_sha256", "result"}
                and receipt["payload_sha256"] == digest(_canonical(event["payload"]))
                and receipt["result"] == {"task_id": ident, "revision": index, "status": event["status"],
                                         "operation_id": op, "completion_scope": "local_artifacts" if event["status"] == "completed" else None,
                                         "recorded_at": event["recorded_at"]},
                "Invalid operation receipt")
    require(data["events"][-1]["status"] == data["status"], "Event/status mismatch")


def _read_task(root, ident):
    data = _load(root, _task_path(ident))
    _validate(root, data, ident)
    return data


def _waiting_shape(root, waiting):
    require(isinstance(waiting, dict) and set(waiting) == {"condition", "trigger", "evidence_ref"}, "Invalid waiting object")
    _text(waiting["condition"])
    _text(waiting["trigger"])
    _ref_shape(root, waiting["evidence_ref"])


def _followup(root, ident):
    capture_followup._id(ident)
    report = capture_followup.collect(root, capture_id=ident, limit=1)
    # Unrelated corrupt captures must not silently truncate/validate this one.
    require(bool(report["items"]), "Existing followup capture required")
    item = report["items"][0]
    require(not item["errors"] and not item["drifted"] and not item["legacy"],
            "Followup requires explicit valid version-bound review")
    return item


def _wait_open(root, task):
    # A closed followup cannot erase an independent task-local wait.
    local_open = task["waiting"] is not None
    if task["followup_id"] is not None:
        item = _followup(root, task["followup_id"])
        return local_open or item["state"] not in {"absorbed", "expired", "rejected", "confirmed"}
    return local_open


def _followup_open(root, ident):
    return _followup(root, ident)["state"] not in {"absorbed", "expired", "rejected", "confirmed"}


def _fresh(root, task, evidence_refs=None, *, refresh_wait=False):
    for key in ("goal_ref", "acceptance_ref", "action_ref"):
        if task[key] is not None:
            _check_ref(root, task[key])
    # Explicit same-path observations can supersede earlier artifact versions.
    # They never refresh authoritative source bindings or dependency refs.
    replacements = {ref["path"] for ref in evidence_refs or []}
    _refs(root, [ref for ref in task["evidence_refs"] if ref["path"] not in replacements], fresh=True)
    if task["waiting"]:
        waiting_ref = task["waiting"]["evidence_ref"]
        # Only explicit owner recheck may observe a newer dependency version;
        # the wait operation and original binding remain in immutable history.
        if not (refresh_wait and waiting_ref["path"] in replacements):
            _check_ref(root, waiting_ref)
    if task["followup_id"]:
        _followup(root, task["followup_id"])


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _request(payload):
    require(isinstance(payload, dict), "Task payload must be an object")
    action = payload.get("action")
    require(isinstance(action, str) and action in FIELDS, "Unknown task action")
    require(COMMON <= set(payload) <= COMMON | FIELDS[action], "Unknown or missing request keys")
    require(type(payload["expected_revision"]) is int and payload["expected_revision"] >= 0,
            "expected_revision must be a nonnegative integer")
    _id(payload["operation_id"])
    _text(payload["actor"])
    required = {"register": {"owner", "goal_ref", "acceptance_ref", "criteria"},
                "takeover": {"executor", "attempt_id"}, "progress": {"attempt_id", "evidence_refs"},
                "wait": {"attempt_id"}, "recheck": {"evidence_refs"},
                "rebind": {"goal_ref", "acceptance_ref"}, "complete": {"attempt_id", "evidence_refs"},
                "interrupt": {"attempt_id"}}.get(action, set())
    require(required <= set(payload), "Missing action fields")
    if "attempt_id" in payload:
        _id(payload["attempt_id"])
    if "executor" in payload:
        _text(payload["executor"])
    if "followup_id" in payload:
        capture_followup._id(payload["followup_id"])
    _canonical(payload)


def configure(root, payload) -> dict:
    """Explicit opt-in/out; disabling keeps all records and refuses open work."""
    root = Path(root)
    require(isinstance(payload, dict) and set(payload) == {"enabled", "actor", "request_ref"}, "Invalid configure keys")
    require(type(payload["enabled"]) is bool, "enabled must be bool")
    _text(payload["actor"])
    _check_ref(root, payload["request_ref"])
    require(checked_path(root, ".flg").is_dir(), "Existing .flg project directory required")
    checked_path(root, ".flg/.operation.lock")
    with project_operation_lock(root):
        previous = _config(root)
        _check_ref(root, payload["request_ref"])
        if payload["enabled"] and not previous["enabled"]:
            # Do not adopt an unrelated preexisting task store at opt-in.
            folder = checked_path(root, ".flg/tasks")
            require(not folder.exists() or folder.is_dir(), "Task records path must be directory")
            if not previous.get("history"):
                require(not folder.exists() or not any(folder.iterdir()), "Existing task store needs separate local migration")
        if not payload["enabled"]:
            for ident in _task_ids(root):
                task = _read_task(root, ident)
                require(task["status"] in TERMINAL and task["active_attempt"] is None,
                        "Cannot disable with unresolved task work or live attempts")
        history = previous.get("history", []) + [deepcopy(payload)]
        require(len(history) <= MAX_OPERATIONS, "Configuration history limit reached")
        result = {"schema_version": 1, **deepcopy(payload), "history": history}
        _save(root, CONFIG, result)
        return result


def _end(task, status="ended"):
    if task["active_attempt"] is not None:
        task["attempts"][-1]["status"] = status
        task["attempts"][-1]["ended_at"] = _now()
        task["active_attempt"] = None


def _executor(task, payload):
    attempt = task["active_attempt"]
    require(task["status"] == "running" and attempt is not None, "Running task/attempt required")
    require(payload["actor"] == attempt["executor"] and payload["attempt_id"] == attempt["attempt_id"],
            "Executor/attempt fence mismatch")


def apply(root, task_id, payload) -> dict:
    """Sole task mutation API. Exact operation replay precedes revision CAS."""
    root, ident = Path(root), _id(task_id)
    _request(payload)
    # Snapshot caller-owned input before validation and persistence.
    payload = deepcopy(payload)
    require(_config(root)["enabled"], "Task continuity is disabled")
    checked_path(root, ".flg/.operation.lock")
    with project_operation_lock(root):
        require(_config(root)["enabled"], "Task continuity is disabled")
        path = checked_path(root, _task_path(ident))
        task = _read_task(root, ident) if path.exists() else None
        op, action = payload["operation_id"], payload["action"]
        fingerprint = digest(_canonical(payload))
        if task is not None and op in task["operations"]:
            receipt = task["operations"][op]
            require(receipt["payload_sha256"] == fingerprint, "Operation ID payload conflict")
            return deepcopy(receipt["result"])
        require(payload["expected_revision"] == (task["revision"] if task else 0), "Revision CAS mismatch")
        if action == "register":
            require(task is None, "Task already registered; explicit task IDs are never goal-deduped")
            require(len(_task_ids(root)) < MAX_TASKS, "Task store exceeds 100-record stage-1 limit")
            _text(payload["owner"])
            require(payload["actor"] == payload["owner"], "Owner actor required")
            _criteria(root, payload["criteria"])
            for key in ("goal_ref", "acceptance_ref", "action_ref"):
                if key in payload:
                    _check_ref(root, payload[key])
            followup = payload.get("followup_id")
            if "followup_id" in payload:
                _followup(root, followup)
            initial_status = "waiting" if followup and _followup_open(root, followup) else "ready"
            task = {"schema_version": 1, "task_id": ident, "status": initial_status, "revision": 0,
                    "owner": payload["owner"], "goal_ref": payload["goal_ref"], "acceptance_ref": payload["acceptance_ref"],
                    "action_ref": payload.get("action_ref"), "criteria": payload["criteria"], "followup_id": followup,
                    "waiting": None, "evidence_refs": [], "active_attempt": None, "attempts": [],
                    "events": [], "operations": {}, "completion_scope": None}
        else:
            require(task is not None, "Task must be explicitly registered")
            require(task["status"] not in TERMINAL, "Terminal task cannot reopen")
            if action in {"progress", "wait", "complete"}:
                _executor(task, payload)
            else:
                require(payload["actor"] == task["owner"], "Owner actor required")
            evidence = payload.get("evidence_refs") if action in {"progress", "recheck", "complete"} else None
            if evidence is not None:
                _refs(root, evidence, fresh=True, nonempty_list=True)
            if action not in {"pause", "cancel", "rebind", "interrupt"}:
                _fresh(root, task, evidence, refresh_wait=action == "recheck")
            if action == "takeover":
                require(task["status"] in {"ready", "running"}, "Takeover requires ready/running")
                require(not _wait_open(root, task), "Unresolved wait/followup requires owner dependency recheck")
                require(all(x["attempt_id"] != payload["attempt_id"] for x in task["attempts"]), "Attempt ID cannot be reused")
                _end(task, "replaced")
                attempt = {"attempt_id": payload["attempt_id"], "executor": payload["executor"], "status": "running",
                           "started_at": _now(), "ended_at": None}
                task["attempts"].append(attempt)
                task["active_attempt"] = deepcopy(attempt)
                task["status"] = "running"
            elif action in {"progress", "complete", "recheck"}:
                _refs(root, payload["evidence_refs"], fresh=True, nonempty_list=True)
                if action == "complete":
                    require(not _wait_open(root, task), "Unresolved wait/followup blocks completion")
                    coverage = {ref["path"] for ref in payload["evidence_refs"] if "quote" not in ref}
                    require(all(c["path"] in coverage for c in task["criteria"]), "Exact whole-file evidence must cover every criterion")
                    task["status"], task["completion_scope"] = "completed", "local_artifacts"
                    _end(task)
                elif action == "recheck":
                    require(task["status"] in {"waiting", "blocked"}, "Recheck requires waiting/blocked")
                    if task["followup_id"]:
                        require(not _followup_open(root, task["followup_id"]), "Unresolved followup cannot be cleared")
                    task["waiting"] = None
                    task["status"] = "ready"
                    _end(task)
                task["evidence_refs"] = payload["evidence_refs"]
            elif action == "wait":
                require(("followup_id" in payload) != ("waiting" in payload), "Wait requires exactly one followup_id or waiting object")
                if "followup_id" in payload:
                    require(task["waiting"] is None and task["followup_id"] in {None, payload["followup_id"]},
                            "Cannot discard an existing dependency")
                    item = _followup(root, payload["followup_id"])
                    require(item["followup"].get("disposition") == "awaiting_evidence", "Followup must be waiting")
                    task["followup_id"] = payload["followup_id"]
                else:
                    _waiting_shape(root, payload["waiting"])
                    _check_ref(root, payload["waiting"]["evidence_ref"])
                    require(task["waiting"] is None, "Cannot overwrite waiting dependency")
                    task["waiting"] = payload["waiting"]
                task["status"] = "waiting"
                _end(task)
            elif action in {"pause", "cancel"}:
                task["status"] = "paused" if action == "pause" else "cancelled"
                _end(task)
            elif action == "resume":
                require(task["status"] == "paused", "Resume requires paused task")
                task["status"] = "waiting" if _wait_open(root, task) else "ready"
            elif action == "rebind":
                for key in ("goal_ref", "acceptance_ref", "action_ref"):
                    if key not in payload:
                        continue
                    old, new = task[key], payload[key]
                    require(old is not None, "Rebind cannot add project-action permission")
                    _check_ref(root, new)
                    require(new["path"] == old["path"] and new.get("quote") == old.get("quote"),
                            "Rebind must retain original path and quote scope")
                    # Whole-file edits cannot establish that goal/acceptance
                    # intent survived; use exact quote scope from registration.
                    require("quote" in old or new["sha256"] == old["sha256"],
                            "Whole-file scope changes require a new task; cannot verify unchanged intent")
                    task[key] = new
                task["status"] = "blocked"
                task["evidence_refs"] = []
                _end(task)
            elif action == "interrupt":
                require(task["active_attempt"] is not None and task["active_attempt"]["attempt_id"] == payload["attempt_id"],
                        "Active attempt fence mismatch")
                task["status"] = "blocked"
                _end(task)
        task["revision"] += 1
        require(task["revision"] <= MAX_OPERATIONS, "Task operation limit reached")
        result = {"task_id": ident, "revision": task["revision"], "status": task["status"],
                  "operation_id": op, "completion_scope": task["completion_scope"], "recorded_at": _now()}
        task["events"].append({"revision": task["revision"], "operation_id": op, "payload": payload,
                               "status": task["status"], "recorded_at": result["recorded_at"]})
        task["operations"][op] = {"payload_sha256": fingerprint, "result": result}
        _validate(root, task, ident)
        _save(root, _task_path(ident), task)
        return deepcopy(result)


def _task_ids(root):
    folder = checked_path(root, ".flg/tasks")
    if not folder.exists():
        return []
    require(folder.is_dir(), "Task records path must be directory")
    result = []
    # Bound scanning as well as returned output. Refuse an overfull store.
    for path in folder.iterdir():
        require(len(result) < MAX_TASKS, "Task store exceeds 100-record stage-1 limit")
        require(path.suffix == ".json", "Unknown task-store entry")
        _id(path.stem)
        checked_path(root, f".flg/tasks/{path.name}")
        result.append(path.stem)
    return sorted(result)


def _projection(root, task):
    issues = []
    wait_open = False
    try:
        _fresh(root, task)
        wait_open = _wait_open(root, task)
        if wait_open and task["status"] in {"ready", "running"}:
            issues.append("Unresolved dependency requires owner recheck; takeover/completion unavailable")
    except ERRORS as exc:
        issues.append(str(exc)[:300])
    result = deepcopy(task)
    result["issues"] = issues
    result["needs_recheck"] = bool(issues) or task["status"] == "blocked"
    result["checks"] = {"needs_recheck": result["needs_recheck"], "refs_valid": not issues,
                        "actor_identity": "host-asserted", "completion_scope": "local_artifacts",
                        "project_action_permission": False, "wait_open": wait_open}
    if wait_open and task["status"] in {"ready", "running"}:
        safe = "owner dependency recheck; pause/cancel; no takeover/completion"
    elif issues:
        safe = "explicit source review or same-path evidence refresh; owner pause/cancel"
    else:
        safe = {"ready": "owner takeover", "running": "current executor progress/wait/complete local_artifacts",
                "waiting": "owner recheck with evidence after dependency resolution", "blocked": "owner recheck with evidence",
                "paused": "owner resume", "completed": "terminal; no reopen", "cancelled": "terminal; no reopen"}[task["status"]]
    result["next_safe_action"] = safe
    return result


def show(root, task_id) -> dict:
    """Read top-level task fields plus checks; corrupt state is never executable."""
    root, ident = Path(root), _id(task_id)
    try:
        # Hosts may pass a root alias for read views. Subpath checks stay strict.
        root = root.resolve(strict=True)
        config = _config(root)
        if not config["enabled"]:
            return {"enabled": False, "task_id": ident, "issues": [], "checks": {"executable": False}}
        return {"enabled": True, **_projection(root, _read_task(root, ident))}
    except (*ERRORS, RuntimeError) as exc:  # Older Python raises RuntimeError for symlink loops.
        return {"enabled": True, "task_id": ident, "status": "unknown", "revision": None,
                "active_attempt": None, "needs_recheck": True, "issues": [str(exc)[:300]],
                "checks": {"needs_recheck": True, "executable": False}, "next_safe_action": "owner inspect corrupt local record"}


def collect(root) -> dict:
    """Bounded read-only projection; corruption is explicit, never implicit off."""
    root = Path(root)
    try:
        root = root.resolve(strict=True)
        config = _config(root)
        if not config["enabled"]:
            return {"enabled": False, "tasks": [], "issues": []}
        ids = _task_ids(root)
        tasks = [show(root, ident) for ident in ids]
        # Readers never acquire the write lock. Detect config changes across
        # this projection, including disable/enable ABA via its append history.
        # Revalidate instead of treating mixed or corrupt state as disabled.
        require(_config(root) == config and all(task["enabled"] for task in tasks),
                "Task continuity configuration changed during read; retry")
    except (*ERRORS, RuntimeError) as exc:
        return {"enabled": True, "tasks": [], "issues": [str(exc)[:300]], "needs_recheck": True}
    issues = [{"task_id": task["task_id"], "error": issue} for task in tasks for issue in task["issues"]][:50]
    return {"enabled": True, "tasks": tasks, "issues": issues,
            "needs_recheck": any(t["needs_recheck"] for t in tasks)}


def render_notice(root) -> str:
    """Read-only host-asserted/local_artifacts notice; never execution authority."""
    report = collect(root)
    if not report["enabled"]:
        return ""
    lines = ["Task continuity (host-asserted actors; local_artifacts only; reading grants no authority):"]
    visible = [task for task in report["tasks"] if task["status"] not in TERMINAL or task["needs_recheck"]]
    visible.sort(key=lambda task: (task["status"] in TERMINAL, not task["needs_recheck"], task["task_id"]))
    history_count = len(report["tasks"]) - len(visible)
    if not visible and not report["issues"]:
        lines.append(f"No active tasks; {history_count} historical tasks.")
    elif history_count:
        lines.append(f"{history_count} historical tasks omitted; available in list/show.")
    for task in visible[:4]:
        wait = task.get("waiting")
        detail = f"; wait={wait['condition']}; trigger={wait['trigger']}" if wait else ""
        if task.get("followup_id"):
            detail += f"; followup={task['followup_id']}"
        lines.append(f"- {task['task_id']} revision={task['revision']} status={task['status']}; next={task['next_safe_action']}{detail}"[:320])
    if len(visible) > 4:
        lines.append(f"- {len(visible) - 4} tasks omitted")
    for issue in report["issues"][:3]:
        lines.append(f"- needs_recheck: {issue}"[:240])
    if len(report["issues"]) > 3:
        lines.append(f"- {len(report['issues']) - 3} issues omitted")
    lines.append("Expand with flg task list / flg task show <task_id>.")
    return "\n".join(lines) + "\n\n"
