# Task continuity: bounded stage-1 implementation contract

This work is an opt-in local continuation slice, authorized 2026-11-01. It does
not implement external effects, distributed leases, remote identity verification,
formal judgment approval or automatic task extraction. Existing projects and
their runtime mappings must remain unchanged. No release/version bump.

## Core API (owned by implementation worker)

Module `flg.core.task_continuity`:

- `configure(root, payload) -> dict`: explicit enable/disable. Payload contains
  `enabled: bool`, `actor`, `request_ref` (source reference). No silent default
  enabling. Disabling refuses live attempts or unresolved task work; keep files.
- `apply(root, task_id, payload) -> dict`: sole local task state mutation.
- `show(root, task_id) -> dict`: read-only task with derived check state.
- `collect(root) -> dict`: disabled returns `enabled: false, tasks: [], issues: []`
  without creating anything; enabled returns bounded tasks and issues.
- `render_notice(root) -> str`: empty for disabled projects; bounded read-only
  projection for context/status/handoff. Never grant authority by reading.

Task config `.flg/task-continuity.json`; per-task atomic record
`.flg/tasks/<task_id>.json`. IDs restricted ASCII, max 80 chars, no path escapes.
Keep state+event+operation receipts in one task record. Reuse existing path/hash
validation, `project_operation_lock`, `atomic_write_text`; do not edit state.json.
Treat corrupted/unknown schema or symlinked paths fail-closed, never as disabled.

All apply requests have `action`, `expected_revision`, `operation_id`, `actor`.
Reject unknown request keys and invalid types, including bool revisions. Exact
operation ID + same canonical payload returns prior result; different payload
rejects; reject duplicates even after intervening operations. Check request
identity before mutation; task records contain revision and append-only events.
The same task key must be explicitly mapped from an existing business task or
newly registered; do not infer/dedupe by goal text. No new business fact ledger.

References: `{path, sha256}` for whole-file scope, optionally `quote` for exact
UTF-8 substring scope with sha256 of that quote. Use project-relative regular
files; file refs bind bytes. Quote occurrence must be unique so unrelated edits
can stay valid. Never write referenced files. Keep references in task, do not
duplicate their body. Source drift blocks progress/recheck/resume/complete;
show reports `needs_recheck` without mutating the lifecycle. Permit pause/cancel
even with stale references. Rebinding needs an explicit owner operation and new
refs, with immutable history, not silent hash refresh.

Registration: revision 0, actor=owner, owner string, goal_ref,
acceptance_ref (predeclared criteria source), `criteria` nonempty list of
`{id, path}` describing required local artifact paths. Optional `followup_id`
references an existing capture, optional `action_ref` references an authoritative
current task action. Result ready revision 1, no attempt. This slice validates
local artifact existence and exact versions only; semantic acceptance and formal
approval remain in existing review. Mark completion scope `local_artifacts`.
Reject criteria requesting formal approval/remote effects instead of faking it.

Operations:
- takeover: owner actor, fresh refs, ready/running only; required `executor` and
  new `attempt_id`; replace old running attempt explicitly, increment revision.
- progress: current executor actor + active attempt_id + running task; required
  evidence_refs nonempty; record refs and event, do not overwrite project files.
- wait: current executor/attempt; required existing followup_id OR waiting object
  `{condition, trigger, evidence_ref}`; preserve dependency refs; end attempt;
  task waiting. Existing followup must be waiting, and remain source of facts.
- recheck: owner, waiting/blocked only, explicit evidence_refs; validate refs and
  existing followup disposition. Cannot clear an unresolved followup. New material
  alone never auto-authorizes. End in ready, no running attempt.
- pause/cancel: owner, nonterminal; end active attempt, task paused/cancelled.
- resume: owner, paused only; fresh refs and still-open waits remain waiting,
  otherwise ready. Never start attempt implicitly.
- rebind: owner, nonterminal; explicit new goal_ref/acceptance_ref/action_ref,
  retain task intent (goal changes require new task); blocked pending recheck,
  end attempt. Original criteria must remain, no completion-rule weakening.
- complete: current executor/attempt, running, fresh refs, evidence_refs with
  exact current file refs covering all predeclared criterion paths; atomically
  complete local_artifacts task and end attempt. No automatic decision adoption.

Task states: ready/running/waiting/blocked/paused/completed/cancelled. Attempts
running/ended/replaced; explicit interruption action may block a task but no
timeouts or background auto-takeover. Terminal tasks cannot reopen. Session end
never calls complete. Actor strings are host assertions, not authenticated
identities; publish this limitation. No promises about old writers outside this
new task-record API.

Tests owned by worker: core tests for opt-in, zero writes when disabled, schema
and paths, CAS and old-attempt fence, operation replay/conflict, task/session
independence, waiting read stability, pause/cancel, recheck, refs drift/quote,
artifact completion checks, data preservation and atomic-write failure.

## Integration (owned by parent)

Parent owns CLI adapter `flg task enable/disable/list/show/apply`, existing CLI
registration and status, context/handoff/doctor projections, integration tests,
public docs. JSON input remains a host interface; users need not hand-operate it.
No existing mutation command will be described as task-fenced in this slice.
Existing follow-up is referenced and checked, not rewritten by this module.

Stop before modifying a real project's ledger, runtime mapping, installed skill,
release version/tag, pushing or publishing. Work only in this isolated worktree.
