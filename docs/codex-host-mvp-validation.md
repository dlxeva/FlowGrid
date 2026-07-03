# Codex Host MVP Validation

## Goal

Validate that a real user can stay inside Codex, work in natural language, and still complete the full FlowGrid loop:

1. `init`
2. raw session capture
3. `closeout`
4. `review`
5. `merge`
6. `resume`

## Validation Setup

A high-fidelity sandbox project was created under a temporary directory:

- project name: `Codex Host MVP`
- template: `strategy`
- session file stored under `.flg/sessions/`

The sandbox was used instead of a production project so the full loop could be exercised without polluting real ledgers.

## Session Input

The validation session contained a realistic project-language exchange:

- clarify the homepage promise
- state the real promise
- state what the product is not
- record a concrete positioning decision

This was saved as a raw session file and then used as `closeout` input.

## What Was Verified

### 1. Project initialization

Verified:

- `PROJECT.md`
- `FRAMING.md`
- `DECISIONS.md`
- `SNAPSHOT.md`
- `PROGRESS.md`
- `GOAL_EVOLUTION.md`
- `CONSTRAINTS.md`
- `.flg/`

were created successfully.

### 2. Raw session to patch

Verified:

- `flg closeout --transcript .flg/sessions/<session>.md`

produced a pending patch.

### 3. Human decision confirmation

Verified:

- `flg review --patch <patch> --accept-all`

accepted the candidate decision and wrote it into `DECISIONS.md`.

### 4. Merge after review

Verified:

- `flg merge --patch <patch>`

did **not** re-warn that the reviewed decision still needed manual handling.

It:

- appended to `PROGRESS.md`
- produced a merge log
- marked the patch as merged in `.flg/state.json`

### 5. Resume state

Verified:

- `flg status`
- `flg handoff`
- `flg export-handoff`

all worked after the patch had moved through review/merge.

## Key Evidence

### State evidence

Observed in `.flg/state.json`:

- `status: merged`
- `decision_review_status: accepted`
- `merged_at: <timestamp>`

### Ledger evidence

Observed in `DECISIONS.md`:

- the accepted decision was appended as a formal decision entry

Observed in `PROGRESS.md`:

- session progress entry was appended by merge

### Merge evidence

Observed in `.flg/merge_logs/...`:

- `Merged Files: PROGRESS.md`
- `Skipped Sections: Candidate decisions (already accepted via review)`

## What This Proves

This is enough to support a concrete product claim:

**A user can stay inside Codex, talk naturally, let Codex call FlowGrid at the right moments, and complete the full ledger loop without treating the CLI as the primary interface.**

More specifically:

- natural language can remain the interaction layer
- raw session files can serve as closeout input
- reviewed decisions can become formal ledger entries
- merge can complete the rest of the patch without re-opening the same decision boundary
- project state can be resumed from files later

## Remaining Rough Edges

- `review` still writes a generic decision template entry rather than a more polished domain-shaped decision block
- `status` still emphasizes patch presence more than “human host workflow state”
- there is not yet a dedicated helper command for saving host session notes before closeout

These are quality issues, not blockers for the MVP claim.

## Conclusion

The Codex host MVP is validated:

- not as a GUI product
- not as a standalone CLI-first product
- but as a **host-integrated local protocol workflow** where Codex is the interaction surface and FlowGrid is the project state layer.
