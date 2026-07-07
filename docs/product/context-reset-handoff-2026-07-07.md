# FlowGrid Context Reset Handoff — 2026-07-07

## Purpose

This document records the project-level pause point before switching to a new working conversation.

The current conversation has accumulated enough context that the next step should be driven from this handoff and the repository state, not from continued chat memory.

## Current High-Level Judgment

FlowGrid has not strategically drifted.

The current product direction is still correct:

**FlowGrid is a local project-state context engine for rationale-heavy, non-coding business projects.**

The core risk is now execution drift:

**concept expansion is moving faster than validation.**

The immediate next phase should stop adding new conceptual layers or new eval scenarios and validate the minimal loop that already exists.

## Current Product Definition

FlowGrid serves business-project-oriented, non-coding knowledge workers who must maintain defensible judgment chains over time.

It serves a work structure, not a job title.

The work structure is:

- long-running business projects
- fuzzy goals and changing assumptions
- repeated judgment, revision, explanation, and handoff
- deliverables such as proposals, campaigns, mechanism plans, strategy decks, and retrospectives
- a need to preserve what was judged, why, what was rejected, what is pending, and what has been superseded

## What Has Been Added Recently

### Product / Strategy Docs

- `docs/product/user-pain-model.md`
- `docs/product/v0.3-plan.md`
- `docs/product/context-pack-contract.md`
- `docs/product/judgment-status-model.md`
- `docs/product/eval-set-v0.md`
- `docs/product/context-reset-handoff-2026-07-07.md`

### Protocol Docs

- `docs/protocol.md` aligned to project-state context engine framing
- `docs/host-usage.md` aligned to AI host usage and judgment-status rules

### Functional Code

- `src/flg/commands/context.py`
  - implements deterministic `flg context --mode resume --budget 4000`
  - outputs `.flg/context/startup.md`
  - does not load raw sessions by default
  - does not use vector search, embeddings, or generic compression

- `src/flg/commands/evidence.py`
  - implements `flg evidence <decision-id>`
  - reads `.flg/context/evidence_index.json`
  - falls back to `DECISIONS.md` when no evidence index exists

- `src/flg/commands/review.py`
  - now writes `.flg/context/evidence_index.json` when accepted decisions are reviewed
  - stores status, authority, source type, source patch, source session, source excerpt, review time, rationale, rejected alternatives, and reversal conditions

- `src/flg/cli.py`
  - registers `flg context`
  - registers `flg evidence`

- `scripts/smoke_test.py`
  - now runs closeout, review, evidence, context, handoff, and status

### Eval Fixtures

- `evals/README.md`
- `evals/runbook.md`
- `evals/scenarios/campaign-proposal/`
- `evals/scenarios/client-solution-proposal/`
- `evals/scenarios/operations-mechanism-design/`

Current eval scenarios are designed around the same failure pattern:

1. A prior direction was rejected or narrowed.
2. A later stakeholder input pressures the project to reopen that direction.
3. The receiving agent must preserve confirmed state, pending state, rejected alternatives, and proof object boundaries.

## What Is Working Conceptually

The current work is coherent with the main product claim.

The strongest current product chain is:

```text
raw session
-> closeout patch
-> review
-> decision ledger
-> evidence index
-> context pack
-> resumed agent
-> eval comparison
```

This chain directly serves the core pain:

**The judgment chain cannot be maintained across long-running AI collaboration.**

## Where We May Be Starting to Drift

### 1. Eval fixture expansion before eval execution

Three eval scenarios now exist, but no manual A/B/C eval result has been recorded yet.

Do not add the fourth and fifth scenarios until at least one or two existing scenarios have been manually evaluated.

### 2. Code added before local validation

`flg context` and `flg evidence` have been implemented and added to smoke test, but local smoke test has not yet been run in this chat.

This must be validated before adding more commands.

### 3. README command table is behind implementation

The README command table still needs to list:

- `flg context --mode resume`
- `flg evidence <decision-id>`

It should not imply `flg trace` is implemented yet.

### 4. `flg trace` should stay deferred

`flg trace` appears in planning docs as a future Phase 4 command, but only `flg evidence` has been implemented.

Do not implement trace until evidence and context pass smoke test and at least one eval has been run.

## Immediate Next Actions

The next conversation should not continue adding concepts.

The next conversation should execute this stabilization loop:

### Step 1 — Pull and run local validation

Run locally:

```bash
python scripts/smoke_test.py
pytest -q
```

Expected checks:

- `flg context` command resolves
- `.flg/context/startup.md` is created
- `flg review --accept-all` creates `.flg/context/evidence_index.json`
- `flg evidence D-002` works in smoke test
- no Typer argument issue
- no brittle path issue on Windows

### Step 2 — Fix smoke test failures before new features

If smoke test fails, fix only the failure path.

Do not add new product functionality while smoke test is failing.

### Step 3 — Update README command table

Add implemented commands:

- `flg context --mode resume` — Generate bounded agent startup Context Pack
- `flg evidence <decision-id>` — Show evidence behind a reviewed decision

Make clear that `flg trace` is future work.

### Step 4 — Run one manual eval

Start with:

```text
evals/scenarios/campaign-proposal/
```

Run Mode A, Mode B, and Mode C according to `evals/runbook.md`.

Record the result in a new file, suggested path:

```text
evals/results/campaign-proposal-manual-001.md
```

### Step 5 — Let eval results change the product

After manual eval, inspect whether Mode C actually improves:

- continuity accuracy
- judgment boundary control
- rejected alternative suppression
- revision reasoning
- evidence awareness
- action usefulness
- hallucination resistance

If Mode C does not clearly beat raw history, adjust Context Pack Contract or generator before adding more scenarios.

## Current Stop Rule

Do not add more eval scenarios, templates, or commands until all of these are true:

- smoke test passes locally
- README command table matches implemented CLI
- one manual eval result is recorded
- the first eval result has been reviewed for product implications

## Suggested Prompt for Next Conversation

Use this in the next ChatGPT conversation:

```text
继续推进 FlowGrid。先读取 GitHub 主仓 `dlxeva/FlowGrid` 的 `docs/product/context-reset-handoff-2026-07-07.md`，不要继续扩展概念。按 handoff 执行稳定闭环：先本地 smoke test 验证 `flg context` 和 `flg evidence`，再更新 README 命令表，然后跑 `campaign-proposal` 的 Mode A/B/C 手工 eval 并记录结果。
```

## One-Line Summary

FlowGrid has not gone off direction; it now needs validation discipline before further expansion.
