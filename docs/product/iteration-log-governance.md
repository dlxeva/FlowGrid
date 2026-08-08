# Iteration Log Governance

## Canonical source

`ITERATION_LOG.md` in the FlowGrid code repository is the canonical product
iteration log. New product observations, confirmed recurring failures, fixes,
and validation boundaries are written there first.

Project or Vault copies may preserve historical source material, but they are
not parallel write targets. A generated mirror must identify its source commit
and generation time.

## Legacy sources

The following sources contain useful history and must not be deleted during
migration:

- the project Vault's historical `ITERATION_LOG.md`;
- iteration-log changes on legacy FlowGrid worktrees or branches;
- raw sessions, captures, patches, and evaluation reports linked by an entry.

Legacy records are migrated selectively when they change current product
priority, supply repeated evidence, or document a shipped fix. Migration keeps
the original date, status, and source location. It does not copy private project
names into public artifacts without redaction.

Public entries refer to private legacy evidence through a redacted alias such as
`vault@2026-08-04#112` or `dev-worktree@2026-07-18#14`. A bare legacy number is
not sufficient because old logs reused numbers.

## Stable entry IDs

New records use `FLG-ITER-YYYYMMDD-NN`. Existing `发现 N` labels remain readable
historical text but are not extended. This avoids collisions between old log
copies and permits a migrated entry to cite its former label.

## Status and promotion

- `observed`: one bounded occurrence or incomplete evidence;
- `confirmed`: repeated across projects, or one high-impact reproducible defect;
- `fixing`: an isolated candidate exists and has an explicit acceptance test;
- `fixed`: the relevant tests pass and the change is linked to a commit or PR;
- `wontfix`: the boundary is explicit and the reason is retained.

Changing an entry's status requires the evidence to be visible in the same
entry or through a stable repository link. A proposal or implementation claim
does not by itself make an issue `fixed`.

## Acceptance checks

1. Agents starting from any mapped FlowGrid runtime can locate the canonical
   log from the repository root.
2. New entries have unique stable IDs.
3. Vault history remains recoverable but is not silently merged or overwritten.
4. Current-state documentation links to the canonical log and distinguishes
   implemented fixes from migration backlog.
