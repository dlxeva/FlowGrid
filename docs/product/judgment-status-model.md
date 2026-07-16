# FlowGrid Judgment Status Model

## Purpose

FlowGrid preserves judgment chains for rationale-heavy, non-coding business projects.

Because these projects evolve through reversals, feedback, assumptions, and contested trade-offs, FlowGrid must not flatten every extracted item into a fact.

The Judgment Status Model defines how a project judgment should be represented before it enters Context Pack, Evidence Trace, or DECISIONS.md.

## Core Problem

The risk is not only forgetting.

The risk is making weak, stale, or superseded judgments look authoritative.

A useful project-state system must distinguish fact, judgment, assumption, preference, pending review, and obsolete state without turning every distinction into a user-facing approval step.

## Status Values

### confirmed

A decision or project state item that is clearly committed in the conversation
or adopted from strong source evidence. This does not require a separate FLG
approval prompt; the host still preserves provenance and authority.

Agents may inherit it as current project truth unless a newer item supersedes it.

### pending_review

A candidate judgment extracted from a session or patch.

Agents may mention it, but must not treat it as confirmed truth.

### assumption

A working premise that supports project reasoning but has not been fully verified.

Agents should surface assumptions when making recommendations.

### rejected

An alternative that was considered and ruled out.

Agents should not re-suggest it unless new evidence is present.

### superseded

A judgment that was once valid but has been replaced by a newer judgment.

Agents should not rely on it as current truth.

### contested

A judgment that has conflicting signals or disagreement.

Agents should surface the conflict and retrieve evidence. They should interrupt
only when an irreversible external action depends on the contested item.

### stale

A judgment that may have expired due to time, external change, client feedback, budget change, or project-stage change.

Agents should surface the recheck boundary before relying on it for a material
action; routine ledger maintenance can continue in the background.

### needs_recheck

A judgment explicitly marked for future review.

Agents may use it only with caution and should surface the review trigger.

## Authority Levels

Status says what kind of state an item is.

Authority says how much weight the agent should give it.

### high

Examples:

- explicit user confirmation
- client-confirmed feedback
- signed-off decision
- explicit human review entry
- authoritative project document

### medium

Examples:

- repeated user preference
- meeting note with clear stakeholder signal
- strong but unreviewed closeout extraction
- project owner hypothesis

### low

Examples:

- AI inference
- weak signal from raw discussion
- speculative idea
- ambiguous meeting fragment

## Source Types

Every important judgment should eventually reference its source type.

Suggested source types:

- raw_session
- closeout_patch
- review_action
- user_confirmation
- client_feedback
- data_report
- authoritative_doc
- ai_inference

## Recommended Item Shape

```yaml
id: D-002
status: confirmed
authority: high
source_type: user_confirmation
source_ref: .flg/patches/closeout-xxx.patch.md
evidence_ref: E-002
supersedes: []
conflicts_with: []
reversal_conditions:
  - if client rejects the budget assumption
review_trigger:
  - after next client feedback
```

## Relationship Types

### supersedes

Judgment A replaces Judgment B.

Example:

```text
D-004 supersedes D-001
```

### conflicts_with

Judgment A conflicts with Judgment B and requires review.

Example:

```text
D-005 conflicts_with D-003
```

### depends_on

Judgment A depends on an assumption, document, constraint, or prior decision.

Example:

```text
D-006 depends_on A-002
```

### derived_from

Judgment A was extracted from a source item.

Example:

```text
D-007 derived_from session-20260707.md
```

## Agent Rules

A FlowGrid-aware agent should follow these rules:

1. Treat `confirmed` as inheritable current project truth.
2. Treat `pending_review` as a candidate, not a fact.
3. Surface `assumption` when using it to support a recommendation.
4. Avoid re-suggesting `rejected` alternatives unless new evidence exists.
5. Never rely on `superseded` items as current truth.
6. Surface `contested` items with their conflicting evidence; interrupt the user
   only if the next external action depends on resolving the conflict.
7. Warn before relying on `stale` or `needs_recheck` items.
8. Prefer high-authority evidence when judgments conflict.

## Context Pack Implication

The Context Pack must not list judgments as plain bullets.

It should group or annotate them by status:

- confirmed decisions
- pending judgments
- active assumptions
- rejected alternatives
- superseded judgments
- stale or needs-recheck items

## Evidence Trace Implication

Evidence Trace should show:

- what judgment is being inspected
- current status
- authority level
- source type
- source reference
- source excerpt
- related supersession or conflict links

## v0 Implementation Scope

v0 should implement only the minimum needed statuses:

- confirmed
- pending_review
- assumption
- rejected
- superseded
- needs_recheck

`contested` and `stale` can be protocol-level concepts first, then added after dogfood evidence.

## Success Criteria

The model succeeds if an agent can answer:

- Can I inherit this judgment?
- Is this a fact, a judgment, or an assumption?
- What evidence and authority support this judgment?
- Was this rejected or superseded?
- What could reverse it?
- What source supports it?

## Product Principle

FlowGrid should preserve reasoning without creating false authority.

A good judgment ledger is not just memory.

It is controlled epistemic state for long-running AI collaboration.
