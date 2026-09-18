# Judgment Impact Real-Ledger Replay — 2026-09-19

## Question

Does `flg impact` produce obvious false-positive revalidation candidates on
FlowGrid's current formal decision graph?

## Scope

- Source: the current FlowGrid formal `DECISIONS.md` ledger.
- Baseline: public `master` at `fcac7b4`.
- Graph size: 48 formal decisions and 3 explicit relation edges.
- Method: read-only CLI replay; no ledger status or relation was changed.

The three declared edges were:

| Source | Relation | Target |
| --- | --- | --- |
| D-047 | `supersedes` | D-037 |
| D-048 | `supports` | D-044 |
| D-048 | `depends_on` | D-047 |

## Frozen Interpretation

The input to `flg impact` means that a decision's evidence, validity, or formal
standing may have changed materially. It does not mean that wording or metadata
was edited without changing the judgment.

Under that contract:

- a dependent should be reviewed when its prerequisite changes;
- a supporting decision should be reviewed when the decision it reinforces changes;
- a superseding decision should be reviewed when the decision it replaced changes;
- a superseded predecessor may be reviewed when its superseding decision changes,
  because its historical standing or fallback relevance may need owner judgment;
- none of these reviews automatically restore, reject, or rewrite a decision.

## Results

| Changed decision | Derived candidates | Expected | Result |
| --- | --- | --- | --- |
| D-037 | D-047 at depth 1; D-048 at depth 2 | yes | pass |
| D-044 | D-048 at depth 1 | yes | pass |
| D-047 | D-037 and D-048 at depth 1 | yes | pass |
| D-048 | none | yes | pass |

Across these four roots, the command emitted five candidate instances. Manual
relation-semantic review found zero obvious false positives and zero missing
candidates under the frozen material-change interpretation.

## Decision

Do not add automatic state transitions, model inference, or a `change_kind`
parameter from this sample. The current conservative read-only queue is useful
and its owner gate remains necessary.

## Limits

This is one real ledger with only three edges. It contains no `conflicts_with`
edge, no multi-parent dependent, no cycle, and no larger graph where candidate
volume could become noisy. The result validates this graph and these relation
semantics. It does not establish a general false-positive rate for FlowGrid.

The next useful validation requires another privacy-safe real ledger with a
larger relation graph, or newly accumulated FlowGrid relations. Synthetic edge
count alone should not be presented as product evidence.
