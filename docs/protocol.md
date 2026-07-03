# FlowGrid Protocol

## What It Is

FlowGrid is a **local project protocol** for non-coding knowledge work.

The CLI matters, but it is not the whole product. The deeper contract is:

- the project directory is the source of truth
- markdown files carry the durable working state
- `.flg/` carries runtime, review, and pending-change state
- agents may propose updates, but not silently rewrite core judgment

This makes FlowGrid closer to a local project state layer than to a note-taking format or a generic prompt pack.

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

These files hold the durable project state a human or agent should read before acting.

### Runtime / Review Layer

Inside `.flg/`:

- `CONTRACT.md` — collaboration rules
- `state.json` — minimal project runtime state
- `index.json` — index metadata
- `patches/` — pending review updates
- `sessions/` — session artifacts
- `memory/` — project-local memory artifacts
- `exports/` — resumable handoff packs

## State Model

FlowGrid now uses a minimal common state layer for compatibility:

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

## Two-Layer Read Model

When resuming a project, an agent should read:

### Layer 1: Formal Ledger

The merged, durable project state in core markdown files.

### Layer 2: Pending Review State

Anything in `.flg/patches/` that has not yet been merged.

This is why FlowGrid is not just “files plus a CLI”. It is a protocol for handling:

- confirmed facts
- pending facts
- review boundaries
- resumable state

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

These should generate a patch for review.

### High Risk

Examples:

- goal changes
- boundary changes
- major decision overrides

These must stay reviewable and should not be silently merged.

## Why This Exists

The protocol is designed for a specific problem:

**non-coding project work often loses its state between sessions, tools, and agents.**

FlowGrid is meant to reduce:

- repeated re-explanation
- repeated state reconstruction
- document truth ambiguity
- judgment loss across sessions

## What It Is Not

FlowGrid is not currently:

- a team project management suite
- a SaaS collaboration platform
- a visual workflow builder
- a full multi-project control plane

Its center of gravity is still:

**single-operator, local-first, resumable project state for judgment-heavy work.**
