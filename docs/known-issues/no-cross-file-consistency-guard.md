# Known Issue: No Cross-File Consistency Guard

## Status

Non-blocking, but silently degrades project truth over time.

Observed during real-project maintenance of a FlowGrid dogfood project (identity redacted), after migration from Windows to macOS.

## Symptom

Four independent inconsistencies were found in a project that `flg status` and `flg state-schema` both reported as healthy (✅ 标准 / schema_health = ok):

1. **Stale decision count.** `state.json` field `decisions_count` was lower than the actual number of entries in `DECISIONS.md`. The count had never been updated since project creation.

2. **Duplicate decision ID.** Two separate decisions shared the same ID (e.g. `D-010`). This breaks `flg evidence D-010`, which uses `find()` and always returns the first match. The second decision is unreachable by evidence lookup.

3. **Stale `current_stage`.** `state.json` still showed a stage from several days prior, but the project had since produced newer deliverables. Multiple days of progress were never reflected in state.

4. **Dead path reference.** `state.json` `pending_patches[].path` still pointed to a pre-migration Windows path. After migration to macOS the path is unreachable, but no command flagged it.

5. **Empty patch from frame false-positive.** `flg frame` generated a patch claiming "FRAMING.md has 0/10 fields filled", but FRAMING.md was actually fully populated. Root cause: `frame.py` `REQUIRED_FIELDS` regex matches English headings (`## Problem Statement`, `## Goals`), but this project's FRAMING.md uses Chinese headings. The empty patch sat in `pending_patches` indefinitely because nothing could merge meaningful content out of it.

## Root Cause Analysis

These are not five separate bugs. They share one root cause:

**FLG CLI validates structure (does the field exist?) but never validates value correctness or cross-file consistency.**

| Issue | What CLI checks | What it should check |
|---|---|---|
| Stale count | `decisions_count` is an extension field, preserved as-is | Count `## D-NNN` in DECISIONS.md, compare to stored value |
| Duplicate ID | `decision add` uses `max(findall(r"D-(\d+)")) + 1` for new IDs | Before adding, scan for existing ID collision |
| Stale stage | `current_stage` is a core field, displayed verbatim | Compare `updated_at` / `last_closeout_at` age to now, warn if stale |
| Dead path | `pending_patches[].path` stored from whatever was passed | Verify file existence at read time |
| Frame false-positive | Regex matches English headings only | Add Chinese heading aliases or make matching locale-aware |

The pattern: every command reads a single file in isolation and trusts its content. No command cross-references state.json against the ledger files it claims to describe.

## Likely Fix

### Minimal (detect, don't auto-fix)

Add a `flg doctor` command that cross-validates:

1. **Decision count match**: `len(re.findall(r"^## D-\d{3}", DECISIONS.md))` vs `state["decisions_count"]`.
2. **Decision ID uniqueness**: scan for duplicate `D-NNN` headings.
3. **Path reachability**: for each `pending_patches[].path`, check `Path(path).exists()`.
4. **Stage freshness**: warn if `updated_at` older than N days since last closeout.
5. **Frame heading compatibility**: if FRAMING.md exists, check whether its headings match any pattern in `REQUIRED_FIELDS` (including a Chinese alias map). If 0/10 match but the file has substantial content, warn about locale mismatch instead of generating a patch.

Note: item 5 (Chinese heading support) was partially addressed in v0.3.0 (frame now accepts `#{2,3}` heading levels for Explicit Requirements / Real Needs Hypothesis). Full Chinese heading alias support remains open.
