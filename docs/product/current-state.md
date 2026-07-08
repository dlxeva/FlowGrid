# FlowGrid Current State

Last updated: 2026-07-07
Primary branch: `master`

## Purpose of this File

This is the first file a future local agent, Codex session, or ChatGPT connector session should read before continuing FlowGrid work.

It exists to prevent context loss between conversations, local repository work, and GitHub connector work.

## Product Position

FlowGrid is currently defined as:

> A local project-state context engine for rationale-heavy, non-coding business projects.

The target work pattern is not ordinary task execution. It is long-running judgment work where the deliverable depends on preserving why a direction was chosen, what alternatives were rejected, what evidence supported the call, and when the call should be reopened.

Do not expand the concept until the current stabilization loop is closed.

## Branch Policy

Use `master` as the active mainline branch.

Do not split work across `main` and `master`. The repository default branch is `master`, and recent stabilization commits are on `master`.

Treat `main` as non-authoritative unless the repository default branch is intentionally migrated later.

## Current Stabilization Goal

The active goal is to close a stable loop around:

1. reviewed decisions
2. evidence lookup
3. bounded Context Pack generation
4. manual eval on a rationale-heavy business scenario

The current loop is about validation and documentation, not feature expansion.

## Completed in the 2026-07-07 Stabilization Pass

### 1. Smoke test failure path fixed

`scripts/smoke_test.py` now selects the latest `closeout-*.patch.md` for review instead of taking the last patch by filename across all patch types.

This matters because the smoke flow can create both `frame-*` and `closeout-*` patches. Reviewing the wrong patch can skip candidate decisions and fail the `review -> evidence -> context` path.

Commit:

- `8ee6dfcf46a8a898f267f5e90f76deec8c3b4442` — `Fix smoke test closeout patch selection`

### 2. Campaign proposal manual eval recorded

A first directional manual eval was recorded at:

```text
evals/results/campaign-proposal-manual-001.md
```

Commit:

- `83a00349f9f0b5200b3951eefc79c26a28cb3118` — `Record campaign proposal manual eval result`

### 3. Stabilization closeout recorded

A detailed closeout note was added at:

```text
docs/product/stabilization-closeout-2026-07-07.md
```

Commit:

- `96e1ed773de32ecb72217f37b9a81e2034744b73` — `Add stabilization closeout note`

## Manual Eval Snapshot

Scenario:

```text
evals/scenarios/campaign-proposal/
```

Directional result:

| Mode | Score | Interpretation |
|---|---:|---|
| Mode A — No FLG State | 8/14 | Inflated by leakage in `resume-prompt.md` |
| Mode B — Raw History | 13/14 | Strong because raw history is short and clean |
| Mode C — FlowGrid Context Pack | 14/14 | Best continuation surface |

Product interpretation:

- Context Pack is directionally valid for this scenario.
- The eval does not yet justify generator changes.
- The fixture should be tightened before adding more scenarios.

## Known Open Items

### Capture Pipeline Design (v0.4 prep)

Design RFC drafted at `docs/product/judgment-capture-pipeline.md`. Implementation gated on v0.3 Phase 1-2 completion.

4 open questions for review:
1. Command name: `flg capture` vs `flg judgment`?
2. `decision add` directly writes DECISIONS.md — accept breaking patch-first?
3. `capture review` auto-merge or manual `flg merge`?
4. Field named `type` or `judgment_type`?

### Eval Fixture: raw-session.md noise

The campaign-proposal `raw-session.md` is currently clean and short. Mode B scored 13/14, Mode C 14/14 — a 1-point gap. Adding noise/length would better separate Mode B from Mode C, but this is optional. Only do if new eval runs show weak separation.

## Next Session Order

1. Review Design RFC at `docs/product/judgment-capture-pipeline.md`; resolve 4 open questions.
2. If capture pipeline is approved, proceed with v0.3 Phase 1 (State Contract Lock) → Phase 2 (Protocol Alignment).
3. After v0.3 Phase 1-2 complete, open `feature/capture-pipeline` branch for implementation.
4. Optionally: add noise to `evals/scenarios/campaign-proposal/raw-session.md` to widen Mode B/C gap.

## Stabilization Status

- ✅ README command table updated (context + evidence commands, trace note)
- ✅ Smoke test passed (init → frame → closeout → review → evidence → context → handoff → status)
- ✅ Pytest: 77 passed
- ✅ Eval fixture tightened: resume-prompt.md no longer leaks KOL boundary to Mode A
- ⬜ Optional: add noise to raw-session.md

The v0.3 stabilization loop is closed. New work can proceed into Phase 1 (State Contract Lock).

## Current Guard Rule

New commands (e.g. `flg capture`) must go through design lock first — see `docs/product/judgment-capture-pipeline.md`. Do not implement before v0.3 Phase 1-2 completion.

## Useful Reading Order for Future Agents

1. `docs/product/current-state.md`
2. `docs/product/context-reset-handoff-2026-07-07.md`
3. `docs/product/stabilization-closeout-2026-07-07.md`
4. `evals/results/campaign-proposal-manual-001.md`
5. `scripts/smoke_test.py`
6. `README.md`

## Non-Goals Right Now

- Do not turn FlowGrid into a generic PM tool.
- Do not optimize for coding-agent workflows.
- Do not add a dashboard or SaaS framing.
- Do not expand personas or verticals.
- Do not add `flg trace` implementation yet.
- Do not rename or migrate branches yet.