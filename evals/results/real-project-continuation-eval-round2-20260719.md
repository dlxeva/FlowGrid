# Real-project continuation evaluation round 2 - 2026-07-19

## Scope

This is the required expansion of the 2026-07-19 three-mode continuation
evaluation. It uses three additional, redacted real local ledgers without
modifying their source projects:

- **Project R**: a content-production and calibration project with confirmed
  visual constraints, a manually published first episode, and incomplete
  outcome snapshots.
- **Project T**: a one-off interactive-content project at the final preview and
  publication-decision boundary.
- **Project H**: a post-meeting B2B proposal whose current snapshot explicitly
  supersedes a pre-meeting OCR framing.

For every project, fresh `gpt-5.4` agents using medium reasoning received one
sealed temporary directory only. Mode A received the task; Mode B received the
task plus uncompressed history; Mode C received the task plus the generated
Context Pack. Agents could not read project directories, git history, or the
web, and did not self-score. The disposable inputs remain outside this
repository at `/tmp/flowgrid-real-continuation-round2-20260719/`.

## Input Sizes

| Project | Mode A | Mode B raw history | Mode C Context Pack |
|---|---:|---:|---:|
| Project R | 1.1 KB | 53.3 KB | 13.5 KB |
| Project T | 1.1 KB | 34.4 KB | 14.8 KB |
| Project H | 1.1 KB | 33.1 KB | 15.5 KB |

Mode C used 60-75% less input than the raw-history mode across these projects.

## Scoring

The same independent seven-dimension, 14-point rubric from the previous real
continuation evaluation was used:

1. Continuity accuracy
2. Judgment-boundary control
3. Rejected-alternative suppression
4. Revision reasoning
5. Evidence awareness
6. Action usefulness
7. Hallucination resistance

## Initial Results

| Project | Mode A | Mode B | Mode C | Better than raw history? |
|---|---:|---:|---:|---|
| Project R | 10/14 | 14/14 | 14/14 | Tie |
| Project T | 10/14 | 14/14 | 14/14 | Tie |
| Project H | 10/14 | 14/14 | 11/14 | No; stale-source defect |
| **Total** | **30/42** | **42/42** | **39/42** | **0 of 3** |

All three no-state agents correctly declined to invent a project state. This is
useful boundary behavior, but it cannot replace continuation.

### Project R

Both raw history and Context Pack preserved the current Phase 1 state, the
distinction between production feasibility and demand evidence, the locked visual
system, and the next action of completing the EP001 observation snapshots. Mode
C retained these boundaries with substantially less input.

### Project T

Both raw history and Context Pack preserved the one-off satire boundary, the
static-H5 decision, the public naming and disclaimer constraints, the
unconfirmed external feedback, and the final owner check before an irreversible
submission decision. Mode C did not claim that preview loading proved public
publication or real engagement.

### Project H: discovered stale-source defect

The initial Mode C response correctly chose the locked next action and preserved
the Conditional Go and small-sample-validation decisions. However, it also
treated the explicitly superseded `FRAMING.md` goal, OCR-only range, and 2-5w
cost as active state because the generator used that file as a fallback and
rendered an older `CONSTRAINTS.md` section as current. Raw history correctly
recognized that those assumptions had been overturned after the meeting.

This is a material Context Pack defect: a source which states that it is no
longer current project truth cannot be allowed to fill current-state fields.

## Targeted Repair and Recheck

The generator was repaired in the same evaluation cycle:

- an explicitly obsolete `FRAMING.md` no longer supplies Current Goal, Review
  Object, Proof Object, Project Frame, or open questions;
- current `SNAPSHOT.md` hard constraints and non-goals take precedence over a
  separate historical constraints file;
- an obsolete framing source is omitted from `Sources Included` so agents do not
  mistake it for startup truth;
- a deterministic regression test covers this source-precedence case.

A new clean Mode C agent then re-ran Project H against the regenerated pack and
scored **14/14**. It correctly treated the old OCR-only and 2-5w statements as
historical, retained the Conditional Go / no-development boundary, and selected
the agreed case-study delivery as the next action.

The recheck validates this defect repair, but it is not counted as a second raw
history comparison because the code changed after the original Mode B run.

## Combined Evidence After Five Real Projects

Combining the earlier two-project evaluation with this expanded sample gives:

| Outcome after current repair | Count |
|---|---:|
| Context Pack beats raw history | 1 |
| Context Pack ties raw history | 3 |
| Context Pack loses to raw history | 1 |

Context Pack now has no known critical continuation failure in the five sampled
projects, and it is consistently better than no-state continuation. It still
does **not** meet the v0 superiority threshold of beating raw history in at
least four of five scenarios.

## Interpretation and Next Gate

The supported claim is now:

> Context Pack can preserve current decision boundaries with materially less
> context than raw history, but it has not yet demonstrated general superiority
> over raw history.

Do not expand into cognitive routing, a blindspot engine, or provenance graph
work on the basis of this result. The next product-validation gate is a real
host-adapter run: verify that a host can archive a natural session, invoke
background capture/closeout, and give the next agent a valid Context Pack
without requiring the user to learn FLG commands.

## Limits

- One response per mode is directional evidence, not a benchmark.
- The repaired Project H recheck validates a specific regression only.
- These tests do not establish external design-partner adoption, retention,
  payment, or host integration reliability.
