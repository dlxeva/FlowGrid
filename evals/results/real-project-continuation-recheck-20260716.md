# Real-Project Continuation Recheck

**Date:** 2026-07-16
**Scope:** Re-run the continuation comparison after the Context Pack next-action and source-health fixes.

## Privacy boundary

This report uses disposable, redacted copies of two local projects:

- **Project W:** a real project with substantial ledger/index drift.
- **Project F:** a healthy FlowGrid project used as a control.

Project names, local paths, and identifying material are intentionally omitted.

## Results

| Sample | Context Pack next action | Source-health signal |
|---|---|---|
| Project W | Preserved the explicit Fixture 05 evaluation and field-spec unification action. | `needs_attention`: 63 formal decisions, 14 indexed, 49 missing index entries. |
| Project F | Preserved the continuation-evaluation action. | `ok`: 27 formal decisions, 27 indexed, no missing or orphan entries. |

The repaired Context Pack now handles the Snapshot heading variants used by both projects and surfaces deterministic ledger/index health instead of presenting an apparently complete pack.

## Verification

- `134 passed`
- `python scripts/smoke_test.py`
- `git diff --check`
- Current FLG project `flg doctor`: 27 formal decisions, 27 indexed, 0 missing, 0 orphan, 0 broken evidence references.

## Additional fix

An empty `flg closeout` previously rewrote `SNAPSHOT.md` with default placeholders even when no decisions, risks, or next actions were extracted. That behavior is now a no-op and has a regression test. The fix merged in PR #23.

## What this does not prove

- It does not prove that raw history is always worse than a Context Pack.
- It does not prove automatic source capture at the host level.
- It does not authorize repair of Project W's real ledger; that remains an explicit project-owner action.

## Next test

Run the full regression gate in CI, then test whether a fresh Agent automatically preserves the raw discussion and triggers the closeout path on a disposable project copy.
