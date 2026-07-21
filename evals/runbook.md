# FlowGrid Eval Runbook

## Purpose

This runbook defines how to manually evaluate whether FlowGrid Context Pack improves agent continuation.

The eval compares three modes:

- Mode A: no FLG state
- Mode B: raw history
- Mode C: FlowGrid Context Pack

The goal is to test the product claim, not to make the model look good.

## Required Inputs

For each scenario, use the files in:

```text
evals/scenarios/<scenario-name>/
```

Required files:

- `scenario.md`
- `raw-session.md`
- `golden-decisions.md`
- `rejected-alternatives.md`
- `expected-context-pack.md`
- `resume-prompt.md`
- `scoring-notes.md`

## Evaluation Setup

Run each scenario at least five times with the same model and reasoning setting.
Use distinct clean sessions for every run/mode pair. Report both mean score and
`Pass^k`: a mode only passes stability when every run reaches the minimum score
and produces no critical failure.

Prepare sealed, hash-addressed input packs before opening any evaluator session:

```bash
python evals/continuation_stability.py prepare \
  --output /tmp/flowgrid-continuation-stability \
  --runs 5
```

Each evaluator receives one `input.md` only and writes its response to the
matching `response.md`. A separate scorer writes machine-readable scores to
`scorer-output.json`; do not let the continuation agent score itself. Link that
output to the scorecard so the harness can verify the input, response, and
scorer-output hashes:

```bash
python evals/continuation_stability.py record \
  --scorecard /tmp/flowgrid-continuation-stability/run-01/campaign-proposal/mode-c/score.json \
  --scorer-output /tmp/flowgrid-continuation-stability/run-01/campaign-proposal/mode-c/scorer-output.json \
  --evaluator independent-scorer \
  --continuation-model gpt-5.4 \
  --scorer-model gpt-5.6-terra
```

After every scorecard is linked, aggregate the result with:

```bash
python evals/continuation_stability.py summarize \
  --output /tmp/flowgrid-continuation-stability --strict
```

Prepare the deterministic FlowGrid Context Packs with the repository-local
runtime before opening the manual model sessions:

```bash
python evals/prepare_context_eval.py --output /tmp/flowgrid-context-eval
```

This script only creates disposable project directories and copies the generated
Context Packs to the requested output directory. It does not score model output.

### Mode A — No FLG State

Give the agent only `resume-prompt.md`.

Do not provide `raw-session.md`, `golden-decisions.md`, or `expected-context-pack.md`.

### Mode B — Raw History

Give the agent:

- `resume-prompt.md`
- `raw-session.md`

Do not provide the expected Context Pack.

### Mode C — FlowGrid Context Pack

Give the agent:

- `resume-prompt.md`
- `expected-context-pack.md`

Do not provide raw history unless the agent explicitly asks for evidence.

## Evaluation Procedure

1. Select one scenario.
2. Open a clean model session for Mode A.
3. Provide the Mode A inputs and capture the full response.
4. Open a clean model session for Mode B.
5. Provide the Mode B inputs and capture the full response.
6. Open a clean model session for Mode C.
7. Provide the Mode C inputs and capture the full response.
8. Score each response using `scoring-notes.md`.
9. Record critical failures.
10. Compare total scores and failure patterns.

## Scoring Dimensions

Each dimension is scored 0-2.

1. Continuity Accuracy
2. Judgment Boundary Control
3. Rejected Alternative Suppression
4. Revision Reasoning
5. Evidence Awareness
6. Action Usefulness
7. Hallucination Resistance

Maximum score per run: 14.

## Critical Failures

A response can score well in some areas and still fail if it violates a core project boundary.

Examples:

- treats pending input as confirmed decision
- revives rejected alternatives without new evidence
- relies on superseded judgments as current truth
- invents stakeholder approval, budget, metrics, or evidence
- ignores the proof object
- restarts broad discovery despite available project state

## Result Record Template

```markdown
# Eval Result: <scenario-name>

Model:
Date:
Evaluator:

## Mode A — No FLG State

Score:

- Continuity Accuracy:
- Judgment Boundary Control:
- Rejected Alternative Suppression:
- Revision Reasoning:
- Evidence Awareness:
- Action Usefulness:
- Hallucination Resistance:

Critical failures:

Notes:

## Mode B — Raw History

Score:

- Continuity Accuracy:
- Judgment Boundary Control:
- Rejected Alternative Suppression:
- Revision Reasoning:
- Evidence Awareness:
- Action Usefulness:
- Hallucination Resistance:

Critical failures:

Notes:

## Mode C — FlowGrid Context Pack

Score:

- Continuity Accuracy:
- Judgment Boundary Control:
- Rejected Alternative Suppression:
- Revision Reasoning:
- Evidence Awareness:
- Action Usefulness:
- Hallucination Resistance:

Critical failures:

Notes:

## Comparison

Did Mode C beat Mode A?

Did Mode C beat Mode B?

What did Context Pack improve?

What did Context Pack fail to improve?

What should be changed in Context Pack contract or generator?
```

## Success Threshold

For v0, Context Pack should:

- beat Mode A in all scenarios
- beat Mode B in at least 4 of 5 scenarios
- reduce critical failures around pending/rejected/superseded judgment boundaries
- reduce invented project facts
- improve next-action usefulness

## Product Interpretation

If Mode C loses to raw history, inspect whether:

- Context Pack omitted important current state
- judgment status was unclear
- rejected alternatives were not explicit enough
- proof object was missing
- agent instructions were too weak
- evidence references were insufficient

If Mode C only wins over no-state but not raw history, FlowGrid may still be useful, but the Context Pack contract needs sharper compression and stronger judgment boundaries.

## English-Native Gate\n\nRun the deterministic English-first CLI gate before release changes:\n\n```bash\npython evals/english_native_check.py --output /tmp/flowgrid-english-native-eval.json\n```\n\nIt checks English initialization, external transcript archiving, English closeout output,\nand protection against promoting a revisit question into a formal decision. It does not\nreplace manual model-quality scoring.\n\n## Current Manual Priority

Run `campaign-proposal` first.

Then run `client-solution-proposal`.

Do not automate scoring until at least two scenarios have been manually evaluated.
