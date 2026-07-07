# Context Pack v0

## Goal

Create a bounded startup context for AI agents working on FlowGrid projects.

The first version should be deterministic and local-first.

## Proposed Command

```bash
flg context --mode resume --budget 4000
```

## Inputs

Default priority:

1. SNAPSHOT.md
2. recent reviewed decisions from DECISIONS.md
3. PROGRESS.md recent entries
4. next actions from state.json
5. active pending patches
6. evidence references

Raw sessions should not enter the startup context by default.

## Output

A markdown context pack that an agent can read before continuing a project.

Suggested output location:

```text
.flg/context/startup.md
```

## Rules

- confirmed state outranks pending state
- reviewed decisions outrank unreviewed suggestions
- current project state outranks old history
- every compressed judgment should keep a source reference when possible
- raw sessions are retrieved only when needed

## Non-Goals

- no generic token compression
- no vector database
- no coding repo context system
- no SaaS workspace

## Why This Matters

Rationale-heavy work creates long histories, but agents should not read the entire history on every restart.

Context Pack turns the current project state into a bounded, auditable startup payload.
