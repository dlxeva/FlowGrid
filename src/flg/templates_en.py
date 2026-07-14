"""English templates for FlowGrid projects."""

PROJECT_MD = """# {project_name}

## Basic Info

- **Project Type:** {project_type}
- **Client/Sponsor:** {client}
- **Current Stage:** {current_stage}
- **Core Deliverables:** {deliverables}
- **Timeline:** {timeline}
- **Key Constraints:** {constraints}

## Background

{background}

---

*Created: {created_at}*
*Last Updated: {updated_at}*
"""

FRAMING_MD = """# Problem Definition

## Problem Statement

{problem_statement}

## Requirements

### Explicit Requirements

{explicit_requirements}

### Real Needs Hypothesis

{real_needs}

## Goals

{goals}

## Non-Goals

{non_goals}

## User Objects

{user_objects}

## Review Objects

{review_objects}

## Success Criteria

{success_criteria}

## Constraints

{constraints}

## Open Questions

{open_questions}

---

*Created: {created_at}*
*Last Updated: {updated_at}*
"""

DECISIONS_MD = """# Decision Log

> Record why a decision was made, not only what was chosen.
> Capture context, alternatives, rejected paths, and reversal conditions.

<!-- Copy this template for each decision. -->

## D-001 | Decision title

### Decision Date
(date)

### Project Stage
(discovery / planning / execution / retrospective)

### Decision Background
(What happened? Why did this judgment become necessary?)

### Core Question
(What question was this decision answering?)

### Alternatives
A. (option A)
B. (option B)
C. (option C)

### Final Decision
(What was chosen?)

### Decision Rationale
(Why was it chosen? What evidence supports it?)

### Rejected Alternatives
(Why were the other options not chosen?)

### Risk Assessment
(What could go wrong?)

### Follow-up Validation
(How will we validate this judgment?)

### Reversal Conditions
(When should this decision be reconsidered?)

---

*Created: {created_at}*
*Last Updated: {updated_at}*
"""

SNAPSHOT_MD = """# Project Snapshot

**Updated:** {updated_at}

## Current Stage

{current_stage}

## Current Core Goal

{current_goal}

## Current Core Judgments

{judgments}

## Confirmed

{confirmed}

## Unconfirmed

{unconfirmed}

## Current Risks

{risks}

## Next Highest Priority Action

{next_action}

---

*Last Updated: {updated_at}*
"""

GOAL_EVOLUTION_MD = """# Goal Evolution

> Record how the goal changes, not only the final decision.
> For each shift, capture the trigger and affected documents or actions.

<!-- Copy this template for each goal shift. -->

## Goal Shift 001

- **When:** (date)
- **Previous Goal:** (previous goal)
- **New Goal:** (current goal)
- **Trigger:** (event, information, or constraint)
- **Impact:** (affected documents, actions, or boundaries)

---

*Created: {created_at}*
*Last Updated: {updated_at}*
"""

CONSTRAINTS_MD = """# Constraints and Rules

> Record rules, constraints, exceptions, and review triggers.

## Constraint Blocks

<!-- Copy this template for each constraint. -->

### Constraint 001

- **If:** (trigger)
- **Then:** (required action or judgment)
- **Unless:** (exception; write none if not applicable)
- **Owner:** (person or role)
- **Review Trigger:** (when this constraint must be checked again)

---

*Created: {created_at}*
*Last Updated: {updated_at}*
"""

PROGRESS_MD = """# Progress Log

## Document Evolution

> Record who created an important document, when, why, and what it replaced.

<!-- Copy this template for each document evolution entry. -->

### [Document Name]

- **File:** (path)
- **Role:** (document responsibility)
- **Provenance:** internal | external | mixed
- **Created:** (date)
- **Supersedes:** (replaced file, or none)
- **Why:** (why this document exists)
- **Status:** active | superseded | archived

---

*Created: {created_at}*
*Last Updated: {updated_at}*
"""

CONTRACT_MD = """# FlowGrid Contract

## Core Rules

1. The project directory is the highest-priority source of truth.
2. AI memory is temporary cache only; verify project facts against files.
3. Separate formal ledger facts from pending patch judgments.
4. Never promote pending judgments to confirmed decisions without review.
5. Never revive rejected or superseded directions without new evidence.
6. Close each meaningful session with flg closeout.
7. Use patches for medium- and high-risk changes.
8. Read the Context Pack before resuming work.

## Startup Sources

1. SNAPSHOT.md
2. Recent entries in DECISIONS.md
3. next_actions in .flg/state.json

## Status Vocabulary

- confirmed
- pending_review
- rejected
- superseded
- needs_recheck
"""

RATIONALE_TRAIL_MD = """# Rationale Trail

> Record disputes, uncertainty, external information, and changes in reasoning.
> DECISIONS.md records the commitment point; this file records the reasoning path.

---

*Created: {created_at}*
*Last Updated: {updated_at}*
"""

LESSONS_LEARNED_MD = """# Lessons Learned

> Record whether earlier judgments were validated by outcomes.
> DECISIONS.md records why the choice was made; this file records what happened.

---

*Created: {created_at}*
*Last Updated: {updated_at}*
"""

ANCHORS_MD = """# Authoritative Anchors

> List files that define the current project truth and their responsibilities.

---

*Created: {created_at}*
*Last Updated: {updated_at}*
"""

DOCS_README_MD = """# Project Materials

Use this directory for research, meeting notes, references, and other working
materials. These files are evidence and context, not formal project truth.
"""
