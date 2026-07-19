# FlowGrid Current State

Last updated: 2026-07-20
Primary branch: `master`
Current code version: `v0.3.0`
Current stage: `v0.4 core validation`

## Product Position

FlowGrid is a local project-state context engine for rationale-heavy, non-coding business projects.

Its job is to let project state, boundaries, judgments, progress, and next actions follow the project directory across AI sessions and hosts, reducing repeated context explanation.

## Current Implemented Surface

- English-first project initialization and localized ledger entries
- `closeout` raw transcript archiving under `.flg/sessions/`
- Batch closeout extraction with pending review patches
- Real-time `capture add/list/show/review`
- Explicit `decision add` for strong user commitments
- `doctor` and `reindex` for cross-file consistency and rebuildable evidence indexes
- Bounded Context Pack, evidence lookup, handoff, onboarding, and host-agnostic Agent Skill
- Advisory evidence-basis quality signal for complete `FRAMING.md` files
- Patch lifecycle parsing that preserves rejected and superseded states

## Current Verification

- `160` tests passed
- `python scripts/smoke_test.py` passed
- English-native deterministic gate passed
- Real FlowGrid ledger audit passed with an expected undeclared-evidence-basis warning
- Background review only promotes candidates with explicit user/client attribution; pending candidates, risks, and next actions do not become current truth
- Remote LLM extraction requires explicit per-command consent with `--allow-remote-llm`
- A disposable real-project replay verified that an `Assistant:` proposal remains auditable but cannot enter formal state through the background loop; see [host-like acceptance](../../evals/results/host-like-continuation-safety-20260720.md)

## Current Goal

Complete the v0.4 core loop:

1. Raw discussions reliably enter the project state layer.
2. Formal ledger state and evidence indexes can be rebuilt from source files.
3. Real, long, contradictory project histories show lower context-repetition cost for the next Agent.

## Immediate Priorities

- Validate automatic session capture across Codex, ZCode, Hermes, and other supported hosts.
- Run isolated comparisons between no state, raw history, and FlowGrid Context Pack.
- Measure repeated explanation, revived rejected directions, candidate/fact confusion, hallucinated project facts, and user correction count.
- Keep `DECISIONS.md` as formal truth and avoid adding new cognitive abstractions until the loop is proven.
- Run one explicitly authorized external-host continuation. Measure raw transcript availability, speaker-label preservation, candidate false positives/negatives, user CLI burden, and fresh-agent recovery.

## Deferred

- Quadrant tags and protocol routing
- Blindspot pass and unknown-unknown discovery engine
- Multi-source provenance graph and `flg trace`
- Graph database, ABAC, GUI, cloud sync, SaaS, and generic project management features

## Non-Goals

- Do not turn FlowGrid into a generic PM tool.
- Do not optimize for coding-agent workflows.
- Do not present v0.4 as released before real-project validation is complete.

## Reading Order for Future Agents

1. `docs/product/current-state.md`
2. `docs/product/future-direction.md`
3. `docs/product/judgment-capture-pipeline.md`
4. `docs/protocol.md`
