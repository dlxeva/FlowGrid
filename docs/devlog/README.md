# FlowGrid Dev Log

These are public records of implementation failures that changed FlowGrid's
protocol or code. They are not release notes and they are not case studies
written after a success.

Each entry answers five questions:

1. What failed in a real or controlled project workflow?
2. Why could that failure mislead a later agent or project owner?
3. What did FlowGrid change?
4. What evidence verifies the change?
5. What does the change still not prove?

Dogfood project identities, raw conversations, and private evaluation material
are deliberately omitted. The public record keeps the failure mechanism and
the product boundary.

## Published

- [001 - A candidate is not a decision](./001-candidate-is-not-a-decision.md)
- [002 - Review must happen before a candidate reaches startup context](./002-review-before-context.md)
- [003 - The ledger is the truth; the index is a cache](./003-ledger-is-truth-index-is-cache.md)

## Next candidates

These are likely future topics, not commitments or claims that the problems
are already solved.

- Why a complete Context Pack may still lose to short, clean raw history.
- Why a host integration needs raw-session capture, not only a better parser.
- Why an installed Agent Skill drifting from the repository version can reopen
  a resolved safety problem.
