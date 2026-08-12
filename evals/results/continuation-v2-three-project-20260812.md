# Continuation V2 Three-Project Holdout - 2026-08-12

## Question

After further real-project use and product changes, does having FlowGrid state
make a fresh Agent continue a project better than having no project state?

The test separates that broad question from a harder product question: does one
default FLG view work reliably across different project histories?

## Protocol

Three live projects were selected before inspecting holdout outputs: FlowGrid,
FlightModeAI, and the AI thinking canvas. Four isolated projectless threads per
project received the same continuation task and one sealed input:

- A: no project state;
- B: redacted raw `.flg/sessions/` history;
- C: current Resume Context Pack;
- D: current Continuity Manifest.

All 12 continuations used `gpt-5.6-luna` with `max` reasoning. The two
additional projects were only sent after explicit owner approval and were
redacted before remote use. Two isolated Luna Max scorers per project received
the frozen ground truth and anonymous W/X/Y/Z responses. They scored seven
dimensions from 0-2 and separately flagged critical stale-state, false-
completion, rejected-route, pending-as-confirmed, and unauthorized-action
failures. Mode identity was revealed only after scoring.

The FlowGrid row is the previously sealed pilot; FlightModeAI and the AI
thinking canvas are the two pre-selected follow-up holdouts.

## Inputs and Runtime

| Project | Mode A bytes / time | Mode B bytes / time | Mode C bytes / time | Mode D bytes / time |
| --- | ---: | ---: | ---: | ---: |
| FlowGrid | 0 / 33.7s | 32,601 / 474.9s | 12,095 / 45.6s | 5,345 / 157.5s |
| FlightModeAI | 36 / 111.0s | 6,361 / 151.8s | 12,459 / 176.3s | 2,530 / 739.9s |
| AI thinking canvas | 36 / 143.7s | 70,839 / 180.8s | 14,883 / 151.9s | 13,539 / 142.8s |

Runtime was not controlled and is reported as observation, not a stable latency
claim. FlightModeAI also shows that a generated Resume Pack can be larger than
its short raw history.

## Blind Scores

Maximum score is 14. “Critical voters” is the number of the two scorers that
found at least one critical failure; it is not the number of failure labels.

| Project | Mode | Scorer 1 | Scorer 2 | Mean | Critical voters |
| --- | --- | ---: | ---: | ---: | ---: |
| FlowGrid | A: no state | 8 | 9 | 8.5 | 0/2 |
| FlowGrid | B: raw | 8 | 7 | 7.5 | 1/2 |
| FlowGrid | C: Resume | 12 | 13 | **12.5** | 0/2 |
| FlowGrid | D: Manifest | 7 | 9 | 8.0 | 2/2 |
| FlightModeAI | A: no state | 3 | 3 | 3.0 | 0/2 |
| FlightModeAI | B: raw | 11 | 7 | 9.0 | 2/2 |
| FlightModeAI | C: Resume | 9 | 10 | **9.5** | 0/2 |
| FlightModeAI | D: Manifest | 8 | 3 | 5.5 | 2/2 |
| AI thinking canvas | A: no state | 7 | 5 | 6.0 | 0/2 |
| AI thinking canvas | B: raw | 4 | 5 | 4.5 | 2/2 |
| AI thinking canvas | C: Resume | 5 | 7 | 6.0 | 2/2 |
| AI thinking canvas | D: Manifest | 12 | 12 | **12.0** | 0/2 |

Both FlowGrid scorers ranked C > A > B > D. FlightModeAI scorers disagreed on
the top two: one ranked B > C > D > A and the other C > B > D > A. Both AI
thinking canvas scorers ranked D > A > C > B.

| Mode | Mean across projects | Critical voters / 6 |
| --- | ---: | ---: |
| A: no state | 5.83 | 0 |
| B: raw | 7.00 | 5 |
| C: Resume | **9.33** | 2 |
| D: Manifest | 8.50 | 4 |

The aggregate is descriptive only. It does not erase project-level critical
failures or prove that three projects represent a population.

## What Actually Happened

### FlowGrid: Resume correctly overrode old work

Resume recovered the current external-host trial. Raw history and Manifest
revived older implementation or completed-evaluation actions. Compactness alone
did not make Manifest current.

### FlightModeAI: Resume narrowly won, raw history was plausible but unsafe

Raw history understood the one-theme learning product and 13-screen native
direction, but both scorers found that it treated the latest build as already
installed and skipped the unfinished build/install gate. Resume correctly kept
that state unresolved, although it proposed freezing a learning-pack acceptance
spec before directly finishing the authorized implementation. The two scorers
therefore split their top rank.

Manifest was smallest but spent 739.9 seconds to recommend reading another
state package and following a Snapshot action. It did not perform the actual
continuation and risked reviving a stale “review pending patches” instruction.

### AI thinking canvas: only Manifest selected the current priority

Manifest identified the current geometry-source and independent-math-review
gate while preserving the isolation of web, Windows, old GOAI, and Artifact
Review work. Raw history revived an August 9 callback-protocol task. Resume
revived IMP-007 Artifact Review implementation despite the newer Snapshot and
the absence of authorization to resume product code. Both scorer pairs marked
those stale continuations critical.

## Supported Conclusion

The plain answer is:

**Having FLG can be better than having nothing, but having FLG is not by itself
enough. The Agent must receive the current view and understand which newer state
overrides older decisions.**

At least one FLG view outscored no state in all three projects. The winning view
was not universal: Resume won two projects and Manifest won one. Wrong or stale
FLG views could be worse than no state because abstention is safer than
confidently continuing an obsolete task.

The result also explains the historical `1 win / 3 ties / 1 loss`: FLG's
potential value is visible, but current-state selection and supersession are
still product work. The historical result and this V2 result should not be
arithmetically combined because their models, protocol, and compared modes
differ.

## Product Decision

The next iteration should optimize one target: **safe current-state selection**.

1. Compile one canonical `current_action` with explicit source and timestamp.
2. Encode `supersedes`, `completed`, and `stale` relationships before rendering
   Resume or Manifest.
3. Refuse or abstain when two views disagree on the current action.
4. Add a deterministic continuation check: no completed or superseded action
   may appear as the recommended next step.
5. Re-run these same sealed projects after the repair; do not select the best
   view after seeing outputs.

This is a stronger and more falsifiable target than increasing document count
or assuming that more context is better.

## Repair Implemented on Evaluation Branch

The first deterministic repair is implemented after the sealed run:

- Resume, Manifest, and Handoff now use one current-action resolver;
- `SNAPSHOT.md` is the formal current-action authority;
- legacy `state.next_actions` entries are counted and ignored when they differ;
- an empty patch queue invalidates “Review pending patches”;
- an action repeated under an explicit completed, superseded, or stale section
  is refused;
- every view exposes action status, source, source timestamp, ignored fallback
  count, and the reason for selection or abstention.

This implementation is not evidence that the semantic continuation problem is
closed. It must pass deterministic real-project replay first, then the same
sealed model protocol without selecting a mode after output inspection.

The deterministic replay has since passed on all three projects; see
[`current-action-replay-20260812.md`](current-action-replay-20260812.md). The
fresh-Agent semantic rerun remains the next evidence gate.

## Limits

- One continuation per mode and project.
- Continuations and scorers used the same model family.
- All three projects are owner-operated, not independent external adoption.
- Frozen truth and rubric design still contain human judgment, although mode
  anonymity and dual scoring reduce direct preference leakage.
- Selecting the best FLG view after scoring is an oracle comparison; the
  product has not yet demonstrated automatic view selection.
