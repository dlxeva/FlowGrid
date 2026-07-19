# Private Asset Migration Map

| Original Path | Destination | Public Replacement | Migration Status |
|---|---|---|---|
| `docs/known-issues/no-cross-file-consistency-guard.md` (original) | `flowgrid-lab-export/dogfood/no-cross-file-consistency-guard.md` | Sanitized version kept at original path (project identity redacted, decision text generalized, username path removed) | ✅ Done |
| `docs/known-issues/merged-patch-stale-pending-state.md` (username) | N/A (light sanitization only) | Sanitized in place: username → `<your-workspace>`, added v0.3.0 resolution note | ✅ Done |

## Notes

- No other tracked files required migration.
- The private export lives at `../flowgrid-lab-export/` (sibling of the public repo).
- The public version does not depend on any content in the private export.
- Git history was not rewritten. The original content of the sanitized file
  exists in prior commits but does not contain credentials or legally
  protected data — it is internal dogfood project context that was redacted
  for cleanliness, not for security reasons.
