# FlowGrid Protocol

## What It Is

FlowGrid is a **local project-state context engine** for rationale-heavy, non-coding business projects.

The CLI matters, but the deeper contract is agent-state governance:

- the project directory is the source of truth
- markdown files carry durable project state and its evidence boundaries
- `.flg/` carries runtime, review, pending-change, context, and evidence state
- agents may maintain clear, evidence-backed updates in the background, but
  must preserve provenance, status, and authority instead of hiding uncertainty
- receiving agents should consume a bounded Context Pack instead of raw history dumps

FlowGrid is designed for business-project knowledge workers who need to keep judgments reviewable, traceable, and resumable across long-running AI collaboration.

Product-level references:

- [User Pain Model](./product/user-pain-model.md)
- [Context Pack Contract](./product/context-pack-contract.md)
- [Judgment Status Model](./product/judgment-status-model.md)
- [Eval Set v0](./product/eval-set-v0.md)

## Protocol Goal

The protocol exists to preserve project state without creating false authority.

For rationale-heavy business projects, an agent needs to know:

- what the project is trying to prove
- what has been confirmed
- what is still pending review
- what assumptions are active
- what alternatives were rejected
- what judgments have been superseded
- what risks affect the current plan
- where evidence can be retrieved
- what the next useful action is

## Core Files

### Formal Ledger

- `PROJECT.md`
- `FRAMING.md`
- `DECISIONS.md`
- `SNAPSHOT.md`
- `PROGRESS.md`
- `GOAL_EVOLUTION.md`
- `CONSTRAINTS.md`
- `ANCHORS.md`

These files hold durable project state that a human or agent can inherit, with
status and authority determining how strongly it should be trusted.

### Evidence Basis

`FRAMING.md` may declare an overall evidence basis using the `Evidence Basis`
section. This is an advisory quality signal, not an additional required field.

Supported labels are `direct`, `verified`, `secondary`, and `speculative`.
`flg frame` and `flg audit` warn when the basis is missing, secondary, unclear,
or speculative. A warning does not block exploration, but the agent should not
present the framing as established fact or make a high-risk commitment without
first-hand validation or an explicit conversational commitment.

### Runtime / Review / Context Layer

Inside `.flg/`:

- `CONTRACT.md` — collaboration and agent startup rules
- `state.json` — minimal project runtime state
- `index.json` — index metadata
- `patches/` — pending review updates
- `sessions/` — raw session artifacts
- `memory/` — project-local memory artifacts
- `exports/` — resumable handoff packs
- `context/` — generated context packs and evidence indexes

## State Model

FlowGrid uses a minimal common state layer for compatibility:

- `project_id`
- `project_name`
- `schema_version`
- `flg_version`
- `created_at`
- `updated_at`
- `current_stage`
- `pending_patches`
- `next_actions`

Projects may extend `state.json` with extra fields, but shared commands should depend only on the minimal common layer.

## Judgment State Model

FlowGrid must not flatten every extracted item into a fact.

Important judgments should carry status. The protocol-level statuses are:

- `confirmed` — clearly committed in the conversation or adopted from strong
  source evidence; inheritable as current project truth without a separate FLG
  approval ceremony
- `pending_review` — extracted candidate judgment, not formal truth
- `assumption` — working premise that supports reasoning
- `rejected` — considered and ruled out
- `superseded` — replaced by a newer judgment
- `needs_recheck` — valid only with caution until reviewed again

Extended protocol concepts:

- `contested` — conflicting signals or disagreement
- `stale` — likely expired due to time, client feedback, budget change, external change, or project-stage change

Authority levels may be used when available:

- `high` — explicit user confirmation, client-confirmed feedback, signed-off decision, explicit human review entry, authoritative project document
- `medium` — repeated user preference, meeting note with clear stakeholder signal, strong but unreviewed extraction, project owner hypothesis
- `low` — AI inference, weak raw-session signal, speculative idea, ambiguous fragment

Source types may include:

- `raw_session`
- `closeout_patch`
- `review_action`
- `user_confirmation`
- `client_feedback`
- `data_report`
- `authoritative_doc`
- `ai_inference`

See [Judgment Status Model](./product/judgment-status-model.md).

## Read Model

