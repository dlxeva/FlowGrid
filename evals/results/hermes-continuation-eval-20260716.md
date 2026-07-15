# Hermes continuation evaluation — 2026-07-16

## Scope

Independent continuation evaluation for two synthetic scenarios using separate Hermes CLI processes. Each scenario was run in three modes:

- A: resume prompt only (no project state)
- B: resume prompt plus raw session history
- C: resume prompt plus the prepared FlowGrid Context Pack

The evaluator could not read the golden decisions, runbook, source code, or other scenario files. Scores are the evaluator's 0–2 self-assessment across seven dimensions; maximum is 14.

## Results

| Scenario | Mode | Score | Critical failures | Format note |
|---|---:|---:|---|---|
| `client-solution-proposal` | A | 9/14 | None | Valid JSON |
| `client-solution-proposal` | B | 14/14 | None | Hermes wrapped JSON in a Markdown fence |
| `client-solution-proposal` | C | 14/14 | None | Hermes prefixed prose and then wrapped JSON |
| `campaign-proposal` | A | 2/14 | None | Valid JSON |
| `campaign-proposal` | B | 14/14 | None | Hermes wrapped JSON in a Markdown fence |
| `campaign-proposal` | C | 14/14 | None | Hermes prefixed prose and then returned JSON |

## Interpretation

The raw-history and Context Pack modes both reached the maximum self-assessed score in both scenarios. The no-state mode behaved differently by scenario: it produced a plausible but generic plan for the client scenario, while correctly refusing to fabricate a campaign continuation when no evidence was available. This is evidence that structured project state improves continuation quality and boundary control, not proof that Context Pack is superior to raw history.

The current result does not establish a statistically reliable Context Pack advantage: there are only two synthetic scenarios, one evaluator model, and the evaluator scored its own answers. The next evaluation must use longer, conflicting real-project histories and an independent scorer or fixed rubric review.

## Operational findings

1. Context Pack and raw history both preserved confirmed scope, pending questions, rejected alternatives, and reopening conditions in these fixtures.
2. No mode triggered a critical failure such as reviving a rejected direction, treating pending input as confirmed, or inventing approval, budget, metrics, or evidence.
3. Hermes did not consistently honor the machine-readable output contract. The evaluation harness must tolerate or normalize fenced/prefaced JSON and record that normalization explicitly.
4. The extraction-only harness and this continuation harness answer different questions. Extraction-only results must not be presented as evidence of cross-session continuation quality.

## Source artifacts

- `evals/runbook.md`
- `evals/scenarios/client-solution-proposal/resume-prompt.md`
- `evals/scenarios/client-solution-proposal/raw-session.md`
- `evals/scenarios/client-solution-proposal/expected-context-pack.md`
- `evals/scenarios/campaign-proposal/resume-prompt.md`
- `evals/scenarios/campaign-proposal/raw-session.md`
- `evals/scenarios/campaign-proposal/expected-context-pack.md`
- Raw evaluator output: `/tmp/flg-manual-eval-20260716/`

## Decision

Keep the current v0.4 priority on real-project continuation evidence. Do not add cognitive routing or blindspot features based on this result alone. First improve the harness's strict JSON handling and run the same rubric on long, contradictory real-project histories.
