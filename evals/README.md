# FlowGrid Eval Scenarios

FlowGrid's hypothesis is that a bounded Context Pack helps an agent resume
rationale-heavy business projects better than no state and provides a smaller,
more legible continuation surface than raw history. It must be evaluated per
scenario; Context Pack is not assumed to outperform a clean raw history.

This directory contains scenario fixtures for evaluating that claim.

## Evaluation Modes

Each scenario should support three modes:

- Mode A: no FLG state
- Mode B: raw history
- Mode C: FlowGrid Context Pack

## Scoring Dimensions

Each scenario is scored on seven dimensions, 0-2 points each:

1. Continuity Accuracy
2. Judgment Boundary Control
3. Rejected Alternative Suppression
4. Revision Reasoning
5. Evidence Awareness
6. Action Usefulness
7. Hallucination Resistance

Maximum score per scenario: 14.

## Scenario Structure

Each scenario directory should contain:

```text
scenario.md
raw-session.md
golden-decisions.md
rejected-alternatives.md
expected-context-pack.md
resume-prompt.md
scoring-notes.md
```

## Current v0 Scenarios

- `campaign-proposal/`: marketing campaign proposal with a rejected KOL-heavy plan and a later stakeholder request to revisit KOL.
- `client-solution-proposal/`: client proposal narrowed from broad AI transformation to an operational pilot, then challenged by ambition pressure.
- `operations-mechanism-design/`: activity mechanism simplified after execution review, then challenged by a request to restore points and ranking.

## Product Principle

The eval set is part of the product.

If Context Pack does not improve agent continuation under evaluation, FlowGrid's core claim has not been proven yet.

See the first five-run independently scored result in
[`results/continuation-stability-20260722.md`](results/continuation-stability-20260722.md).
