# Known Issue: Merged Patch Remains in Pending State Summary

## Status

Non-blocking.

Observed during the FlowGrid for OpenClaw local demo on Windows 11.

## Symptom

After running:

```bash
flg review --patch <patch-file> --accept-all
printf "y\n" | flg merge --patch <patch-file>
flg status
flg handoff
```

`flg merge` completes successfully and writes formal ledger updates, but `flg status` / `flg handoff` can still report a pending patch.

## Observed Evidence

The actual ledger is correct:

- `DECISIONS.md` contains the accepted decision.
- `PROGRESS.md` contains the merged session progress.
- `.flg/merge_logs/<timestamp>-merge.md` exists.
- `.flg/state.json` marks the patch status as `merged`.

The inconsistency appears because the merged patch can remain in state or patch-summary discovery paths used by `status` and `handoff`.

## Impact

This is a UI / summary-state inconsistency.

It does not block:

- closeout
- review
- merge
- formal ledger updates
- demo recording

## Likely Fix

A minimal fix should do one or both of the following:

1. After `flg merge`, remove the merged patch from `state["pending_patches"]`, or move it to a separate merged history field.
2. Update `flg status` and `flg handoff` so they filter patch records by active pending status, ignoring `merged` patches.

## Reproduction Path

Use the FlowGrid for OpenClaw competition repo:

```powershell
cd <your-workspace>\.openclaw\workspace\flowgrid-openclaw
& "C:\Program Files\Git\bin\bash.exe" scripts/run_local_demo.sh
cd .demo-runtime\ai-collaboration-sharing
flg status
flg handoff
```

## Recommendation

This issue has been addressed in v0.3.0 — `flg status` now filters patches by status, only showing `pending_review` patches in the warning table. Merged/rejected/superseded patches appear in a separate "Closed patches" summary line.

The original reproduction path referenced a specific competition workspace; it has been generalized above.
