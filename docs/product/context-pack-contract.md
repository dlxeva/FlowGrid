# FlowGrid Context Pack Contract

## Purpose

The Context Pack is the controlled startup payload for an AI agent entering a FlowGrid project.

It is not a general summary.

It is not a raw history dump.

It is an agent-readable state contract that tells the agent what project state can be inherited, what is pending, what has been rejected, and what must be treated carefully.

## Product Definition

FlowGrid is a local project-state context engine for rationale-heavy, non-coding business projects.

The Context Pack is the first concrete artifact that turns this definition into an agent-consumable contract.

## Command Target

```bash
flg context --mode resume --budget 4000
```

Default output:

```text
.flg/context/startup.md
```

## Contract Principles

### 1. Reviewed state first

The Context Pack should prefer reviewed project state over raw discussion.

Raw sessions should not enter the pack by default.

### 2. Status must be explicit

The agent must be able to distinguish:

- confirmed decisions
- pending judgments
- assumptions
- rejected alternatives
- superseded judgments
- stale or needs-recheck items

### 3. Context is not authority by itself

A context item is only as strong as its status and evidence.

The pack must avoid making assumptions look like facts.

### 4. Business project intent must be visible

For rationale-heavy business projects, the agent must know what the work is trying to prove.

The pack should include:

- review object: who or what will judge the work
- proof object: what the project must make believable
- current deliverable type
- judgment boundaries

### 5. Evidence remains retrievable

The pack should include evidence references, not full source history.

The agent should be able to retrieve evidence on demand through `flg evidence`
and `flg trace` commands.

## Required Sections

A valid v0 Context Pack should include these sections.

### 1. Project Identity

Minimum fields:

- project name
- project type
- current stage
- client or sponsor when available
- updated timestamp

### 2. Review Object

Who or what evaluates the work.

Examples:

- client stakeholder
- internal business owner
- campaign reviewer
- strategy reviewer
- future self
- project team

### 3. Proof Object

What the work must make believable.

Examples:

- why this campaign direction should be chosen
- why this activity mechanism can work
- why this proposal answers the client problem
- why this strategy should replace the old one

### 4. Current Goal

The highest-level active goal.

This should come from `FRAMING.md`, `SNAPSHOT.md`, or reviewed project state.

### 5. Confirmed Decisions

Reviewed decisions that the agent may inherit.

Each item should include:

- decision id
- title or summary
- rationale
- rejected alternatives when available
- reversal conditions when available
- evidence reference when available

### 6. Pending Judgments

Candidate decisions or pending patches that are not yet formal truth.

The agent may reason with them, but must not treat them as confirmed.

### 7. Active Assumptions

Assumptions currently supporting the project.

Each assumption should have one of these states:

- unverified
- user-stated
- evidence-backed
- needs-recheck

### 8. Rejected Alternatives

Directions that were considered and rejected.

The agent should not re-suggest them unless new evidence is present.

### 9. Superseded Judgments

Past judgments that have been replaced.

The agent should not treat them as current truth.

### 10. Current Risks

Risks that affect goal, delivery, stakeholder alignment, constraint fit, or judgment integrity.

### 11. Next Actions

Concrete next actions the project should take.

### 12. Evidence References

References to source sessions, patches, or review logs.

Full raw source content should stay outside the pack unless explicitly requested.

### 13. Agent Instructions

Operational instructions for the receiving agent.

Minimum instructions:

- do not treat pending judgments as confirmed decisions
- do not revive rejected alternatives without new evidence
- cite decision ids when relying on confirmed decisions
- surface the boundary when changing goal, boundary, or core judgment; interrupt
  the user only when an irreversible external action depends on that change
- retrieve evidence when asked why a judgment was made

## Example Skeleton

```markdown
# FLG Context Pack

## Project Identity
- Project: ...
- Stage: ...
- Updated: ...

## Review Object
...

## Proof Object
...

## Current Goal
...

## Confirmed Decisions
### D-001 | ...
- Status: confirmed
- Rationale: ...
- Rejected alternatives: ...
- Reversal conditions: ...
- Evidence: E-001

## Pending Judgments
...

## Active Assumptions
...

## Rejected Alternatives
...

## Superseded Judgments
...

## Current Risks
...

## Next Actions
...

## Evidence References
...

## Agent Instructions
...
```

## Validation Criteria

A Context Pack is valid if a receiving agent can answer:

- What is this project trying to prove?
- What has already been confirmed?
- What is still pending review?
- What should not be repeated without new evidence?
- What old judgment has been superseded?
- What should happen next?
- Where can evidence be retrieved?

## Non-Goals for v0

The v0 Context Pack should not include:

- embedding retrieval
- vector search
- generic compression
- automatic truth ranking
- full raw transcript loading
- multi-project control plane

## Engineering Priority

Implement the contract before optimizing the pack.

The first version can be deterministic and conservative.

A smaller trustworthy pack is better than a larger fluent summary.
