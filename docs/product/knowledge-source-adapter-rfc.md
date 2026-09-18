# Knowledge Source Adapter RFC

Status: proposed

## Decision

FlowGrid will not become a Wiki, documentation site generator, editor, search
engine, or publishing system. It will expose a small provider-neutral contract
for tracking the continuity of knowledge that already lives elsewhere.

The existing `flg wiki` surface remains a backwards-compatible
`filesystem_markdown` adapter until a migration path is validated.

## Problem

Long-running projects often accumulate hundreds of documents. Existing tools
can render, search, edit, and publish them. The continuity problem starts when a
human or agent cannot tell:

- which source version informed a judgment;
- whether the source changed afterwards;
- where the relevant passage can be reopened;
- which reviewed judgments may require revalidation.

FlowGrid should solve those questions without copying an external knowledge
system into the formal ledger.

## Boundary

FlowGrid owns:

- provider and source identity;
- stable source and page IDs;
- version or content fingerprints;
- bounded locators;
- freshness and drift status;
- explicit links from sources to reviewed judgments;
- derived revalidation candidates after source drift.

External tools own:

- authoring and editing;
- information architecture and page navigation;
- backlinks and graph presentation;
- full-text search UI;
- collaboration, permissions, and authentication;
- hosting and publication.

## Proposed contract

Each configured source returns a deterministic manifest:

```json
{
  "provider": "filesystem_markdown",
  "source_id": "project-docs",
  "authority": "reference",
  "version": "git:0123456",
  "generated_at": "2026-09-19T00:00:00Z",
  "items": [
    {
      "item_id": "docs/product/brief.md",
      "locator": "docs/product/brief.md#scope",
      "fingerprint": "sha256:...",
      "title": "Product Brief",
      "related_judgments": ["D-042"]
    }
  ]
}
```

Required adapter operations:

1. `probe`: confirm that the provider is reachable without modifying it.
2. `manifest`: return bounded metadata and fingerprints, not full content.
3. `diff`: compare the current manifest with the accepted snapshot.
4. `resolve`: turn an item ID or locator into an inspectable source pointer.

Adapters are read-only. Formal writes continue through the existing FlowGrid
review and owner-gate paths.

## Initial providers

| Provider | Intended use | FlowGrid integration |
|---|---|---|
| `filesystem_markdown` | Existing project Markdown or Git-backed docs | Native manifest, SHA, relative locator |
| `mkdocs` | Structured documentation sites | Read source Markdown and optional nav config; do not parse generated HTML by default |
| `quartz` | Obsidian-style notes, wikilinks, and digital gardens | Read source notes and stable paths; leave graph/search to Quartz |
| `external_wiki_api` | Hosted collaborative Wiki systems | Record immutable page/version IDs and URLs; require an explicit credential boundary |

Docusaurus and other static-site generators fit the same source/build-output
split and do not require a dedicated core abstraction initially.

## Freshness semantics

- `current`: provider version and accepted manifest match.
- `drifted`: added, changed, or removed items exist.
- `unreachable`: the provider cannot be probed; no freshness claim is made.
- `unversioned`: a provider is reachable but cannot provide a trustworthy
  version or item fingerprint.

`drifted` does not invalidate a judgment automatically. It produces a bounded
review candidate containing the changed source IDs and explicitly related
judgments. Promotion, replacement, or rejection remains an owner decision.

## Compatibility and migration

1. Keep `.flg/wiki.json` and `flg wiki` working.
2. Interpret them internally as one `filesystem_markdown` source.
3. Introduce a provider-neutral config only after round-trip compatibility and
   a real-project migration dry run pass.
4. Do not copy or rewrite existing documents during migration.

## Acceptance criteria

The first provider-neutral slice is acceptable only when:

- a legacy Wiki configuration produces the same accepted manifest;
- unchanged sources remain deterministic across repeated runs;
- added, changed, and removed items are distinguished;
- an unreachable provider never reports `current`;
- source drift identifies only explicitly related judgments;
- no source content enters formal truth without review;
- startup context receives only a bounded status and expansion pointer;
- all tests use synthetic, privacy-safe fixtures.

## Validation order

1. Render one sanitized Markdown corpus with MkDocs Material and Quartz.
2. Compare setup cost, navigation, search, backlink needs, and maintenance.
3. Keep the better presentation tool external to FlowGrid.
4. Implement only the provider-neutral manifest boundary proven necessary by
   the comparison.

