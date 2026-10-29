# Changelog

## 0.4.0a1 (2026-10-29)

First v0.4 prerelease. This version identifies the implemented continuation and
review contracts; broader host reliability and long-term usefulness remain under
validation. It is not a stable 0.4.0 release.

- Record actual source-review spans, byte versions, affected judgments and
  processing history; preserve compact review notices across contexts and handoff.
- Distinguish unreviewed candidates, reviewed evidence waits, reviews triggered
  by declared dates or changed references, and explicit closure reasons.
- Preserve candidate status, original claims and history. Neither age nor drift
  approves or closes a judgment. Auto-confirm cannot bypass explicit follow-up.
- Keep legacy waits and historical closures distinguishable without inventing
  missing evidence or closure reasons. Filter before bounded display limits.
- Suppress obsolete candidate claims when evidence cannot be validated; keep
  source/work views and current-action date checks separate from formal approval.
- Include the accumulated decision relations, read-only impact analysis,
  provenance, work-view freshness, attribution safeguards and Windows hardening
  developed since the package last reported 0.3.0.
- Align package metadata, Python import and CLI version. `status` displays the
  installed runtime version separately from the project's recorded version;
  existing project files are not migrated merely to change a version display.
- Preserve literal UTF-8 bytes in atomic text writes on Windows, including
  existing CRLF bodies, so declared review hashes and exact retries remain valid.

Detailed private-project inputs remain private. Public tests use synthetic
fixtures and bounded, redacted evidence reports.

## 0.3.0

Previous package version. Subsequent feature development retained this number;
historical evaluations therefore also identify source commits and scope.
