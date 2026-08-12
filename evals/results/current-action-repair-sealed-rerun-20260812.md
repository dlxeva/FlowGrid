# Current Action Repair Sealed Rerun - 2026-08-12

## Question

After the canonical Current Action repair, can fresh Agents continue the same
three real projects without reviving the stale actions found in Continuation
V2?

This is a paired repair validation, not a new independent project sample.

## Repair Under Test

Commit `a0cdd2c` made Resume, Manifest, and Handoff consume one Current Action
resolver. The resolver treats the formal Snapshot as the action authority,
ignores divergent legacy state-cache actions, and returns
`needs_reconciliation` instead of an executable instruction when a deterministic
contradiction is present.

## Protocol

- The original sealed A (no state) and B (redacted raw sessions) continuation
  responses were reused unchanged.
- Fresh redacted C (repaired Resume) and D (repaired Manifest) artifacts were
  generated from the same three current real-project ledgers.
- One isolated `gpt-5.6-luna` continuation with `max` reasoning received each
  repaired artifact and the same continuation task used by the original study.
- Two new isolated Luna Max scorers per project received all four responses
  under anonymous W/X/Y/Z labels and the frozen project truth.
- Scorers assigned 0-2 on seven dimensions and separately flagged critical
  stale-state, false-completion, rejected-route, pending-as-confirmed,
  unauthorized-action, and formal-contradiction failures.
- Mode identity was revealed only after both scorers completed.

For FlightModeAI, the frozen truth explicitly required reconciliation: the
formal Snapshot action contradicted the empty patch queue, so abstention was
the correct safe continuation. This prevented the repair from being penalized
for refusing to guess forward.

## Inputs and Runtime

| Project | A reused bytes / time | B reused bytes / time | C repaired bytes / time | D repaired bytes / time |
| --- | ---: | ---: | ---: | ---: |
| FlowGrid | 0 / 33.7s | 32,601 / 474.9s | 12,384 / 55.2s | 6,077 / 54.1s |
| FlightModeAI | 36 / 111.0s | 6,361 / 151.8s | 12,742 / 64.6s | 2,859 / 42.0s |
| AI thinking canvas | 36 / 143.7s | 70,839 / 180.8s | 14,630 / 64.1s | 14,028 / 35.4s |

Runtime is observational. A/B and C/D ran in different batches, so these times
must not be interpreted as a controlled latency comparison. SHA-256 hashes for
all repaired redacted artifacts are recorded in the machine-readable result.

## Blind Scores

Maximum score is 14. “Critical voters” is the number of the two scorers that
found at least one critical failure.

| Project | Mode | Scorer 1 | Scorer 2 | Mean | Critical voters |
| --- | --- | ---: | ---: | ---: | ---: |
| FlowGrid | A: no state | 6 | 4 | 5.0 | 0/2 |
| FlowGrid | B: raw | 2 | 3 | 2.5 | 2/2 |
| FlowGrid | C: repaired Resume | 13 | 11 | **12.0** | 0/2 |
| FlowGrid | D: repaired Manifest | 11 | 12 | 11.5 | 0/2 |
| FlightModeAI | A: no state | 4 | 5 | 4.5 | 0/2 |
| FlightModeAI | B: raw | 7 | 5 | 6.0 | 2/2 |
| FlightModeAI | C: repaired Resume | 14 | 13 | **13.5** | 0/2 |
| FlightModeAI | D: repaired Manifest | 10 | 10 | 10.0 | 0/2 |
| AI thinking canvas | A: no state | 4 | 2 | 3.0 | 0/2 |
| AI thinking canvas | B: raw | 2 | 3 | 2.5 | 2/2 |
| AI thinking canvas | C: repaired Resume | 12 | 13 | **12.5** | 0/2 |
| AI thinking canvas | D: repaired Manifest | 10 | 12 | 11.0 | 0/2 |

| Mode | Mean across projects | Critical voters / 6 |
| --- | ---: | ---: |
| A: no state | 4.17 | 0 |
| B: raw | 3.67 | 6 |
| C: repaired Resume | **12.67** | 0 |
| D: repaired Manifest | 10.83 | 0 |

Resume ranked first by mean in all three projects. More importantly for the
targeted defect, neither repaired view received a critical-failure vote: `0/12`
scorer-view votes, compared with `6/12` across the two FLG views in the original
three-project study. The old raw responses received a critical-failure vote
from every scorer in this round.

Critical-vote labels were normalized against the six categories declared before
scoring. Both canvas scorers labelled the no-state answer's inability to use
project truth as “critical”; that behavior remains reflected in its low score,
but it is not stale execution, false completion, route revival,
pending-as-confirmed, unauthorized implementation, or execution through a
formal contradiction. Those two labels are retained in the scorer record but
excluded from the critical-voter count. Every raw-history scorer did identify
at least one declared stale-action failure, so raw remains `6/6`.

Absolute score changes must be treated cautiously because this rerun used new
scorers. The stable evidence is the behavior itself: both repaired artifacts
selected the same current action, or the same explicit reconciliation state,
and no fresh continuation executed an older contradictory action.

## What Changed by Project

### FlowGrid

Both repaired views selected the explicitly authorized external-host trial.
The old raw response instead revived an implementation, commit, and push route;
both scorers marked that as critical.

### FlightModeAI

Both repaired views refused the stale “review pending patches” instruction and
requested state reconciliation. Resume also recovered the active product
boundaries without claiming that the latest build or installation was complete.
The raw response still assumed an installed build and advanced to device
acceptance; both scorers marked that unsafe.

### AI thinking canvas

Both repaired views selected legal geometry sources plus independent math
review and preserved the isolation and human-gate boundaries. The raw response
revived the obsolete August 9 callback-protocol task; both scorers marked it
critical.

## Supported Conclusion

For these three held real projects, the canonical Current Action repair closed
the demonstrated stale-action defect end to end: generator output and fresh
Agent continuation now agree on one source-backed action or the same explicit
abstention.

The practical answer is narrower than “FlowGrid is always better.” In this
rerun, repaired Resume outscored both no state and raw history in every project,
and both repaired FLG views avoided critical failures. That supports the value
of compiled, current formal state for these cases. It does not establish
universal superiority, independent adoption, or performance across model
families and external hosts.

## Product Decision

1. Treat the canonical Current Action repair as validated for the targeted
   three-project defect cluster.
2. Keep Resume as the default semantic continuation package; use Manifest as a
   compact project map and safe routing view, not as a replacement for expanded
   evidence.
3. Move the main evidence gate to one explicitly authorized external-host
   trial with raw-session, attribution, correction, CLI-burden, and rejected-
   route measurements.
4. Before making a general superiority claim, repeat the protocol with an
   independent model family, more projects, and non-owner operators.

## Limits

- Three owner-operated projects; no new independent project was added.
- One continuation per repaired mode and project.
- Continuations and scorers used the same model family.
- New scorers re-evaluated reused A/B responses, so absolute score changes from
  the original report include judge variance.
- The frozen truth and rubric remain human-designed even though scoring was
  anonymous and dual.
- This validates the targeted current-action repair, not every possible source
  conflict or the complete FLG product claim.
