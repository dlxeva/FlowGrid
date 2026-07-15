# Real-project continuation evaluation — 2026-07-16

## Scope

Two redacted local FLG projects were evaluated without modifying their source directories:

- Project W: a real project with four sessions, a long decision ledger, and known index drift.
- Project F: the FlowGrid dogfood project with five sessions, 27 formal decisions, and a healthy ledger.

Hermes ran through the configured `deepseek-chat` provider. Copies were created under `/tmp`, with project paths replaced by neutral labels. Each project was tested in three isolated modes:

- A: resume prompt only
- B: resume prompt plus project files and raw sessions/captures
- C: resume prompt plus a generated FlowGrid Context Pack

The evaluator could not read files outside the mode directory. Codex reviewed the outputs against the source project state rather than accepting model self-assessment.

## Findings

| Project | No state | Raw history | Context Pack |
|---|---|---|---|
| Project W | Correctly refused to fabricate; no continuation possible | Recovered the real next action: record and evaluate Fixture 05 | Failed to preserve the explicit next action; proposed a generic multi-fixture evaluation |
| Project F | Correctly refused to fabricate; no continuation possible | Recovered the current evaluation gate and its evidence limits | Recovered the current evaluation gate, but exposed missing rubric and source detail |

## Main result

The raw-history mode was the most reliable for the two real projects. The Context Pack was useful for Project F, but incomplete for Project W because it carried confirmed decisions and recent progress without a sufficiently explicit current next action. This is a concrete Context Pack completeness defect, not evidence for cognitive routing.

The result also confirms that a healthy ledger and a messy ledger need different handling: Project W's index drift must be surfaced as a warning, not silently compressed into a clean-looking state.

## Harness issue found and fixed during evaluation

The first Mode C attempt failed because the temporary copies omitted `.flg/CONTRACT.md`. This was an evaluation fixture construction error. After copying the actual protocol file from each project, `flg context` generated successfully for both projects.

## Required follow-up

1. Make Context Pack generation include an explicit current next action, current risks, and source-health warnings.
2. Add a regression fixture where `SNAPSHOT.md` and recent sessions contain a more specific next action than the formal decision summary.
3. Re-run the same two projects after the Context Pack fix.
4. Keep cognitive routing, blindspot discovery, and graph storage deferred until the continuation loop is stable.

## Limits

This is two projects, one remote evaluator provider, and one Codex review pass. It is evidence for a specific failure mode, not a general benchmark or proof that raw history is always better.
