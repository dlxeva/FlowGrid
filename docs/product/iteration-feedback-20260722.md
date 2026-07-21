# Iteration Feedback Closure - 2026-07-22

This note records three repeated FlowGrid feedback patterns, the smallest
product rule adopted for each, and the evidence that the rule is executable.
It does not promote a single incident into a universal product claim.

## 1. A formal decision without a durable path back is weak project state

**Feedback source:** The FlowGrid iteration log's direct-decision and handoff
observations showed that an entry could reach `DECISIONS.md` while later
handoff or evidence tooling could not explain its originating material.

**Rule:** Formal ledger remains the source of truth; every indexed judgment
gets rebuildable Source Episodes for its raw session, capture, closeout patch,
review action, and ledger anchor where available.

**Implementation:** `flg reindex`, `flg doctor`, and `flg trace D-xxx`.

**Verified:** `test_reindex_builds_stable_source_episodes_and_trace_reads_them`
and `test_doctor_reports_broken_source_episode` cover construction, recovery,
and failure detection. `flg doctor --strict` on the FlowGrid project reports 36
formal and indexed decisions with zero missing or broken Source Episodes.

**Boundary:** This is a local, file-based provenance index. It is not a graph
database, access-control system, or a claim that every old manual decision has
a preserved verbatim transcript.

## 2. Verification work must not become an invented project decision

**Feedback source:** Repeated host and closeout replays generated plausible
candidate decisions from assistant narration, test reports, and routine
validation statements. The safe write path correctly rejected them, but the
host protocol needed to say what to retain instead.

**Rule:** Preserve material verification evidence, but do not create or promote
a formal decision unless an attributed user/client choice changes a boundary or
supplies a reversal condition.

**Implementation:** The `flowgrid-operator` Skill's `Verification-only
segments` protocol; shell or ambiguous candidates are closed without adoption
while their raw source remains traceable.

**Verified:** The repository smoke flow and autonomous-review regression suite
continue to keep shell and unattributed candidates out of `DECISIONS.md`.

**Boundary:** This deliberately favors a missed automatic capture over
misrepresenting an AI explanation as a human-authorized fact. Explicit user
commitments can still use the direct decision path.

## 3. A Context Pack must be judged against raw history, not assumed superior

**Feedback source:** Real-project replays already showed Context Pack could
match or lose to raw history for observation-heavy projects. The first
five-run independently scored synthetic stability evaluation confirms the same
boundary for a short, clean campaign history.

**Rule:** Treat Context Pack as a bounded continuation surface. Do not optimize
for a synthetic score win or claim general superiority over raw history without
long, contradictory real-project evidence.

**Implementation:** `evals/continuation_stability.py` seals inputs, records
responses, links independent scorer output through hashes, and reports both
`Pass^k` stability and Mode C versus raw-history pairs.

**Verified:** [The 2026-07-22 result](../../evals/results/continuation-stability-20260722.md)
has five independently scored runs per mode: no state 4.4/14, raw history
14.0/14, Context Pack 13.8/14, and no critical failure. Mode C was 0 wins, 4
ties, and 1 lower than raw history.

**Boundary:** This verifies safe stable continuation for one synthetic scenario,
not cross-host adoption, real-project superiority, or a need for cognitive
routing or progressive-disclosure features.
