# Dev Log 001: A Candidate Is Not a Decision

## What happened

We ran `closeout` on a project discussion after a positioning review. It
extracted five candidate decisions. Three were actually priority-list items,
one repeated an existing decision, and none had a rationale, rejected
alternative, or reversal condition.

`review --accept-all` then wrote them into `DECISIONS.md`.

The failure was not that an agent missed a useful detail. It created formal
project state from a work plan that nobody had authorized as a decision.

## Why it mattered

Later agents read `DECISIONS.md` as reviewed project truth. Empty entries made
the ledger harder to trust and gave an agent material it could mistake for a
real commitment.

This is a common failure mode for long-running Agent work: a fluent extraction
can make a plausible candidate look more certain than its source warrants.

## What changed

FlowGrid now identifies a shell decision when its rationale, alternatives, and
rejection rationale are all absent.

- `closeout` retains the candidate for audit, but marks it low confidence.
- `review --accept-all` skips shell decisions instead of writing them into the
  formal ledger.
- Interactive review keeps a human override for the rare case where a concise
  decision is still valid.

The same shell check is applied to keyword, LLM, and Hermes extraction paths.

## Evidence

Regression coverage verifies that shell candidates are flagged and skipped by
automatic acceptance, while decisions with actual reasoning can still be
accepted. The original polluted patch was also retained as audit evidence for
the failure mode.

## What remains open

A nearby but unrelated rationale can still make a weak candidate look rich to a
simple context-window extractor. Fixing that needs semantic attribution, not a
smaller text window. We are keeping this as an observed boundary rather than
claiming automatic decision extraction is solved.
