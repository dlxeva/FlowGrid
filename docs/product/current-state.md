# FlowGrid Current State

Last updated: 2026-09-19
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
- Read-only judgment impact analysis that derives revalidation candidates while
  preserving the owner gate
- Optional filesystem-Markdown knowledge-source continuity (currently exposed
  through the compatibility command `flg wiki`), explicit active-delivery
  contracts, and a Source-backed Work View
- A machine-readable real-case registry with bounded claims and limitations

## Current Verification

- Public `master` is at merge commit `fcac7b4` (PR #54). It includes PR #51's
  runtime freshness, read-only judgment impact, knowledge-source adapter
  boundary, the rebased Windows hardening, explicit current-action dates, and
  deterministic Chinese reported-speech attribution guards.
- Windows Python 3.12 and Linux Python 3.10/3.11/3.12 passed before PR #52
  merged. Native drive paths, MSYS paths, deterministic Wiki ordering, GBK-safe
  first-run output, and capture-ID collision protection have current regressions.
- The explicit current-action date contract adds optional `Review Date` and
  `Valid Until` fields. Due, expired, duplicate, or malformed declared dates
  make generated continuation views abstain and make `doctor --strict` fail;
  ordinary prose is never scanned for inferred deadlines. The candidate passes
  `276` local tests and forced source-tree smoke. PR #53 passes Linux Python
  3.10/3.11/3.12 and Windows Python 3.12 CI.
- The Chinese attribution guard distinguishes the transcript speaker
  from a third party named inside the utterance. It abstains on same-sentence,
  cross-sentence, quoted-first-person, and customer-requirement reports while
  preserving direct client speech and explicit owner adoption. The candidate
  passes `282` local tests and forced source-tree smoke. PR #54 passes Linux
  Python 3.10/3.11/3.12 and Windows Python 3.12 CI.
- A read-only replay over the real FlowGrid ledger covered 48 decisions and all
  3 declared relation edges. Four changed-decision roots produced five review
  candidate instances with zero obvious false positives or missing candidates
  under a frozen material-change interpretation. This is a bounded graph result,
  not a general false-positive rate; see the
  [real-ledger replay](../../evals/results/judgment-impact-real-replay-20260919.md).
- `doctor --strict` now treats a mapped runtime that is behind its configured
  upstream as unhealthy. A clean, internally consistent but stale checkout can
  no longer pass only because `repo-map.json` points to that stale commit.
- `doctor --strict` also requires mapped runtimes to record a `remote_commit`;
  an unversioned path alone is no longer accepted as runtime attestation.

- PR #44 established the pre-Continuation V2 `master` baseline at merge commit
  `11c337d`
- The independent FlowGrid AML Retriever ranked #8 in the first public Agent
  Memory Leaderboard Academic Textual track with a score of 43.98. This is
  external benchmark evidence for the competition retriever, not FlowGrid Core
  adoption or an end-to-end Core evaluation.
- The pre-Continuation V2 baseline passes `198` tests
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

## Continuation V2 Holdout

The Continuation V2 iteration repeated the same sealed A/B/C/D Luna Max
protocol on three current real projects: FlowGrid, FlightModeAI, and the AI
thinking canvas. Resume won FlowGrid and FlightModeAI by mean blind score;
Manifest won the AI thinking canvas. At least one FLG view beat no state in all
three projects, but stale FLG views produced critical failures in every project.

The supported product conclusion is therefore narrower than “FLG is always
better”: a current, correctly selected state view improves continuation, while
mere state availability does not. The result and its same-family, single-run,
owner-operated limits are recorded in the
[three-project report](../../evals/results/continuation-v2-three-project-20260812.md).

The same iteration compiles one canonical Current Action across Resume,
Manifest, and Handoff. Snapshot current state wins over legacy state caches;
deterministic contradictions produce `needs_reconciliation` instead of an
executable recommendation. Current-action and source-tree Smoke regressions
bring the branch to `211` passing tests. Real-project replay and a paired sealed
Luna Max rerun both pass. Across the three held projects, repaired Resume won
all three by mean blind score; Resume and Manifest received `0/12` critical-
failure scorer-view votes, versus `6/12` critical-failure votes for the two FLG
views before repair. This validates the targeted stale-current-action defect, not universal
superiority or external adoption. See the
[repair rerun](../../evals/results/current-action-repair-sealed-rerun-20260812.md).
Critical-voter counts use only the six failure categories frozen before scoring;
ordinary no-state inability remains in the semantic score rather than being
promoted post hoc into a critical boundary failure.

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

1. Field-test the Chinese attribution guard on privacy-safe real transcripts.
   Reported-speech and cross-sentence regressions now cover the deterministic
   false-attribution slice; broader pronoun resolution remains out of scope.
2. Field-test the explicit current-action date contract on real project state.
   Keep dates optional and machine-readable; do not infer deadlines from prose.
3. Separate four continuity-health dimensions in host guidance: structural
   integrity, runtime/source freshness, knowledge coverage, and unclosed work
   increments. Do not collapse them into one green status.
4. Re-run `flg impact` when a second privacy-safe real ledger has a larger
   relation graph. Keep automatic state transitions out of scope.
5. Validate the merged Windows hardening on another real Windows checkout when
   a current external host is available; CI coverage is complete for this slice.
6. Keep `DECISIONS.md` as formal truth. Derived impact and state views must stay
   rebuildable and must not introduce an autonomous decision authority.
7. Define a provider-neutral knowledge-source adapter before adding any new
   Wiki-specific behavior. FLG must track provenance, freshness, locators, and
   judgment impact while external tools own authoring, search, and publishing.
   The proposed boundary and acceptance criteria are recorded in the
   [Knowledge Source Adapter RFC](knowledge-source-adapter-rfc.md).

## Iteration Triage

- The current filesystem-Markdown continuity adapter and Source-backed Work View
  are implemented. The remaining problem is provider-neutral source freshness
  and host-triggered revalidation, not another Wiki storage or presentation
  layer.
- Pending captures are present in the startup Manifest on current master. The
  earlier recovery omission is therefore closed at the CLI layer.
- Runtime branch, HEAD, and dirty-state reporting was necessary but insufficient;
  upstream freshness is now part of strict health.
- Judgment-state ideas are accepted only as a bounded, derived impact view.
  A new schema, model dependency, or automatic evidence-driven reversal is not
  justified by current evidence.

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
