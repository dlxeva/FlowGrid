# Dev Log 003: The Ledger Is the Truth; the Index Is a Cache

## What happened

FlowGrid stores formal decisions in `DECISIONS.md` and keeps derived evidence
data in `evidence_index.json`.

We found that a decision written directly to the ledger could be visible in
the decision list while its evidence was absent from the Context Pack. The
index was created as a side effect of one review path, so it was incomplete
for other valid write paths.

## Why it mattered

An index is meant to make project state faster to query. If it silently becomes
the only version that downstream tooling trusts, it becomes a hidden source of
truth.

That breaks a central FlowGrid promise: project files should remain readable,
auditable, and recoverable without trusting an opaque runtime cache.

## What changed

FlowGrid treats the ledger as the canonical record and rebuilds derived source
data from it.

- `flg reindex` reconstructs the provenance index from formal ledger state and
  available source artifacts.
- `flg doctor --strict` checks decision/index consistency and reports broken
  source references.
- `flg trace` follows a decision back through its ledger anchor, review action,
  patch, capture, or raw session when that material exists.

## Evidence

The FlowGrid project currently passes strict integrity checks with its formal
decisions indexed and no missing or broken Source Episodes. Regression tests
cover both deterministic index construction and a deliberately broken source
reference.

## What remains open

Rebuilding an index cannot invent raw evidence that was never captured. Older
manual decisions may have a ledger anchor but no verbatim source conversation.
That is an honest provenance boundary, and why reliable source capture remains
separate work.
