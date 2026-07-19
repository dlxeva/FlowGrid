# FlowGrid in AI Hosts

## Core Idea

FlowGrid is not meant to replace Codex, Claude, OpenClaw, Hermes, or any other AI agent work product.

It gives those hosts a **local project-state context layer** for rationale-heavy, non-coding business projects.

The intended model is:

- natural language is the user interface
- the AI host decides when to call `flg`
- FlowGrid writes durable project state with explicit status and evidence
- FlowGrid generates bounded startup context for later agents
- FlowGrid preserves judgment status and evidence references

## What the User Should Feel

The user should feel:

- my project state is being kept in sync
- I can come back later without re-explaining everything
- important judgments are captured with reasons and status
- rejected directions do not keep coming back without new evidence
- a later agent can continue from the project state instead of reconstructing history

The user should not feel:

- I am learning a new command-line tool
- I must manually maintain a project accounting system
- every session starts from scratch

## Best-Fit Host Model

FlowGrid currently fits best as a host-integrated workflow in:

- Codex
- Claude / Claude Code
- OpenClaw
- Hermes
- any AI agent work product that can read files and run shell commands

It is not optimized around the assumption that end users will operate the CLI directly all day.

## Host Responsibilities

An AI host integrating FlowGrid should do six things well.

### 1. Preserve raw session input

FlowGrid `closeout` should ingest:

- raw meeting notes
- raw transcripts
- raw discussion logs
- `.flg/sessions/` files

Preserve speaker labels when the source has them (for example `User:` and
`Assistant:`). Background review uses these labels to distinguish a user or
client commitment from an agent-authored proposal.

The host should not feed interpreted ledger files back into closeout by default:

- `PROGRESS.md`
- `SNAPSHOT.md`
- `DECISIONS.md`
- `README.md`

Those files already represent interpreted project state.

### 2. Separate discussion from ledger

The host may discuss broadly with the user, but should call `flg` when it is time to:

- initialize
- frame
- close out
- review
- merge
- generate context
- retrieve evidence
- resume

### 3. Preserve internal state boundaries

The host must not turn routine ledger maintenance into a user-facing approval
ceremony. It should silently adopt clear, well-supported judgments only when
their source explicitly identifies a user or client commitment. It must keep
agent-authored, unattributed, ambiguous, or shell candidates pending with
their evidence.

Expected sequence:

```text
raw session -> closeout -> background review -> background merge -> context
```

### 4. Respect judgment status

The host should distinguish:

- confirmed decisions
- pending judgments
- assumptions
- rejected alternatives
- superseded judgments
- needs-recheck items

The host should not treat pending judgments as confirmed decisions.

The host should not revive rejected alternatives unless new evidence exists.

### 5. Prefer bounded context over raw history

When resuming a project, the host should prefer Context Pack over raw session replay.

Target command:

```bash
flg context --mode resume --budget 4000
```

Target output:

```text
.flg/context/startup.md
```

The Context Pack should tell the receiving agent:

- what the project is trying to prove
- what has been confirmed
- what is pending
- what assumptions are active
- what has been rejected
- what has been superseded
- what should happen next
- where evidence can be retrieved

### 6. Retrieve evidence when challenged

When the user asks why a judgment was made, the host should retrieve evidence instead of inventing rationale.

Future commands:

```bash
flg evidence <decision-id>
flg trace <decision-id>
```

## Natural Language to CLI Mapping

### Start a project

User says:

- “Start a new campaign project with FLG.”
- “Create a FlowGrid project for this client proposal.”
- “Set up FLG for this mechanism design project.”

Host should call:

```bash
flg init "Project Name" --template proposal
```

### Clarify framing

User says:

- “Before we write the proposal, help me clarify the framing.”
- “Check what this project is still missing.”
- “What exactly does this plan need to prove?”

Host should call:

```bash
flg frame
```

The host should pay special attention to:

- review object
- proof object
- current deliverable
- constraints
- open questions

### Close out a work session

