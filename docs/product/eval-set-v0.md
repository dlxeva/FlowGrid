# FlowGrid Eval Set v0

## Purpose

FlowGrid needs an evaluation layer before it becomes a serious agent-state tool.

The core product claim is that FlowGrid helps agents resume rationale-heavy business projects without losing judgment chains.

That claim must be testable.

## Evaluation Question

Does a FlowGrid Context Pack help a receiving agent continue a project better than raw chat history or no project state?

## Evaluation Modes

### Mode A — No FLG

The receiving agent gets only a short user prompt such as:

```text
Continue this project from where we left off.
```

### Mode B — Raw History

The receiving agent gets a long transcript or meeting history.

### Mode C — FlowGrid Context Pack

The receiving agent gets only the FlowGrid Context Pack and can request evidence when needed.

## Expected Result

Mode C should perform better on project continuity, judgment boundary control, and reasoning traceability.

Mode B may contain more raw information, but should be noisier and easier to misread.

## Evaluation Dimensions

### 1. Continuity Accuracy

Can the agent correctly identify:

- current goal
- current stage
- next action
- current deliverable
- review object
- proof object

### 2. Judgment Boundary Control

Can the agent distinguish:

- confirmed decisions
- pending judgments
- assumptions
- rejected alternatives
- superseded judgments

### 3. Rejected Alternative Suppression

Does the agent avoid re-suggesting rejected alternatives unless new evidence exists?

### 4. Revision Reasoning

Can the agent explain why a prior judgment changed?

### 5. Evidence Awareness

Can the agent identify where evidence would be retrieved from?

### 6. Action Usefulness

Does the agent propose the right next action instead of restarting discovery?

### 7. Hallucination Resistance

Does the agent avoid inventing decisions, facts, stakeholders, or evidence not present in the pack?

## Scoring Rubric

Each dimension can be scored 0-2.

### 0 — Failed

The agent misses the project state, confuses status, invents facts, or restarts from scratch.

### 1 — Partial

The agent gets some project state right but misses key status distinctions or gives generic next steps.

### 2 — Good

The agent correctly inherits state, respects judgment boundaries, and continues from the right point.

Maximum score per scenario: 14.

## Required Scenarios

### Scenario 1 — Campaign Proposal

Project type:

Marketing campaign.

Core tension:

The team previously rejected KOL-heavy execution because budget and conversion proof were weak. Later, a stakeholder asks to revisit KOL.

Expected agent behavior:

- recognize that KOL was previously rejected
- ask what new evidence changes the decision
- avoid treating stakeholder interest as confirmed reversal
- suggest a bounded test if appropriate

### Scenario 2 — Client Solution Proposal

Project type:

Client-facing solution proposal.

Core tension:

The client originally asked for a broad AI transformation proposal, but the project narrowed to one operational pilot.

Expected agent behavior:

- preserve the narrowed scope
- explain why the broad version was dropped
- avoid expanding back into generic AI transformation
- prepare next proposal iteration around pilot proof

### Scenario 3 — Operations Mechanism Design

Project type:

Operations mechanism or activity system.

Core tension:

The team designed rules for an activity, then found the rules were too complex for execution.

Expected agent behavior:

- identify the current mechanism constraints
- distinguish old rule design from revised direction
- suggest simplification without losing goal
- preserve review triggers

### Scenario 4 — Strategy Deck Revision

Project type:

Strategy or business deck.

Core tension:

The first deck explained too much background and failed to make the core judgment sharp. The revised direction is to make the proof object clearer.

Expected agent behavior:

- identify proof object
- explain why the previous structure was weak
- propose deck changes that support the current judgment
- avoid generic slide polishing

### Scenario 5 — Project Retrospective

Project type:

Business project retrospective.

Core tension:

The project outcome is mixed. Some decisions were right, some were wrong, and the user wants reusable lessons.

Expected agent behavior:

- separate outcome from reasoning quality
- identify which assumptions failed
- preserve lessons learned without rewriting history
- suggest what should change next time

## Eval Artifact Structure

Each scenario should eventually include:

```text
scenario.md
raw-session.md
golden-decisions.md
rejected-alternatives.md
expected-context-pack.md
resume-prompt.md
scoring-notes.md
```

Suggested location:

```text
evals/scenarios/<scenario-name>/
```

## Example Resume Prompt

```text
You are entering this FlowGrid project as a new agent.
Read the provided context and continue the project.
First, state what is confirmed, what is pending, what has been rejected, and what the next useful action is.
Then produce the next artifact requested by the user.
```

## Minimum v0 Eval Run

For v0.3, run each scenario in Mode A, Mode B, and Mode C.

Record:

- score per dimension
- total score
- failure notes
- whether rejected alternatives were repeated
- whether pending judgments were treated as confirmed
- whether the agent invented project facts

## Success Threshold

FlowGrid Context Pack should outperform raw history on at least 4 of 5 scenarios.

It should especially improve:

- judgment boundary control
- rejected alternative suppression
- action usefulness
- hallucination resistance

## What This Eval Should Prevent

This eval should prevent FlowGrid from becoming:

- a nicer summary generator
- a generic memory folder
- a context dump tool
- a decision log that cannot prove usefulness

## Product Principle

If FlowGrid cannot improve agent continuation under evaluation, the product claim is not yet proven.

The eval set is part of the product, not an afterthought.
