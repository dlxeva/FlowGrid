# Judgment Impact v0

FlowGrid can derive which formal decisions may need revalidation when one
judgment changes:

```bash
flg impact D-047
```

The report traverses explicit `supersedes`, `conflicts_with`, `supports`, and
`depends_on` relations. It returns a bounded list of revalidation candidates
and the shortest relation path that reached each candidate.

## Authority Boundary

Impact analysis is a read-only derived view. It does not:

- change a formal decision status;
- decide that a related judgment is wrong;
- promote new evidence into the ledger;
- replace owner review.

The formal decision log remains the human-readable source of truth. The impact
view can always be rebuilt from explicit relations in `DECISIONS.md`.

## Propagation Rules

- Incoming relations propagate toward the decision that owns the relation.
  If `D-048 depends_on D-047`, a change to `D-047` makes `D-048` a review
  candidate.
- Outgoing `supersedes` and `conflicts_with` relations also propagate to their
  targets because the changed judgment may alter the target's current standing.
- Outgoing `supports` and `depends_on` do not propagate toward prerequisites.
  A change to a dependent does not automatically invalidate what it depended on.

The result is intentionally conservative. It is a review queue, not an
automatic truth-maintenance engine.
