# FlowGrid Mainline Review — 2026-07-07

## Review Lens

This review uses the updated positioning:

FlowGrid is a local project-state context engine for rationale-heavy, non-coding knowledge work.

## Main Finding

The repository already contains the right foundation.

The gap is that the product language and command surface still describe FlowGrid mostly as a local project protocol and handoff workflow.

The next product step is to make rationale continuity and bounded context explicit.

## Current Strengths

- non-coding knowledge work is already the target
- decision logs already include rationale, rejected options, and reversal conditions
- patch-first workflow already protects human review boundaries
- closeout already extracts decisions, risks, next actions, rationale excerpts, and lessons signals
- handoff already gives agents a resumable summary

## Main Gaps

### Gap 1: Positioning

Current language says project protocol and project state layer.

Next language should say project-state context engine for rationale-heavy non-coding work.

### Gap 2: Context Command

The contract mentions `flg context`, but the CLI does not yet expose a context command.

This should become the next core command.

### Gap 3: Evidence Trace

DECISIONS.md captures rationale, but decisions are not yet fully traceable back through source session and patch metadata.

### Gap 4: Rationale Unit

Decision entries contain rationale fields, but FlowGrid does not yet treat a rationale unit as a first-class object.

## Recommended Next Build

Implement the smallest possible `flg context --mode resume`.

It should read:

1. SNAPSHOT.md
2. recent DECISIONS.md entries
3. PROGRESS.md recent entries
4. state next actions
5. active pending patches

It should output:

```text
.flg/context/startup.md
```

Do not build generic compression, vector search, or a broad memory layer yet.

## Product Rule

History is archived. Reviewed project state enters context. Evidence can be retrieved on demand.
