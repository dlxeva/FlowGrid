# Dev Log 002: Review Must Happen Before a Candidate Reaches Startup Context

## What happened

During a controlled host replay, `closeout` generated three low-confidence
candidate decisions. The later review correctly rejected them.

But the damage had already happened: `closeout` had refreshed `SNAPSHOT.md`
before review. The rejected candidates and their suggested next actions were
already present in the next Agent's startup material.

## Why it mattered

Pending state is useful. Unreviewed state presented as current project context
is unsafe.

An Agent receiving that startup file could reasonably treat the candidates as
facts, even though the system would later reject their patch. A patch-first
workflow is not sufficient if a pre-merge side effect bypasses the patch.

## What changed

`closeout` now produces candidate state only. It does not modify the formal
`SNAPSHOT.md`.

The formal snapshot is refreshed only after `merge` accepts reviewed changes.
The merge step also records the patch lifecycle in its file header and state
metadata, so a closed patch does not reappear in a later handoff.

## Evidence

The controlled lifecycle test ran:

```text
closeout -> autonomous review -> discard -> handoff
```

The rejected candidates did not change the formal snapshot and did not appear
as pending work in the handoff. Repository regression tests and the smoke flow
covered the same write boundary.

## What remains open

This proves the FlowGrid write path can preserve the boundary. It does not mean
every AI host exports raw conversations automatically. Hosts still need to
preserve clean source material before `closeout` can create an auditable
candidate.
