# Current Action Deterministic Replay - 2026-08-12

## Purpose

Verify the first Continuation V2 repair against the same three live project
states without using a model judge.

## Method

The evaluation-branch generator built fresh Resume and Manifest artifacts
directly from each project's current formal ledger. Source projects were read
only. The replay checked whether both views selected the same formal action,
ignored older state-cache actions, or abstained on a deterministic
contradiction.

## Result

| Project | Resume | Manifest | Legacy fallbacks ignored |
| --- | --- | --- | ---: |
| FlowGrid | `current`: external-host trial | same | 1 |
| FlightModeAI | `needs_reconciliation`: stale patch-review action refused | same | 0 |
| AI thinking canvas | `current`: geometry source + independent math review | same | 4 |

Across all three projects:

- Resume/Manifest current-action disagreements: `0`;
- stale actions exposed as executable: `0`;
- both views named the exact Snapshot source and update marker;
- FlightModeAI was not guessed forward from D-007 because its formal Snapshot
  still contradicted the empty patch queue.

## Supported Conclusion

The repair fixes the deterministic rendering defect demonstrated by the sealed
study: Resume and Manifest now agree on one source-backed action or the same
explicit abstention.

This deterministic replay alone does not prove that a fresh Agent will make the
correct full continuation judgment. That separate evidence gate has since
passed for the same three projects; see
[`current-action-repair-sealed-rerun-20260812.md`](current-action-repair-sealed-rerun-20260812.md).