User says:

- “Close out this session.”
- “Turn this meeting into a patch, don’t overwrite the ledger yet.”
- “Extract what changed from this discussion.”

Host should call closeout on the raw transcript:

```bash
flg closeout --transcript path/to/raw-session.md
```

External raw transcripts are automatically copied under `.flg/sessions/`. Use
`flg session save` first only when a stable custom archive filename is needed.

For a remote provider, the host must obtain explicit user authorization and
then pass both `--llm <provider>` and `--allow-remote-llm`. Configured API keys
do not opt a project in automatically.

Host should:

1. save raw session notes or transcript under `.flg/sessions/`
2. call:

```bash
flg closeout --transcript .flg/sessions/<session-file>.md
```

### Background candidate processing

The host normally performs this without interrupting the user. It first runs
an internal, non-writing quality gate:

```bash
flg review --patch <patch-file> --report-only
```

Then it processes eligible candidates in the background:

```bash
flg review --patch <patch-file> --autonomous
```

Only rich candidates with explicit user/client attribution are adopted into the
ledger with their source evidence. Agent-authored, unattributed, shell, or
ambiguous candidates remain pending and must not drive an irreversible external
action. Candidate risks and next actions remain in the patch until a separate
confirmation path exists.

### Merge the rest of the patch

The host then completes routine ledger maintenance without a prompt:

```bash
flg merge --patch <patch-file> --yes
```

### Generate startup context

User says:

- “I’m back, help me pick this project up again.”
- “Recover the current project state before we continue.”
- “Give the next agent the right context.”

Host should call:

```bash
flg context --mode resume --budget 4000
```

Then the host should read:

```text
.flg/context/startup.md
```

If `flg context` is not available yet, the host should fall back to:

```bash
flg status
flg handoff
```

and read:

- `SNAPSHOT.md`
- `FRAMING.md`
- `DECISIONS.md`
- `GOAL_EVOLUTION.md`
- `ANCHORS.md`
- active pending patches

### Retrieve evidence

User says:

- “Why did we decide this?”
- “Where did D-002 come from?”
- “Show me the source behind that judgment.”

Host should call, when available:

```bash
flg evidence D-002
flg trace D-002
```

If evidence commands are not available yet, the host should inspect:

- `DECISIONS.md`
- source patch in `.flg/patches/`
- source session in `.flg/sessions/`
- merge logs when available

## Recommended First-Run Experience

For a real first-time user inside Codex / Claude / OpenClaw / Hermes:

1. Choose a real fuzzy business project.
2. Initialize with a task-mode template.
3. Clarify review object and proof object.
4. Work naturally in chat.
5. Save the session to `.flg/sessions/`.
6. Run `closeout`.
7. Review candidate judgments.
8. Merge accepted project state.
9. Generate Context Pack.
10. Return later and resume from Context Pack.
11. Retrieve evidence for at least one decision.

If that flow works, the user has experienced FlowGrid as intended.

## Host Failure Modes

Hosts should avoid these failures:

### Failure 1: Raw-history restart

The host reads an entire transcript and starts summarizing instead of using reviewed project state.

### Failure 2: Pending-as-confirmed

The host treats candidate judgments from patches as formal decisions.

### Failure 3: Rejected alternative revival

The host re-suggests a direction that was already rejected without new evidence.

### Failure 4: Superseded judgment reuse

The host relies on an old judgment that a later decision replaced.

### Failure 5: Evidence invention

The host explains a decision with plausible reasoning that is not supported by project evidence.

## Product Framing

FlowGrid should be described as:

> a local project-state context engine for rationale-heavy, non-coding business projects

The CLI is the execution surface.

The deeper product is the agent-state contract that different AI hosts can call into.

## Related Product Docs

- [User Pain Model](./product/user-pain-model.md)
- [Context Pack Contract](./product/context-pack-contract.md)
- [Judgment Status Model](./product/judgment-status-model.md)
- [Eval Set v0](./product/eval-set-v0.md)
