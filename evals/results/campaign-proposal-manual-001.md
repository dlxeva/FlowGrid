# Eval Result: campaign-proposal

Model: GPT-5.5 Thinking
Date: 2026-07-07
Evaluator: ChatGPT, directional manual evaluation in current working conversation

## Evaluation Caveat

This run did not use three physically separate clean model sessions. It was performed as a directional manual eval from the scenario fixtures. Treat the score as a first stabilization signal, not as a benchmark-quality result.

Important fixture issue found: `resume-prompt.md` already contains the core KOL boundary and user-generated proof direction. That makes Mode A stronger than a true no-state baseline and reduces the measured lift from FlowGrid state.

## Mode A — No FLG State

Score: 8/14

- Continuity Accuracy: 1/2
- Judgment Boundary Control: 1/2
- Rejected Alternative Suppression: 1/2
- Revision Reasoning: 1/2
- Evidence Awareness: 1/2
- Action Usefulness: 1/2
- Hallucination Resistance: 2/2

Critical failures:

- None observed in this directional run.

Notes:

Mode A can avoid the worst KOL failure because the resume prompt itself says not to treat stakeholder interest in KOL as confirmed reversal, not to recommend KOL-heavy launch without new evidence, and to keep the proposal anchored on user-generated proof and conversion path clarity. It still lacks decision IDs, authority levels, and the confirmed/pending/rejected structure.

## Mode B — Raw History

Score: 13/14

- Continuity Accuracy: 2/2
- Judgment Boundary Control: 2/2
- Rejected Alternative Suppression: 2/2
- Revision Reasoning: 2/2
- Evidence Awareness: 2/2
- Action Usefulness: 2/2
- Hallucination Resistance: 1/2

Critical failures:

- None observed in this directional run.

Notes:

Raw history contains the relevant facts clearly and is short enough for a careful agent to recover the correct state. The main weakness is that status labels are implicit, so a weaker model could still over-weight the later stakeholder KOL comment. This fixture is currently too clean to strongly separate Mode B from Mode C.

## Mode C — FlowGrid Context Pack

Score: 14/14

- Continuity Accuracy: 2/2
- Judgment Boundary Control: 2/2
- Rejected Alternative Suppression: 2/2
- Revision Reasoning: 2/2
- Evidence Awareness: 2/2
- Action Usefulness: 2/2
- Hallucination Resistance: 2/2

Critical failures:

- None observed.

Notes:

Mode C gives the cleanest continuation surface. It explicitly separates D-001 and D-002 as confirmed decisions, D-003 as pending review, rejected alternatives as prohibited unless new evidence exists, and evidence references by source. The next action is also immediately usable: build the revision plan, explain what changed, handle the stakeholder KOL question as pending, and define evidence needed to reopen KOL.

## Comparison

Did Mode C beat Mode A?

Yes. Mode C beat Mode A by 6 points, but the measured gap is likely understated because Mode A is contaminated by key project-state constraints in the resume prompt.

Did Mode C beat Mode B?

Yes, narrowly. Mode C beat Mode B by 1 point. The small gap is expected because the raw history fixture is short, explicit, and low-noise.

What did Context Pack improve?

- Status separation: confirmed vs pending vs rejected is immediately visible.
- Judgment boundary control: KOL is framed as a rejected main path and only eligible as a bounded proof-loop test.
- Evidence awareness: the pack names which facts should be justified by source references.
- Action usefulness: the next actions are already shaped around proposal revision rather than broad rediscovery.

What did Context Pack fail to improve?

- It did not strongly outperform raw history in this specific fixture because the raw session is short and already highly structured.
- It did not expose a generator-level omission yet.

What should be changed in Context Pack contract or generator?

No generator change is justified from this single result. The fixture should be corrected first:

1. Reduce Mode A leakage by removing the KOL boundary and proof-object answer from `resume-prompt.md`, or mark it as a deliberately assisted baseline.
2. Make raw history longer and noisier so Mode B tests compression and judgment-status preservation rather than simple reading comprehension.
3. Keep the current Context Pack status fields because they directly explain Mode C's advantage.

## Product Implication

The current Context Pack contract is directionally valid for this scenario. The immediate product issue is eval design quality, not concept expansion. Next stabilization work should tighten this scenario before adding more scenarios.