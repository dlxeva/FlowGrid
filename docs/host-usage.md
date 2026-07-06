# FlowGrid in AI Hosts

## Core Idea

FlowGrid is not meant to replace Codex, Claude, OpenClaw, Hermes, or any other AI agent work product.

It is meant to give those hosts a **local project state layer**.

The intended model is:

- **Natural language is the user interface**
- **FlowGrid CLI is the execution and state-write layer**

In other words:

- the user keeps talking naturally in the AI host they already use
- the AI host decides when to call `flg`
- FlowGrid turns that work into durable local project state

## What the User Should Feel

The user should not feel:

- “I am learning a new command-line tool”
- “I must manually maintain a project accounting system”

The user should feel:

- “my project state is being kept in sync”
- “I can come back later without re-explaining everything”
- “important judgments are getting captured instead of disappearing into chat”

## Best-Fit Host Model

FlowGrid currently fits best as a host-integrated workflow in:

- Codex
- Claude / Claude Code
- OpenClaw
- Hermes
- any AI agent work product that can read files and run shell commands

It is **not** optimized around the assumption that end users will operate the CLI directly all day.

## Natural Language to CLI Mapping

### Start a project

User says:

- “Start a new strategy project with FLG.”
- “Create a FlowGrid project for this proposal.”

Host should call:

```bash
flg init "Project Name" --template strategy
```

### Clarify framing

User says:

- “Before we write the proposal, help me clarify the framing.”
- “Check what this project is still missing.”

Host should call:

```bash
flg frame
```

### Close out a work session

User says:

- “Close out this session.”
- “Turn this meeting into a patch, don’t overwrite the ledger yet.”

Host should:

1. save raw session notes or transcript under `.flg/sessions/`
2. call:

```bash
flg closeout --transcript .flg/sessions/<session-file>.md
```

### Review candidate decisions

User says:

- “Review the candidate decisions.”
- “Accept the decisions from that patch.”

Host should call:

```bash
flg review --patch <patch-file>
```

### Merge the rest of the patch

User says:

- “Merge the patch.”
- “Apply the reviewed changes.”

Host should call:

```bash
flg merge --patch <patch-file>
```

### Resume a project

User says:

- “I’m back, help me pick this project up again.”
- “Recover the current project state before we continue.”

Host should read:

- `SNAPSHOT.md`
- `FRAMING.md`
- `DECISIONS.md`
- `GOAL_EVOLUTION.md`
- `ANCHORS.md`

And may call:

```bash
flg status
flg handoff
flg export-handoff
```

## Host Responsibilities

An AI host integrating FlowGrid should do three things well:

### 1. Keep session input raw

FlowGrid `closeout` should ingest:

- raw meeting notes
- raw transcripts
- raw discussion logs
- `.flg/sessions/` files

It should **not** feed:

- `PROGRESS.md`
- `SNAPSHOT.md`
- `DECISIONS.md`
- `README.md`

back into `closeout`, because those files are already interpreted ledger state.

### 2. Separate discussion from ledger

The host may discuss broadly with the user, but only call `flg` when it is time to:

- initialize
- frame
- close out
- review
- merge
- resume

### 3. Preserve review boundaries

The host should not silently convert candidate decisions into formal truth.

The expected sequence is:

1. `closeout`
2. `review`
3. `merge`

## Recommended First-Run Experience

For a real first-time user inside Codex / Claude / OpenClaw / Hermes:

1. Choose a new, real project
2. Initialize with a role template
3. Fill enough of `FRAMING.md` to move
4. Work naturally in chat
5. Save the session to `.flg/sessions/`
6. Run `closeout`
7. Run `review`
8. Run `merge`
9. Return later and try to resume from files alone

If that flow works, the user has experienced FlowGrid as intended.

## Product Framing

So the product should be described less as:

> a CLI for non-coding work

and more as:

> an AI-native local project protocol for non-coding knowledge work

The CLI is important.
But the deeper product is the protocol that different AI hosts can call into.