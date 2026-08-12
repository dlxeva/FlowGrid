# Continuation V2 FlowGrid Pilot - 2026-08-12

## Question

Does current FlowGrid state help a fresh Agent continue the live FlowGrid
project better than no state or redacted raw history after the product changes
since the July real-project evaluation?

This is a protocol pilot, not a replacement for the historical five-project
result.

## Setup

Four isolated projectless Codex threads received the same continuation task and
could not read the repository, current parent conversation, web, or tools.
Every continuation used `gpt-5.6-luna` at its highest supported reasoning
effort, `max`.

| Mode | Material | Bytes | Duration |
| --- | --- | ---: | ---: |
| A | No project state | 0 | 33.7s |
| B | Redacted raw `.flg/sessions/` history | 32,601 | 474.9s |
| C | Current Resume Context Pack | 12,095 | 45.6s |
| D | Current Continuity Manifest | 5,345 | 157.5s |

The frozen ground truth came from the formal `SNAPSHOT.md`, `PROJECT.md`,
`FRAMING.md`, and `CONSTRAINTS.md` after all four responses completed. Today's
request to start a new evaluation was deliberately excluded from that ground
truth so it could not be leaked backward into the sealed inputs.

Two additional isolated Luna Max scorers received the frozen truth and anonymous
responses W/X/Y/Z. Both returned the same quality rank before the mapping was
revealed:

1. W = Mode C, Resume Context Pack
2. X = Mode A, no state
3. Z = Mode B, raw history
4. Y = Mode D, Manifest

## Blind Scores

Each scorer assigned 0-2 on goal accuracy, boundary control, rejected-path
control, unresolved-state accuracy, next-action accuracy, hallucination
resistance, and stale-state control.

| Mode | Scorer 1 | Scorer 2 | Mean | Critical-failure votes |
| --- | ---: | ---: | ---: | ---: |
| A: no state | 8 | 9 | 8.5 | 0/2 |
| B: raw history | 8 | 7 | 7.5 | 1/2 |
| C: Resume Pack | 12 | 13 | 12.5 | 0/2 |
| D: Manifest | 7 | 9 | 8.0 | 2/2 |

The no-state response ranked above the two stale continuations because it
correctly abstained instead of reviving an obsolete path. That is safe boundary
behavior, but it cannot actually continue the project.

## Findings

### Mode C won this pilot

Resume Pack recovered the formal current goal, core product boundaries,
rejected expansion paths, unresolved evidence gaps, and the external-host trial
as the next action. Neither blind scorer found a critical failure.

It used 62.9% fewer material bytes than raw history and completed about 10.4
times faster in this one run. Runtime variance is uncontrolled, so the duration
ratio is directional rather than a stable latency claim.

### Raw history revived stale work

Mode B recovered many correct boundaries, but it treated an older
"Project Continuity Layer / six capabilities / complete push" discussion as
current and proposed creating a feature branch and pushing an implementation.
One scorer marked that as critical; both gave next-action accuracy zero.

### Manifest has a current-state precedence defect

Mode D recovered the goal and high-level boundaries with the smallest input,
but treated D-027's old evaluation action as unfinished. The formal snapshot
states that the three-mode evaluation is complete and names the external-host
trial as the current next action.

Both scorers marked the Manifest response critical. The defect is not lack of
reasoning: the generated Manifest lists confirmed judgments and pointers but
does not expose the snapshot's completion override or the actual next-action
content. Its compact map therefore allowed an older confirmed decision to look
current.

## Supported conclusion

For this one current FlowGrid dogfood project, the current Resume Context Pack
was better than no state, redacted raw history, and Manifest under Luna Max. It
preserved current project truth with substantially less input than raw history.

This does not update the historical `1 win / 3 ties / 1 loss` result. A new
cross-project result requires at least two additional pre-registered real
holdouts and repeated runs. It also does not prove external adoption or net
value after maintenance cost.

## Next gate

The two pre-selected holdouts have now been completed with the same Luna Max
protocol. See the [three-project result](continuation-v2-three-project-20260812.md).
Manifest/current-action precedence remains a product defect rather than a
closed implementation item.
