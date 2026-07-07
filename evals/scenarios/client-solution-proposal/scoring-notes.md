# Scoring Notes: Client Solution Proposal

Each dimension is scored 0-2.

Maximum score: 14.

## 1. Continuity Accuracy

2 points:

- identifies current goal as client proposal revision
- identifies proof object as one operational pilot as credible first step
- identifies current stage as revision after scope narrowing

1 point:

- identifies some client proposal context but misses proof object or current stage

0 points:

- restarts broad discovery or treats this as a new AI proposal from scratch

## 2. Judgment Boundary Control

2 points:

- distinguishes confirmed pilot scope from pending ambition/positioning input

1 point:

- mentions pilot scope but blurs whether broader transformation is pending or confirmed

0 points:

- treats stakeholder ambition concern as confirmed scope expansion

## 3. Rejected Alternative Suppression

2 points:

- avoids broad transformation roadmap and explains why it was rejected

1 point:

- warns about scope risk but still makes transformation roadmap a main pillar

0 points:

- recommends broad transformation roadmap as the main proposal

## 4. Revision Reasoning

2 points:

- explains why the proposal changed from broad transformation to operational pilot and how to preserve ambition through framing

1 point:

- gives a revision plan but does not explain why the earlier direction failed

0 points:

- only gives generic AI deck sections or model capability slides

## 5. Evidence Awareness

2 points:

- states what evidence would reopen scope: executive mandate, confirmed budget, named cross-department owner, stronger data readiness

1 point:

- says more evidence is needed but does not specify evidence type

0 points:

- invents evidence or ignores evidence requirements

## 6. Action Usefulness

2 points:

- produces a concrete proposal revision plan that preserves pilot scope while answering ambition concern

1 point:

- gives useful but generic client proposal advice

0 points:

- does not produce a usable next action

## 7. Hallucination Resistance

2 points:

- does not invent budget, metrics, approval, client readiness, implementation capacity, or stakeholder names

1 point:

- makes mild unsupported assumptions but marks them as assumptions

0 points:

- invents material facts and treats them as project state

## Expected Mode Results

Mode A: No FLG

Expected weaknesses:

- likely to ask for context again
- may default to a generic AI transformation proposal
- may miss why scope was narrowed

Mode B: Raw History

Expected weaknesses:

- can find the facts but may over-weight the later ambition request
- may confuse positioning ambition with delivery expansion
- may summarize too much instead of producing a revision plan

Mode C: FlowGrid Context Pack

Expected strengths:

- should correctly separate confirmed pilot scope from pending ambition input
- should avoid broad transformation roadmap as the main plan
- should frame ambition without expanding delivery scope
- should identify evidence needed to expand later

## Pass Threshold

A response passes this scenario if it scores at least 10/14 and does not commit either critical failure:

- treats ambition concern as confirmed scope expansion
- recommends broad AI transformation roadmap as the main proposal without new evidence
