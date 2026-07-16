---
name: flowgrid-operator
description: >-
  Operate FlowGrid (FLG) as a durable project-state layer through natural-language
  conversation. Use when the user asks to start, manage, resume, close out, audit,
  hand off, or recover a rationale-heavy business, strategy, operations, marketing,
  or solution project; when they mention FLG, FlowGrid, project decisions, decision
  log, or project state; or when a project needs durable decisions, evidence, next
  actions, and cross-session continuity.
---

# FlowGrid Operator

Use FlowGrid as a background protocol. The user talks in natural language; you
decide and execute the CLI calls. Do not tell the user to operate `flg` manually.

## Command and scope

Run `flg` from the target project root. The global command should be available
on PATH. If command lookup fails, use the venv directly:

```bash
flg version          # verify install
flg onboard          # first-run setup: env check + demo + skill install
```

Never initialize a project outside the user-requested project directory. Use
`--dir` to target a specific location:

```bash
flg init "Project Name" --type solution --dir /path/to/project
# Add --language en for an English-first formal ledger.
```

## Operating loop

### Start or adopt a project

For a request to run a project in FlowGrid:

1. Locate the project root and inspect its current state.
2. If `.flg/` is absent, audit then initialize:

   ```bash
   flg audit --report-only .
   flg init "Project Name" --type solution --background "concise factual background"
   ```

3. Run `flg frame`, report the material gaps, and maintain the framing with the user.

### Continue an FLG project

At the start of a new work segment in a project containing `.flg/`:

1. Run `flg status` — see pending patches and closed-patch summary.
2. Generate bounded startup state:

   ```bash
   flg context --mode resume --budget 4000
   ```

3. Read `.flg/context/startup.md` and active pending patches before proposing work.
4. Use `flg evidence <decision-id>` when the user challenges a recorded decision.

### Capture a work segment

When a meaningful discussion changes direction, constraints, decisions, evidence,
or next actions, run closeout on the raw discussion:

```bash
flg closeout --transcript path/to/raw-session.md
```

### Mandatory source-capture trigger

Do not rely on memory to reconstruct a meaningful work segment later. When a
session produces a direction change, important evidence, a rejected path, a
new constraint, or a candidate decision:

1. Preserve the raw discussion or notes immediately.
2. Run `flg closeout` before leaving the session or switching agents.
3. Treat the generated patch as internal candidate state and process it in the
   background; do not turn routine ledger maintenance into a user prompt.
4. If the host cannot access the raw transcript, preserve the notes that are
   available and report the missing source instead of claiming closeout is complete.

This is a host workflow rule: the user should not need to remember `session`
or `closeout` commands manually.

Closeout automatically archives an external raw transcript under `.flg/sessions/`.
Use `flg session save` first only when you need a stable custom filename:

```bash
flg session save path/to/raw-session.md --name <timestamp>-<topic>
flg closeout --transcript .flg/sessions/<timestamp>-<topic>.md
```

Use raw conversation notes. `flg session save` rejects structured ledger files by
default, so do **not** feed `PROGRESS.md`, `SNAPSHOT.md`,
`DECISIONS.md`, or `README.md` into `closeout` — those are already-structured
ledger files (closeout will refuse them unless you pass `--force`).

The raw session must contain only the verbatim discussion or unstructured notes.
Do not append an Agent-generated handoff, distilled signals, field labels such
as `Type`, `Owner`, or `Status`, or an extraction summary to the same file.
If a host has already appended such a section, keep the original file for audit
but create a clean raw copy before closeout. FLG also excludes recognized
generated summary sections from extraction without changing the raw source.

If no LLM API keys are configured, add `--no-llm` to force keyword-based extraction.

### Background review and merge

`closeout` output is an internal candidate state, not a user-facing approval
step. In the normal host-integrated flow:

1. Run `flg review --patch <patch-file> --report-only` in the background as an
   internal quality gate. It never interrupts the user or writes ledger state.
2. Run `flg review --patch <patch-file> --autonomous` only after that gate.
   Rich candidates with real reasoning are adopted into the ledger; shell
   candidates with no context remain pending and are not written as decisions.
