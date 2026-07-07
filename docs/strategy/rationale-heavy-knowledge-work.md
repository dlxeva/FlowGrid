# Rationale-Heavy Knowledge Work

FlowGrid is for non-coding knowledge workers whose deliverables depend on long reasoning chains.

Target roles include operations, marketing, creative, strategy, research, and solution work.

These users usually do not produce absolute answers. Their work is to make a judgment defensible.

Examples:

- why this campaign direction should be chosen
- why this audience should be prioritized
- why this proposal structure is convincing
- why a past assumption should be reversed
- why a trade-off is acceptable under current constraints

## Core Product Claim

FlowGrid is a local project-state context engine for rationale-heavy, non-coding knowledge work.

It turns messy AI work sessions into reviewed, traceable, and resumable project context.

## Design Implication

FlowGrid should preserve the reasoning chain behind project state:

- what was judged
- why it was judged
- what alternatives were rejected
- what assumptions supported it
- what could reverse it
- where the source evidence lives

## Product Boundary

FlowGrid should stay focused on non-coding project work.

It should not compete with coding-agent repo context systems.

Coding agents already have strong structures such as repos, commits, tests, issues, and PRs.

Non-coding knowledge work often lacks that structure, so FlowGrid provides a local protocol for judgment continuity.

## Immediate Roadmap

1. Reposition README around rationale-heavy non-coding work.
2. Add a first-class context command for bounded agent startup context.
3. Add evidence and trace commands for decisions.
4. Keep raw history archived and load reviewed project state by default.
