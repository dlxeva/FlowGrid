# Evidence Trace v0

## Goal

Make reviewed judgments traceable back to raw sessions and patches.

FlowGrid should preserve not only decisions, but also the reasoning chain behind them.

## Proposed Commands

```bash
flg evidence D-002
flg trace D-002
```

## Evidence Chain

A reviewed decision should be traceable through:

```text
raw session -> closeout patch -> review -> DECISIONS.md -> context pack
```

## Minimum Metadata

For each reviewed decision, keep:

- decision id
- source session path
- source patch path
- source excerpt
- review time
- current status

## Why This Matters

Non-coding knowledge work depends on defensible judgment.

Users need to know why a decision was made, what alternatives were rejected, and when a past judgment should be reversed.

Evidence trace makes the project state auditable instead of becoming another summary layer.
