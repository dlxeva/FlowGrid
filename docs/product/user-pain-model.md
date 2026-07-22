# FlowGrid User Pain Model

## Current Decision

FlowGrid should not define its primary users by job title alone.

The core ICP is defined by work structure:

**business-project-oriented, non-coding knowledge workers who use multiple AI agents or models and must maintain defensible judgment chains over time.**

Typical roles include operations, marketing, strategy, growth, creative, solution, research-oriented content work, independent consultants, and small-team owners.

These roles often overlap. A marketing lead writes proposals. An operations lead writes mechanism designs. A strategy lead writes campaign logic. A small-team owner does all of them.

FlowGrid should serve the shared work structure, not separate these roles into artificial user groups.

## Core ICP

### Business Project Knowledge Workers

They own fuzzy business projects and move them across different AI agents or models while repeatedly clarifying, judging, revising, explaining, and handing off project state.

Typical work:

- campaign proposals
- client proposals
- activity mechanisms
- growth plans
- strategy decks
- project retrospectives
- content systems
- product-side business planning

Their work is not just producing a document. Their work is making a judgment chain defensible.

## Adjacent ICP

### Research and Creative Knowledge Workers

They also depend on long reasoning chains, but their rhythm is usually more individual and less project-management heavy.

Typical work:

- topic research
- long-form writing
- creative direction
- course design
- method development
- personal research projects

This group is relevant, but the first product language should stay anchored on business-project work.

## Task Modes

FlowGrid should classify use cases by task mode instead of job title.

### 1. Proposal Persuasion

Core question:

Why does this proposal make sense?

Typical artifacts:

- proposal
- brief
- campaign plan
- strategy deck
- client presentation

Main pain:

The final deck exists, but the reasoning chain behind it is scattered across chats, drafts, meetings, and feedback.

### 2. Mechanism Progression

Core question:

How does this project keep moving under real constraints?

Typical artifacts:

- activity mechanism
- operations plan
- execution rhythm
- project status update
- retrospective

Main pain:

Rules, constraints, risks, and changes are discussed repeatedly but not maintained as current project state.

### 3. Judgment Revision

Core question:

Why should a previous judgment be changed now?

Typical artifacts:

- revision note
- updated proposal
- post-feedback version
- retrospective finding
- decision update

Main pain:

Old judgments, new information, pending assumptions, and rejected directions get mixed together.

## Surface Pain

Users may describe the pain as:

- I have to explain the background to AI every time.
- AI keeps suggesting directions we already rejected.
- I cannot remember why we changed the proposal.
- The latest document exists, but the rationale is buried.
- There are too many versions and no clear current truth.
- When challenged by a client or boss, I need to search old chats again.

## Deep Pain

The deeper problem is:

**The judgment chain cannot be maintained across long-running, multi-agent AI collaboration.**

The project history grows, but the current project state becomes less trustworthy.

Raw discussion, candidate judgment, confirmed decision, reversed conclusion, open question, and current state are not separated.

The user may deliberately select different models for complex reasoning,
implementation, long-running work, lower cost, or remaining subscription
capacity. Without a shared project state, every agent reconstructs the project
differently.

## What FlowGrid Must Preserve

FlowGrid must preserve:

- what was judged
- why it was judged
- what alternatives were rejected
- what assumptions supported it
- what could reverse it
- where the source evidence lives
- what is current truth
- what is pending review
- what has been superseded

## What FlowGrid Should Not Solve First

FlowGrid should not start with:

- generic AI memory
- generic token compression
- generic meeting notes
- enterprise project management
- model routing or agent-team management
- coding repo context
- vector database search
- high-compliance professional workflows

These may be adjacent, but they are not the first wedge.

## Product Rule

FlowGrid serves a work structure, not a job title.

The work structure is:

**long-running, fuzzy, rationale-heavy business projects where the user must keep judgments reviewable, traceable, and resumable.**
