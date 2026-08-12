# FlowGrid Current State

Last updated: 2026-08-12
Primary branch: `master`
Current code version: `v0.3.0`
Current stage: `v0.4 core validation`

## Product Position

FlowGrid is a local project-state context engine for rationale-heavy, non-coding business projects.

Its job is to let project state, boundaries, judgments, progress, and next actions follow the project directory across AI sessions and hosts, reducing repeated context explanation.

## Current Implemented Surface

- English-first project initialization and localized ledger entries
- `closeout` raw transcript archiving under `.flg/sessions/`
- Batch closeout extraction with pending review patches
- Real-time `capture add/list/show/review`
- Explicit `decision add` for strong user commitments
- `doctor` and `reindex` for cross-file consistency and rebuildable evidence indexes
- Bounded Context Pack, evidence lookup, handoff, onboarding, and host-agnostic Agent Skill
- Optional BIZ meeting handoff import with explicit role-metadata promotion gates
- Advisory evidence-basis quality signal for complete `FRAMING.md` files
- Patch lifecycle parsing that preserves rejected and superseded states
- Explicit, validated decision relations with derived incoming/outgoing trace views
- A machine-readable real-case registry with bounded claims and limitations

## Current Verification

- PR #44 is merged into `master` at merge commit `11c337d`
- The post-merge baseline passes `198` tests
- `python scripts/smoke_test.py` passed
- English-native deterministic gate passed
- Real FlowGrid ledger audit passed with an expected undeclared-evidence-basis warning
- Background review only promotes candidates with explicit user/client attribution; pending candidates, risks, and next actions do not become current truth
- Remote LLM extraction requires explicit per-command consent with `--allow-remote-llm`
- A disposable real-project replay verified that an `Assistant:` proposal remains auditable but cannot enter formal state through the background loop; see [host-like acceptance](../../evals/results/host-like-continuation-safety-20260720.md)
- A Codex host-operated session run archived raw discussion, rejected assistant and unattributed candidates, and preserved formal ledger hashes; see [Codex protocol acceptance](../../evals/results/codex-host-protocol-acceptance-20260721.md)
- `flg onboard` detects missing, current, and drifted host Skills by content hash; an explicit update replaces drifted local instructions
- Five isolated `gpt-5.4` campaign continuations and separately scored results show Context Pack is stable and better than no state, but not superior to clean raw history; see [the stability result](../../evals/results/continuation-stability-20260722.md)
- Three repeated iteration-feedback patterns are now mapped to executable rules and verification in [the closure note](iteration-feedback-20260722.md)
- Five real continuation projects, repeated dogfood failures, customer field use,
  and host acceptance evidence are indexed without being mislabelled as external
  adoption; see [the Case Registry](case-registry.md)

## Evidence Integrity Iteration

The current iteration tightens evidence claims without changing the v0.4
product boundary:

- `decision add` keeps a direct write confirmed, but an omitted source excerpt
  is recorded as `direct_command` with medium authority;
- missing alternatives, rejected reasons, risks, follow-up validation, and
  reversal conditions remain explicitly `Not provided` instead of receiving
  plausible template prose;
- explicit source evidence retains `user_confirmation` and high authority;
- CI detects product files committed after the last `current-state.md` refresh;
- the Case Registry separates real-project evidence from external adoption.
- the full evidence-integrity iteration passes `204` tests, the repository
  smoke flow, and the English-native deterministic gate.

## Goal-Oriented Reliability Integration

PR #42 merged the goal-oriented reliability work into `master` at `73902fc`
without changing the v0.4 product boundary:

- attributed short user confirmations can bind to one unambiguous Assistant
  proposal while ambiguous choices abstain;
- explicit standing user directives remain candidates rather than open
  questions, while routine edit requests are not promoted;
- `doctor` shows mapped runtime branch, HEAD, and dirty state;
- `status` reports pending captures separately from patches;
- `init` preserves the complete creation path in narrow terminals;
- legacy Chinese ledger parsing and durable raw-source provenance fixes are
  included in the merged integration.

The real PBL confirmation transcript now produces one user-attributed candidate
with the original confirmation and inline-code scope preserved. Formal ledger
writes still require the existing review boundary.

The mapped runtime has been fast-forwarded to `73902fc` and verified with
`189 passed`, a passing smoke test, and `flg doctor --strict`. External-host
adoption and release/tag status remain unverified.

## Current Goal

Complete the v0.4 core loop:

1. Raw discussions reliably enter the project state layer.
2. Formal ledger state and evidence indexes can be rebuilt from source files.
3. Real, long, contradictory project histories show lower context-repetition cost for the next Agent.

## Immediate Priorities

1. Validate the merged reliability behavior in continued real-project use.
2. Use the repository `ITERATION_LOG.md` as the canonical product feedback source;
   preserve the Vault log as a legacy archive instead of continuing dual writes.
3. Validate automatic session capture across Codex, ZCode, Hermes, and other supported hosts.
4. Run isolated comparisons between no state, raw history, and FlowGrid Context Pack.
5. Measure repeated explanation, revived rejected directions, candidate/fact confusion, hallucinated project facts, and user correction count.
6. Run one explicitly authorized external-host continuation. Measure raw transcript availability, speaker-label preservation, candidate false positives/negatives, user CLI burden, and fresh-agent recovery.
7. Validate BIZ-to-FLG handoff with a real meeting that has explicit participant metadata. This is one meeting-input path, not the v0.4 product center.
8. Keep `DECISIONS.md` as formal truth and avoid adding new cognitive abstractions until the loop is proven.

## Deferred

- Quadrant tags and protocol routing
- Blindspot pass and unknown-unknown discovery engine
- Multi-source provenance graph beyond the current rebuildable Source Episode index
- Graph database, ABAC, GUI, cloud sync, SaaS, and generic project management features

## Non-Goals

- Do not turn FlowGrid into a generic PM tool.
- Do not optimize for coding-agent workflows.
- Do not present v0.4 as released before real-project validation is complete.

## Reading Order for Future Agents

1. `docs/product/current-state.md`
2. `docs/product/future-direction.md`
3. `docs/product/judgment-capture-pipeline.md`
4. `docs/protocol.md`
5. `ITERATION_LOG.md`
6. `docs/product/iteration-log-governance.md`
