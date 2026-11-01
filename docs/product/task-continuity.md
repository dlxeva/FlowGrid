# Local task continuation (experimental, opt-in)

This extension keeps a small continuation record for an explicitly selected
project task. The task retains its identity across processes; an execution
attempt can end or be replaced without completing the task. It is disabled by
default. No historical task extraction, automatic migration, daemon or scheduler
runs when it is installed.

## Reuse and authority

Keep goals, acceptance criteria, decisions and business progress in their existing
project sources. Task records retain references and execution metadata. Map an
existing project task key explicitly; do not use text similarity to invent a
second task. Refer to an existing candidate follow-up when it owns the wait.
The task API does not rewrite that follow-up or adopt a judgment.

The configuration is `.flg/task-continuity.json`; task records live under
`.flg/tasks/`. Each record contains state, attempts and operation history in one
atomic replacement. Existing `.flg/state.json` and formal documents remain
unchanged. This does not provide an atomic transaction across project documents
or external tools.

## Host interface

The host interprets a user's request and supplies explicit project-relative JSON
input. Users can continue speaking naturally; these commands are a host interface:

```sh
flg task enable --input host-enable.json
flg task apply T17 --input host-operation.json
flg task show T17
flg task list
flg task disable --input host-disable.json
```

`enable`/`disable` inputs contain `actor` and `request_ref`. A source reference
contains a project-relative `path` and lowercase `sha256` of its exact bytes.
Optional `quote` scope binds one exact, unique UTF-8 passage and its hash; unrelated
edits outside that passage do not invalidate it. Reference bodies stay at source.

An enable input, with the hash replaced by the actual source hash:

```json
{
  "actor": "project-owner",
  "request_ref": {"path": "requests/task-request.md", "sha256": "<actual-sha256>"}
}
```

Each operation contains `action`, `expected_revision`, `operation_id` and `actor`.
Registration uses revision zero and explicitly names the owner, goal source,
acceptance source and local artifact criteria:

```json
{
  "action": "register",
  "expected_revision": 0,
  "operation_id": "register-T17-1",
  "actor": "project-owner",
  "owner": "project-owner",
  "goal_ref": {"path": "tasks/T17-goal.md", "sha256": "<actual-sha256>"},
  "acceptance_ref": {"path": "tasks/T17-acceptance.md", "sha256": "<actual-sha256>"},
  "criteria": [{"id": "draft", "path": "outputs/draft.md"}]
}
```

The same operation ID with the exact original payload returns its original
receipt without a second state transition. The same ID with different content
is rejected. Read the current revision before a new operation; conflicts require
rereading, not overwriting.

## Local lifecycle

- `register`: creates a ready task; no active attempt.
- `takeover`: the owner explicitly assigns a new `attempt_id` and `executor`.
  A replaced attempt loses task-record write access, even if it learns the new
  revision. No automatic takeover by elapsed time.
- `progress`: the current executor supplies `attempt_id` and `evidence_refs`.
  Fresh same-path evidence can explicitly replace an earlier artifact observation;
  prior versions remain in event history. Goal/acceptance authority cannot be
  refreshed this way.
- `wait`: ends the current attempt and preserves a wait. Reference an existing
  `followup_id`, or supply a task-specific `waiting` condition, trigger and
  `evidence_ref` when no existing source owns it.
- `recheck`: the owner supplies evidence and revalidates prerequisites before
  moving waiting/blocked work to ready. It does not start an attempt. Merely
  receiving a file does not invoke this action or approve a conclusion.
  An explicit same-path observation can update the local waiting evidence;
  unresolved candidate follow-ups still block this transition. Multiple waits
  must all be resolved.
- `pause` / `cancel`: owner control actions revoke the active attempt. Later
  input and late executor writes cannot revive the task.
- `resume`: revalidates a paused task and returns it to ready or waiting; a
  separate takeover is needed before executor writes.
- `complete`: the current executor supplies version-bound evidence for every
  predeclared local artifact criterion. It ends the attempt and task together.
- `interrupt`: the owner explicitly records an interrupted attempt, leaving a
  blocked task that needs evidence-based recheck. Session archiving alone does
  not invoke this action or complete work.

Task states are ready, running, waiting, blocked, paused, completed and cancelled.
Source drift produces a read-only `needs_recheck` finding. Reading never changes
the persisted lifecycle, clears a wait, assigns an executor or grants permission.
Completed/cancelled tasks cannot be reopened. Source correction requires an
explicit reviewed rebind; changing the goal's meaning requires a new task.
The initial rebind path retains the original path and exact quote scope. It does
not automatically accept a changed whole-file goal or acceptance document. Keep
authority sources stable or use a precisely declared passage; changed intent
must be reviewed and mapped explicitly.

`context --mode resume`, `manifest`, `work`, handoff, status and doctor display a
bounded task projection. Use `task show` to expand details. These views remain
derived; the formal current action keeps its existing authority.

## Completion and authorization limits

Completion scope is **local_artifacts**. The program checks required artifact
paths and exact evidence versions. It does not assess document quality, prove
that a recommendation is true, confirm a human accepted a judgment, approve a
release or certify business completion. Keep those acceptance decisions in the
existing project review flow. Do not register a formal-approval task and pretend
that the local artifact check satisfies it.

Actor names and authorization sources are assertions made by the participating
local host. This extension does not authenticate users or cryptographically
validate natural-language permission. The host must obtain actual authority and
resolve ambiguous requests before submitting an operation.

The attempt fence protects this task-record API only. Existing review/merge,
decision submission, arbitrary shell writes and external tools do not acquire a
task fence by installation. A participating host must not treat a task record as
permission to bypass those tools' existing approval requirements.

External intent/permit/receipt handling and `outcome_unknown` recovery are not
implemented in this local slice. Do not use it to justify replaying an uncertain
external operation. There is no end-to-end exactly-once guarantee. Cross-machine
ownership and crash-stale lock recovery have not been established.

## Compatibility and exit

Disabled projects do not acquire task state, changes to formal sources or new
task notices. This extension does not switch project runtime mappings or change
installed skills. Explicit enabling is scoped to one project.
An unrelated legacy `.flg/tasks/` directory does not opt a project in. Deleting
configuration or editing task records outside this API is outside its guarantees.

Disabling requires resolving live task work first and retains history. A corrupt
or unsupported extension reports a health issue; it is never silently treated as
disabled. Unknown or stale writers outside the task API remain outside its
protection, so enabling does not establish compatibility with arbitrary old hosts.
This bounded initial store supports at most 100 tasks, 1,000 operations per task
and 2 MiB per record. Writes exceeding limits are rejected without a partial
transition; these are explicit experimental limits, not a production-scale claim.

## Validation boundary

Synthetic tests cover new-process continuation, explicit takeover, stale-worker
rejection, source drift, operation replay/conflict, wait read stability,
pause/cancel, version-bound local completion and unchanged disabled projects.
Existing regression and smoke tests check integration. These do not establish
that a real multi-person project resumes faster or makes fewer mistakes. That
requires a separately scoped real-task trial and a recorded baseline.
