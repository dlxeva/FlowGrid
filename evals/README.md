# FlowGrid Eval Scenarios

FlowGrid's product claim is that a bounded Context Pack helps an agent resume rationale-heavy business projects better than raw history or no project state.

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

## Current v0 Scenario

- `campaign-proposal/`: marketing campaign proposal with a rejected KOL-heavy plan and a later stakeholder request to revisit KOL.

## Product Principle

The eval set is part of the product.

If Context Pack does not improve agent continuation under evaluation, FlowGrid's core claim has not been proven yet.
