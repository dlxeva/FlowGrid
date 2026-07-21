# Continuation Stability Evaluation - 2026-07-22

## Scope

This is the first five-run, three-mode evaluation using the repeatable
`continuation_stability.py` harness. It uses the synthetic
`campaign-proposal` scenario only.

- Evaluator: five fresh `gpt-5.4` sessions per mode, medium reasoning.
- Scorer: a separate fresh `gpt-5.6-terra` session per response, medium
  reasoning.
- Isolation: evaluators and scorers were instructed to read only the supplied
  input or response, use no tools, and ran outside the FlowGrid repository.
- Integrity: every scorecard stores the SHA-256 hashes of its sealed input,
  evaluator response, and independent scorer output.

The complete synthetic artifacts are committed under
[`continuation-stability-20260722/`](continuation-stability-20260722/): 15
sealed inputs, 15 evaluator responses, 15 scorer outputs, 15 linked
scorecards, and the manifest.

## Results

| Scenario | Mode | Runs | Mean | Min | Max | Critical failures | Stable pass |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| campaign-proposal | A: no state | 5/5 | 4.4 | 4 | 5 | 0 | No |
| campaign-proposal | B: raw history | 5/5 | 14.0 | 14 | 14 | 0 | Yes (`Pass^k`) |
| campaign-proposal | C: Context Pack | 5/5 | 13.8 | 13 | 14 | 0 | Yes (`Pass^k`) |

Across the five matched B/C pairs, Context Pack was better in 0 runs, tied in
4, and lower in 1.

## What This Proves

1. In this fixture, a fresh agent with no state stays conservative rather than
   inventing a KOL decision, but cannot recover the prior judgment chain.
2. Both raw history and Context Pack preserve the confirmed KOL rejection,
   pending revisit, user-proof direction, and evidence gate across five runs.
3. Context Pack is stable enough to pass the scenario threshold without a
   critical boundary failure.
4. The harness now links every reported score to the exact input, response, and
   independent scorer output instead of accepting an ungrounded scorecard.

## What This Does Not Prove

This does **not** prove that Context Pack is better than raw history. The raw
history is short, explicit, and clean, so a strong model can recover the same
state without compression. The one lower Context Pack score makes a superiority
claim specifically false for this run.

It also does not establish real-project or cross-host performance. The next
evaluation must use long, contradictory real project histories and record input
size, revived rejected directions, boundary errors, and user correction burden.

## Decision

Keep the v0.4 priority on entry reliability, ledger/index reconstruction, and
real-project continuation. Do not add cognitive routing, blindspot discovery,
or a graph database based on this synthetic result.