### Layer 1: Formal Ledger

Merged durable project state in core markdown files.

### Layer 2: Pending Review State

Anything in `.flg/patches/` that has not yet been merged.

### Layer 3: Context Pack

A bounded startup payload generated for the receiving agent.

Target command:

```bash
flg context --mode resume --budget 4000
```

Target output:

```text
.flg/context/startup.md
```

The Context Pack should prefer reviewed state over raw history and should follow the [Context Pack Contract](./product/context-pack-contract.md).

A valid v0 Context Pack should include:

- Project Identity
- Review Object
- Proof Object
- Current Goal
- Confirmed Decisions
- Pending Judgments
- Active Assumptions
- Rejected Alternatives
- Superseded Judgments
- Current Risks
- Next Actions
- Evidence References
- Agent Instructions

## Closeout Input Boundary

`flg closeout` is meant for raw session material, such as:

- meeting notes
- chat transcripts
- discussion drafts
- files under `.flg/sessions/`

It should not re-process already-structured ledger files such as:

- `PROGRESS.md`
- `SNAPSHOT.md`
- `DECISIONS.md`
- `README.md`

Those files already represent interpreted project state. Re-running extraction on them creates second-order noise and can turn status summaries into fake candidate decisions.

## Write Model

FlowGrid uses a patch-first write strategy.

### Low Risk

Examples:

- progress log append
- non-critical notes

These may be written directly.

### Medium Risk

Examples:

- snapshot updates
- framing supplements
- new risks or open questions
- candidate assumptions
- context pack generation

These should generate a patch or a clearly separated generated artifact depending on whether they modify formal project truth.

### High Risk

Examples:

- goal changes
- boundary changes
- proof object changes
- review object changes
- major decision overrides
- status changes from pending to confirmed
- supersession of confirmed decisions

These must retain provenance and status. The host may process them in the
background, but should not silently promote ambiguous items or let them drive
an irreversible external action.

## Evidence Model

FlowGrid should preserve evidence without loading raw history by default.

The intended evidence chain is:

```text
raw session -> closeout patch -> review action -> DECISIONS.md -> Context Pack
```

Future commands:

```bash
flg evidence D-002
flg trace D-002
```

Evidence Trace should show:

- judgment id
- current status
- authority level when available
- source type
- source reference
- source excerpt
- supersession or conflict links when available

## Agent Rules

A FlowGrid-aware agent should follow these protocol rules:

1. Read the Context Pack before acting when it exists.
2. Treat confirmed decisions as inheritable current project truth.
3. Treat pending judgments as candidates.
4. Surface assumptions when using them to support recommendations.
5. Avoid re-suggesting rejected alternatives unless new evidence exists.
6. Avoid relying on superseded judgments as current truth.
7. Surface the boundary when changing goals, boundaries, review objects, proof
   objects, or core judgments; interrupt the user only when an external,
   irreversible action depends on that change.
8. Retrieve evidence when asked why a judgment was made.
9. Keep raw session input raw; do not feed ledger files back into closeout by default.
10. Generate closeout before leaving a meaningful work session.

## Why This Exists

The protocol is designed for a specific problem:

**rationale-heavy business projects lose judgment chains across long-running AI collaboration.**

FlowGrid is meant to reduce:

- repeated re-explanation
- repeated state reconstruction
- document truth ambiguity
- judgment loss across sessions
- pending judgment being mistaken for confirmed truth
- rejected alternatives being revived without new evidence
- old judgments being treated as current state

## Evaluation Requirement

FlowGrid's product claim should be evaluated.

The minimum v0 evaluation compares:

- Mode A: no FLG
- Mode B: raw history
- Mode C: FlowGrid Context Pack

The Context Pack should improve:

- continuity accuracy
- judgment boundary control
- rejected alternative suppression
- revision reasoning
- evidence awareness
- action usefulness
- hallucination resistance

See [Eval Set v0](./product/eval-set-v0.md).

## What It Is Not

FlowGrid is not currently:

- a team project management suite
- a SaaS collaboration platform
- a visual workflow builder
- a full multi-project control plane
- a generic token compression layer
- a vector database
- a coding repo context system

Its center of gravity is:

**single-operator, local-first, rationale-heavy business project state for agent continuation.**
