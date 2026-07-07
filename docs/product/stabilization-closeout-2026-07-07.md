# FlowGrid Stabilization Closeout — 2026-07-07

## Scope

This closeout records the stabilization work performed after `docs/product/context-reset-handoff-2026-07-07.md`.

No new product concepts, commands, eval scenarios, or templates were added.

## Completed

### 1. Smoke test failure path fixed

`scripts/smoke_test.py` was updated so the review step selects the latest `closeout-*.patch.md` instead of taking the last patch by filename across all patch types.

Reason: the smoke flow creates both `frame-*` and `closeout-*` patches. Reviewing a `frame-*` patch can produce no candidate decisions and fail to validate the `review -> evidence -> context` path.

Commit:

- `8ee6dfcf46a8a898f267f5e90f76deec8c3b4442` — `Fix smoke test closeout patch selection`

### 2. Campaign proposal manual eval recorded

A first directional manual eval was recorded at:

```text
evals/results/campaign-proposal-manual-001.md
```

Commit:

- `83a00349f9f0b5200b3951eefc79c26a28cb3118` — `Record campaign proposal manual eval result`

## Manual Eval Result Summary

Scenario:

```text
evals/scenarios/campaign-proposal/
```

Directional score:

| Mode | Score | Result |
|---|---:|---|
| Mode A — No FLG State | 8/14 | Passes only because `resume-prompt.md` already leaks key boundaries |
| Mode B — Raw History | 13/14 | Strong because raw history is short and clean |
| Mode C — Context Pack | 14/14 | Best continuation surface |

Main finding:

Mode C wins, but the scenario currently understates FlowGrid's advantage because:

1. `resume-prompt.md` includes key KOL/proof-object constraints, making Mode A stronger than a true no-state baseline.
2. `raw-session.md` is short and clean, making Mode B closer to Context Pack than a realistic noisy history.

Product implication:

The Context Pack contract is directionally valid for this scenario. The next improvement should target eval fixture quality before adding more eval scenarios.

## README Remaining Patch

The README command table still needs to be updated. The connector blocked direct full-file replacement during this closeout, so the required patch is recorded here.

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

## Current State Check

The stabilization loop is almost closed:

- smoke test failure path fixed
- campaign-proposal manual eval recorded
- eval result reviewed for product implications
- README command table still needs direct file update

## Stop Rule

Do not add new eval scenarios, templates, or commands next.

Next working session should first apply the README patch above, then rerun:

```bash
python scripts/smoke_test.py
pytest -q
```

Only after that should `campaign-proposal` fixture quality be tightened.