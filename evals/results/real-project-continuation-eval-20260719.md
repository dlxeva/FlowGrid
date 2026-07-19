# Real-project continuation evaluation - 2026-07-19

## Scope

This is a fresh three-mode continuation evaluation after the v0.4 state-boundary,
Context Pack action/risk, and runtime-resolution changes. It uses two redacted,
real local projects without modifying either source project:

- **Project F**: the FlowGrid dogfood ledger. Its raw history is long and contains
  earlier worktree, protocol, evaluation, and hackathon branches that were later
  narrowed or superseded.
- **Project O**: a real external-action observation project with an independent
  decision ledger, incomplete observation data, and several historical data
  discrepancies.

For each project, a fresh `gpt-5.4` agent using medium reasoning received exactly
one of the following sealed inputs:

- **Mode A**: continuation task only.
- **Mode B**: task plus uncompressed project history.
- **Mode C**: task plus the current FlowGrid Context Pack.

The continuation agents were instructed not to read outside their individual
temporary mode directory, not to modify files, and not to self-score. A separate
review scored their final responses against the current snapshots and formal
decisions. The disposable inputs remain outside this repository at
`/tmp/flowgrid-real-continuation-eval-20260719/` and are not a product fixture.

## Input Sizes

| Project | Mode A | Mode B raw history | Mode C Context Pack |
|---|---:|---:|---:|
| Project F | 1.1 KB | 211.2 KB | 12.1 KB |
| Project O | 1.1 KB | 44.8 KB | 9.1 KB |

Mode C used roughly 94% less input than the Project F raw-history mode and 80%
less than the Project O raw-history mode.

## Scoring

Each dimension is 0-2, for a maximum of 14. A proper no-state refusal receives
credit for boundary control and hallucination resistance, but cannot receive full
continuity or revision-reasoning credit.

1. Continuity accuracy
2. Judgment-boundary control
3. Rejected-alternative suppression
4. Revision reasoning
5. Evidence awareness
6. Action usefulness
7. Hallucination resistance

## Results

| Project | Mode A | Mode B | Mode C | Better than raw history? |
|---|---:|---:|---:|---|
| Project F | 10/14 | 13/14 | 14/14 | Yes |
| Project O | 10/14 | 14/14 | 12/14 | No |
| **Total** | **20/28** | **27/28** | **26/28** | **1 of 2** |

### Project F - FlowGrid dogfood ledger

- **Mode A (10/14):** correctly refused to invent a project state and requested a
  minimal handoff. It could not continue the project.
- **Mode B (13/14):** recovered v0.4's three core priorities, the raw-session and
  report-only boundary, the deferred cognitive-routing work, the dirty-checkout
  warning, and the separation of the hackathon branch. It appropriately named the
  three-mode evaluation as next. It also repeated a stale commit/test detail from
  the long history, so it lost one point for treating a historical operational
  claim as current rather than explicitly time-bounded.
- **Mode C (14/14):** retained the current goal, confirmed boundaries, unresolved
  assumptions, rejected expansion paths, and the same highest-value next action.
  It did not revive the cloud/hackathon branch or claim external adoption.

### Project O - external-action observation ledger

- **Mode A (10/14):** correctly refused to fabricate the project and requested
  minimum state inputs.
- **Mode B (14/14):** recovered the actual observation frame, the 100-day scope,
  priority ordering, the incomplete Day 20-23 data, conflicting balance values,
  the distinction between evidence and interpretation, and the correct next
  action: repair the observation gap before extracting mechanisms.
- **Mode C (12/14):** correctly preserved the latest five decisions, platform
  hierarchy, data-collection next action, and uncertainty about the missing
  goal/risk fields. However, it could not recover the project's higher-level
  observation frame, priority ordering, or historical numeric conflict because
  the Context Pack rendered `Current Goal`, `Review Object`, and `Proof Object`
  as undefined and compressed the relevant timeline too aggressively.

## Critical-Failure Review

No response invented stakeholder approval, re-opened a prohibited product
direction, or treated a pending item as a confirmed project fact.

Project O Mode C nevertheless has a **Context Pack completeness defect**: a clean
ledger with a useful `SNAPSHOT.md` can still produce a pack that lacks the
project's governing question and salient contradictions. This is not a reason to
add cognitive routing. It is a source-selection and compression problem.

## Interpretation

This evaluation passes the narrow claim that Context Pack is materially better
than no state in both real projects. It does **not** pass the stronger v0
threshold that Context Pack should beat raw history in four of five scenarios.
The current evidence is one Context Pack win and one raw-history win.

The useful finding is asymmetric:

- For a mature governed ledger, Context Pack retained the current decision
  boundary while removing stale operational detail.
- For a research/observation ledger, raw history retained the framing question,
  temporal contradictions, and interpretation boundary that the current Context
  Pack omitted.

## Required Follow-up

1. Add a deterministic Context Pack regression fixture where `SNAPSHOT.md`
   contains the governing observation frame, a priority order, and an unresolved
   contradictory measurement.
2. Update Context Pack source selection so a missing explicit `Current Goal` is
   not silently emitted as `(not defined)` when an actionable project frame is
   present elsewhere in `SNAPSHOT.md` or `FRAMING.md`.
3. Preserve salient contradictory measurements as an explicit `needs_recheck`
   item instead of compressing them out.
4. Re-run this exact three-mode protocol on at least three additional healthy
   real projects before claiming superiority over raw history.

## Limits

- Two projects and one response per mode are not a general benchmark.
- The evaluator was intentionally constrained by temporary directory boundaries;
  this is a controlled continuation test, not proof that every host preserves
  raw sessions automatically.
- The result does not validate external design-partner adoption, retention,
  payment, or host integration quality.
