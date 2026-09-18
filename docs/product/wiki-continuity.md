# Knowledge-Source Continuity

FlowGrid can index an existing Markdown knowledge source without moving or rewriting its source documents. The current `flg wiki` command is the first compatibility adapter; it is not the start of a FlowGrid-owned Wiki product.

This layer is opt-in. It gives agents a compact map of available knowledge, its freshness, and its relationship to reviewed decisions. Wiki content remains reference material. It does not become confirmed project truth until it passes through the normal FlowGrid review path.

## Product boundary

FlowGrid owns continuity questions:

- Which knowledge source and version was used?
- Has that source changed since it was accepted?
- Which reviewed judgments cite it and may require revalidation?
- What bounded locator should the next human or agent expand?

FlowGrid does not own authoring, page trees, backlinks, full-text search UI,
publishing, collaboration, permissions, or hosting. Those concerns belong to
existing documentation and Wiki systems. A future source-adapter contract may
cover filesystem Markdown, generated documentation sites, or external Wiki
APIs while preserving the same authority boundary.

## Enable it

From an existing FlowGrid project:

```bash
flg wiki init --root docs --home docs/README.md
```

This creates:

- `.flg/wiki.json`: project-local wiki configuration
- `.flg/context/wiki_manifest.json`: page metadata, SHA-256 hashes, and relationships

No wiki page is moved or rewritten.

## Maintain it

```bash
flg wiki status
flg wiki build
flg context --mode resume
```

`wiki status` is read-only. It reports added, changed, and removed Markdown pages. `wiki build` accepts the current wiki snapshot and refreshes the manifest.

When configured, the Context Pack includes a small Project Wiki section with the home page, page count, freshness, and a bounded list of relevant index pages. It does not copy the full wiki into startup context.

## Optional page metadata

A Markdown page may use YAML frontmatter:

```yaml
---
id: W-MARKET-001
type: index
status: active
authority: reference
owner: research
related_decisions:
  - D-042
related_outcomes:
  - O-007
source_ids:
  - SRC-019
last_reviewed: 2026-09-02
review_after: 2026-12-01
---
```

Pages without frontmatter still receive a stable path-derived ID and are indexed normally.

## Authority boundary

The knowledge source answers: "Where is the relevant material?"

FlowGrid answers: "Which version informed the project, has it changed, and what may need review?"

The formal ledger answers: "What has been reviewed and may guide future action?"

A changed wiki page makes the manifest stale. It does not silently rewrite or invalidate a decision. The operator can then inspect the changed source and decide whether a judgment requires revalidation.
