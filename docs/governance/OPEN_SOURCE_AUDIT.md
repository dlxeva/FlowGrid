# FlowGrid Open-Source Audit Report

**Date:** 2026-07-15
**Branch:** `chore/open-source-boundary-v1`
**Base commit:** `3ab000e`
**FlowGrid version:** 0.3.0
**Test count:** 113 passed
**LICENSE file present:** No (prior to this PR)
**pyproject.toml license:** MIT

> This is a historical audit snapshot. Its file count and test count describe
> the audited base commit above, not later FlowGrid releases.

---

## Audit Methodology

All 92 Git-tracked files were classified as PUBLIC, PRIVATE, or REVIEW.
Full scan for credentials, real project names, real user data, and proprietary
learning assets was performed.

---

## Classification Summary

| Classification | Count | Action |
|---|---|---|
| PUBLIC (keep) | 89 | No change |
| PRIVATE (migrate) | 1 | Sanitized in place; original migrated to `flowgrid-lab-export/` |
| REVIEW (sanitized) | 2 | Light sanitization, kept public |

---

## Files Requiring Action

### PRIVATE — sanitized and original migrated

| Path | Issue | Action Taken |
|---|---|---|
| `docs/known-issues/no-cross-file-consistency-guard.md` | Contained real dogfood project name ("FLG东莞验证"), real decision content, real engagement context, and real Windows username in a path. | **Sanitized** in place: project identity redacted, real decision text generalized, username path replaced. **Original** migrated to `../flowgrid-lab-export/dogfood/`. |

### REVIEW — sanitized, kept public

| Path | Issue | Action Taken |
|---|---|---|
| `docs/known-issues/merged-patch-stale-pending-state.md` | Contained real username ("夕颜") in Windows path and reference to specific competition workspace. | **Sanitized**: username replaced with `<your-workspace>`, competition path generalized, added note that issue was resolved in v0.3.0. |
| `.gitignore` | Did not ignore `.flg/state.json`, `.flg/captures/`, `.flg/sessions/`, `.flg/context/`, `.flg/exports/`. Latent footgun for downstream users. | **Fixed**: comprehensive `.flg/` and private-asset ignore rules added. |

---

## Credential Scan Result

**CLEAN.** No hardcoded credentials, API keys, tokens, passwords, real emails, or
personally identifiable information found in any tracked file. All API access
in `src/flg/llm_client.py` uses environment variables (`os.getenv`).

---

## Real Project Name Scan Result

**CLEAN** (after sanitization). None of the flagged real project names
("人工智障", "赛格", "健康管理", "Day1CJ", "风投平台") appear in any tracked
file. "东莞" appeared only in the now-sanitized known-issues file.

---

## History Risk Assessment

**No `HISTORY_REWRITE_REQUIRED`.** The sanitized content in known-issues files
is project-internal dogfood data (not credentials or legally protected data).
The original content is preserved in the private export and can be referenced
if needed. Git history is not being rewritten.

---

## Post-Audit State

All 92 tracked files are now classified PUBLIC after sanitization.
No credentials, no real user data, no real project names remain in the
public working tree. Test count unchanged at 113 passed.
