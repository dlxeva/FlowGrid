# FlowGrid Current State

Last updated: 2026-07-08
Primary branch: `master`
Version: v0.3.0

## Product Position

FlowGrid is a local project-state context engine for rationale-heavy, non-coding business projects.

The target work pattern is long-running judgment work where the deliverable depends on preserving why a direction was chosen, what alternatives were rejected, what evidence supported the call, and when the call should be reopened.

## What Changed in v0.3.0

### Capture Pipeline (P0-P3)

Real-time judgment capture is now fully implemented:

| Command | Description |
|---------|-------------|
| `flg capture add` | Capture a judgment candidate in real-time |
| `flg capture list` | List candidates (filter by type/status) |
| `flg capture show` | View full details and raw evidence |
| `flg capture review` | Interactive review → accept into DECISIONS.md or reject |
| `flg capture profile` | Manage project-specific judgment trigger phrases |
| `flg decision add` | Direct write to DECISIONS.md (strong commitment only) |

Key design:
- Captures stored in `.flg/captures/` (YAML frontmatter), aligned with existing judgment-status-model
- `closeout` (batch extraction) and `capture` (real-time) coexist as complementary pipelines
- Agent detection protocol defined in `flg-workflow` skill → `references/capture-trigger-rules.md`
- Full Design RFC: `docs/product/judgment-capture-pipeline.md`

### v0.3 Stabilization

- README command tables updated (CN + EN)
- Smoke test covers 10 commands: init → frame → closeout → review → evidence → context → capture add → capture list → capture show → handoff → status
- Eval fixture tightened (resume-prompt no longer leaks KOL boundary to Mode A)
- 77 tests passing, 0 regression

## Current Branch

Single active branch: `master`. Feature branch `feature/capture-pipeline` merged and deleted.

## Open Items

- `flg trace` — planned, not implemented
- Eval Set v0 scenarios 4-5 — fixtures needed
- Role and task templates — Phase 6 of v0.3 plan
- Dogfood scenarios — Phase 7 of v0.3 plan

## Non-Goals

- Do not turn FlowGrid into a generic PM tool
- Do not optimize for coding-agent workflows
- Do not add dashboard or SaaS framing

## Reading Order for Future Agents

1. `docs/product/current-state.md` (this file)
2. `docs/product/judgment-capture-pipeline.md` (Design RFC)
3. `docs/product/v0.3-plan.md`
4. `docs/protocol.md`
