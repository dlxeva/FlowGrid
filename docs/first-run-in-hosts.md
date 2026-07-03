# First Run in AI Hosts

## Goal

This script is for the most realistic first-time FlowGrid experience:

- stay inside the AI host you already use
- talk naturally
- let the host call `flg`
- use local files as the durable project state

This is the intended product experience in Codex, Claude, OpenHands, Hermes, or any similar AI agent work product.

## Choose the Right First Project

Pick a project that is:

- new or lightly started
- real enough to continue tomorrow
- judgment-heavy
- likely to require interruption and resume

Good first examples:

- a homepage information architecture
- a proposal draft
- a marketing campaign structure
- an operations mechanism design
- a solution framing memo

Do **not** start with:

- a huge historical archive
- a mature long-running project
- a pure engineering repo
- a random note-taking folder

## First-Run Script

### Step 1: Start naturally in the host

Say something like:

- “Use FLG to start this as a strategy project.”
- “Create a FlowGrid project for this campaign.”
- “Let’s run this project in FLG from the beginning.”

Expected host action:

```bash
flg init "Project Name" --template <strategy|marketing|operations|solution>
```

### Step 2: Clarify framing

Say:

- “Before we write anything, help me clarify the framing.”
- “Check what this project is still missing.”

Expected host action:

```bash
flg frame
```

Fill enough of `FRAMING.md` to move.
Do not wait for perfect language.

### Step 3: Work in natural language

Continue in the host as you normally would:

- discuss options
- make decisions
- revise direction
- collect constraints

Do **not** think of this as “using a CLI”.
Think of it as ordinary AI work with project state capture in the background.

### Step 4: Save a raw session file

At the end of a work segment, save raw notes under:

```text
.flg/sessions/
```

Examples:

- `.flg/sessions/2026-07-03-homepage-iteration.md`
- `.flg/sessions/2026-07-03-proposal-review.md`

Important:

- use raw discussion notes
- use meeting transcript text
- do not use `PROGRESS.md`, `SNAPSHOT.md`, or `DECISIONS.md`

### Step 5: Close out the session

Say:

- “Close out this session.”
- “Turn this session into a patch, but don’t overwrite the ledger.”

Expected host action:

```bash
flg closeout --transcript .flg/sessions/<session-file>.md
```

### Step 6: Review candidate decisions

Say:

- “Review the candidate decisions.”
- “Accept the real decisions into the ledger.”

Expected host action:

```bash
flg review --patch <patch-file>
```

### Step 7: Merge the rest

Say:

- “Merge the patch.”
- “Apply the reviewed updates.”

Expected host action:

```bash
flg merge --patch <patch-file>
```

### Step 8: Leave and return later

Come back later without relying on old chat context.

Start from:

- `SNAPSHOT.md`
- `FRAMING.md`
- `DECISIONS.md`
- `GOAL_EVOLUTION.md`
- `ANCHORS.md`

And optionally:

```bash
flg status
flg handoff
flg export-handoff
```

## What Success Feels Like

The first run is successful if:

1. you did not need to re-explain the whole project after returning
2. the important judgment shifts were captured
3. the project state lives in files, not just in chat
4. you still felt like you were using your normal AI host, not switching to a new workbench

## What Usually Goes Wrong

### Mistake 1: Feeding structured ledger files into `closeout`

Do not use:

- `PROGRESS.md`
- `SNAPSHOT.md`
- `DECISIONS.md`
- `README.md`

These are already interpreted state.

### Mistake 2: Skipping `review`

If you skip review, your most valuable asset—decision continuity—lands too loosely.

### Mistake 3: Starting with a giant legacy project

FlowGrid is easiest to feel correctly on a new or lightly started real project.

## Short Version

FlowGrid is working as intended when:

- natural language happens in the host
- structured state happens in files
- `flg` is called at the right moments
- returning later feels easier than before
