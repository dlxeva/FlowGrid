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

For a smaller navigation-first entrypoint, use:

```bash
flg context --mode manifest
```

The generated Continuity Manifest contains identity, the current goal, judgment
statuses and IDs, active-work pointers, source health, and exact commands for
expanding a judgment through the existing `evidence` and `trace` paths. It is a
derived view. The formal ledger and current project files remain authoritative,
and `.flg/context/evidence_index.json` remains the only evidence index.

Default output:

```text
.flg/context/startup.md
```

Manifest output:

```text
.flg/context/manifest.md
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

### 6. Project Continuity Layer stays navigational

The Continuity Manifest is the compact map for deciding what to expand. The
resume pack remains the bounded working payload. `flg evidence <decision-id>`
and `flg trace <decision-id>` supply judgment detail and provenance on demand.
This layer does not load raw sessions, copy full rationale into the manifest,
introduce another index, or become a new fact-writing surface.

### 7. One canonical current action

Resume, Manifest, and Handoff must compile the same single current action.
`SNAPSHOT.md` is the formal current-action authority. The legacy
`.flg/state.json#next_actions` list may corroborate it, but cannot override it
or independently authorize autonomous continuation.

Every generated view must expose:

- status: `current`, `needs_reconciliation`, or `not_defined`;
- the exact action when status is `current`;
- its source and source-updated timestamp;
- how many legacy fallback actions were ignored;
- the reason for selection or abstention.

If the Snapshot action contradicts deterministic project state, the generator
must abstain. The first enforced contradictions are an empty pending-patch
queue paired with “Review pending patches”, and an action repeated in an
explicit completed, superseded, or stale Snapshot section.

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

### 4a. Current Action

The one source-backed action that a receiving Agent may continue. A status other
than `current` means the Agent must reconcile formal state before acting.

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
- Is that action current, or did FlowGrid explicitly abstain pending
  reconciliation?
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