3. If the host used real-time capture, run `flg capture review --auto-confirm`
   in the background; this only processes captures explicitly marked
   `confirmed` and leaves inferred captures pending.
4. Run `flg merge --patch <patch-file> --yes` in the background.

The user should continue speaking naturally. Report only material project
changes, unresolved ambiguity, or an external action that requires a decision.

Never silently promote a shell or ambiguous judgment into current truth. Do not
reintroduce rejected or superseded directions without new evidence.

### Autonomous continuation mode

When the user asks Codex to continue, take ownership of the next safe project
action instead of returning a menu of options. Inspect status, context, pending
patches, evidence, and the current goal; choose the smallest action that
reduces uncertainty or produces reusable evidence; execute it; then report the
result and next action.

Autonomous actions may include:

- running status, context, audit, doctor, reindex, tests, smoke tests, and
  disposable-copy evaluations;
- retiring stale patches when the ledger evidence clearly shows they are
  obsolete, preserving the audit trail;
- implementing low-risk bug fixes with regression tests;
- committing changes and opening or updating a PR;
- preparing and silently maintaining formal decision patches from clear raw
  evidence; preserve provenance and status for inferred or ambiguous items.

Stop and ask for confirmation only before:

- rewriting or migrating a real project's formal ledger;
- deleting source material or user data;
- publishing externally, changing permissions, spending money, or changing
  a production integration;
- choosing between materially different product or business directions.

Do not ask the user to choose between routine engineering steps. Make the
choice, record the basis, and surface the decision boundary in the report.

### Retire stale patches

When a patch is outdated (e.g. a frame patch generated before FRAMING.md was
rewritten by hand), retire it officially:

```bash
flg patch supersede <patch_id> --reason "replaced by newer framing"
flg patch discard  <patch_id> --reason "false positive"
```

These update both state.json and the patch file's status line. Retired patches
no longer trigger the `⚠ pending` warning in `flg status` and are excluded from
the Context Pack.

## What counts as a decision worth recording

Not every statement with a decision keyword is a real decision. Use this filter:

**Record (via closeout or capture):**
- Architecture-level choices (A vs B, picked one with a reason)
- Product mechanism discoveries (new interaction paradigm, core capability)
- Explicitly rejected directions (the rejection itself is high-value information)
- Design constraints that affect multiple components
- Inferred-but-unverified judgments (record as `inferred`, not `confirmed`)

**Do NOT record:**
- Routine bug fixes (unless the root cause is broadly representative)
- Single-file edits
- Temporary debugging steps
- Work-plan priority lists ("first priority: X, second priority: Y")

When unsure, prefer `flg capture add` (candidate, `inferred`) over
`flg decision add` (confirmed). Keep ambiguous candidates in the background
until stronger conversational evidence appears; do not interrupt the user just
to ask whether an internal ledger entry is correct.

## Natural-language mapping

| User intent | Action |
| --- | --- |
| "用 FLG 管理这个项目" / "start in FLG" | Audit, initialize/adopt, then frame. Add `--language en` when the formal ledger should be English-first. |
| "继续这个项目" / "resume" | `flg status`, `flg context`, then continue from reviewed state. |
| "这个项目还缺什么" / "what's missing" | `flg frame`; surface proof object, constraints, open questions. |
| "收口这次讨论" / "close out" | Run `flg closeout` on the raw session; external files are archived automatically. |
| "审核这轮判断" / "review" | `flg review --patch ...`; preserve status distinctions. |
| "合并这次变更" / "merge" | `flg merge --patch ... --yes` in the background. |
| "这个 patch 作废了" / "stale patch" | `flg patch supersede` or `flg patch discard`. |
| "给下一个人交接" / "hand off" | `flg handoff` or `flg export-handoff`. |
| "为什么当时这么决定" / "why this decision" | `flg evidence <decision-id>` and source inspection. |
| "检查账本一致性" / "doctor" | `flg doctor`; report drift without writing. |
| "重建证据索引" / "reindex" | `flg reindex`; rebuild from `DECISIONS.md`. |

## Report back

Report the project state in plain language: confirmed decisions, pending review,
newly created patch, material risks, and next action. Mention FLG only when it
helps the user understand project state or review a decision.
