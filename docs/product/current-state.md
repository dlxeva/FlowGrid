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

## Known Open Item

README still needs a direct command-table update.

Required README patch:

Add these rows after `flg review --patch <file>`:

```md
| `flg context --mode resume` | Generate bounded agent startup Context Pack |
| `flg evidence <decision-id>` | Show evidence behind a reviewed decision |
```

Add this note after the command table:

```md
`flg trace` is planned future work and is not implemented in the current CLI.
```

Update the Smoke Test description from:

```md
The smoke test creates a temporary project, runs `init`, `frame`, `closeout`, `handoff`, and `status`, then prints the generated files.
```

to:

```md
The smoke test creates a temporary project, runs `init`, `frame`, `closeout`, `review`, `evidence`, `context`, `handoff`, and `status`, then prints the generated files.
```

## Next Session Order

Do these in order:

1. Apply the README patch above.
2. Run:

```bash
python scripts/smoke_test.py
pytest -q
```

3. If tests pass, tighten `evals/scenarios/campaign-proposal/resume-prompt.md` so Mode A no longer receives the key answer.
4. Make `raw-session.md` longer/noisier only if needed to better separate Mode B from Mode C.

## Stop Rule

Do not add new commands, new templates, new scenarios, or new conceptual positioning before the README patch and test rerun are complete.

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