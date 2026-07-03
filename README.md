# FlowGrid (FLG)

[English](./README.md) | [简体中文](./README.zh-CN.md)

> An AI-native local project protocol for non-coding knowledge work.
> Designed to work inside any AI agent work product, with natural language as the interface and local files as the source of truth.

![Stage](https://img.shields.io/badge/stage-v0.2.1--alpha-4c6ef5)
![Runtime](https://img.shields.io/badge/runtime-local--first-2b8a3e)
![Interface](https://img.shields.io/badge/interface-CLI%20%2B%20project%20protocol-495057)
![Tests](https://img.shields.io/badge/tests-58%20passed-2f9e44)

FlowGrid helps strategy, marketing, research, operations, and solution professionals turn vague business work into structured, auditable, and transferable project systems.

It keeps project memory in plain-text files, lets any AI agent work product continue from the same directory, and treats decisions, progress, and pending patches as first-class project state.

## Quick Links

- [Why it exists](#what-is-flowgrid)
- [30-second demo](#30-second-demo)
- [Who it is for](#who-is-it-for)
- [Quick start](#quick-start)
- [CLI commands](#cli-commands)
- [Protocol docs](./docs/protocol.md)
- [Host usage](./docs/host-usage.md)
- [Chinese README](./README.zh-CN.md)

## At a Glance

- **Local-first:** project truth lives in files, not chat memory
- **Host-agnostic:** works inside Codex, Claude, OpenHands, Hermes, or any agent shell that can read files and run commands
- **Continuity-first:** later agents and later sessions read the same ledger and pending patches
- **Decision-aware:** decisions store why, rejected options, and reversal conditions
- **Patch-first:** medium/high-risk updates stay reviewable before merge
- **Non-coder oriented:** built for briefs, proposals, planning, and judgment work

## 30-Second Demo

```bash
mkdir demo && cd demo
flg init "Launch Proposal" --type proposal --client "Client A"
flg frame
flg closeout --transcript meeting-notes.md
flg handoff
```

After that, you will have:

- a local project ledger: `PROJECT.md`, `FRAMING.md`, `DECISIONS.md`, `SNAPSHOT.md`, `PROGRESS.md`
- a protocol directory: `.flg/`
- reviewable pending changes in `.flg/patches/`
- a resumable handoff summary for the next session or agent

You can run that flow from Codex, Claude, OpenHands, Hermes, or any AI agent work product that can read files and run commands.

## What is FlowGrid?

FlowGrid (FLG) is an AI-native local project protocol for strategy, marketing, operations, and solution professionals.

It helps you turn vague business problems into structured, auditable, and transferable project systems.

## Who is it for?

- **Strategy professionals** defining project direction and goals
- **Marketing professionals** planning campaigns and content
- **Operations professionals** designing systems and processes
- **Solution professionals** translating client needs into deliverables

## How is it different from prompt workflows?

| Dimension | Prompt Workflow | FlowGrid |
|-----------|----------------|----------------|
| Scope | Single conversation | Full project lifecycle |
| Memory | AI memory (temporary) | Project files (persistent) |
| Truth source | Scattered across conversations | Unified project ledger |
| Auditability | Not auditable | Plain text, trackable |
| Portability | Tied to specific AI | Any local agent can continue |

## Why Decision Logs Matter

Your AI forgets your decisions every conversation. FLG doesn't.

`DECISIONS.md` doesn't just record *what* you decided — it captures *why* you decided, *what you rejected*, and *under what conditions you'd reverse the call*. This is the difference between a history log and a thinking tool.

Each decision entry uses a 9-field structure:

| Field | Purpose |
|-------|---------|
| `id` | Unique decision identifier |
| `date` | When the decision was made |
| `context` | The situation that triggered it |
| `decision` | What was decided |
| `rationale` | Why this over alternatives |
| `alternatives_rejected` | What was considered and ruled out |
| `reversal_conditions` | What would change this decision |
| `impact` | Expected consequences |
| `status` | Active / Superseded / Revisited |

Over time, this creates three forms of value:

- **Retrospective clarity** — revisit past decisions with full context, not just outcomes
- **Agent relay continuity** — any agent picking up your project sees the full decision history, not just the current state
- **Judgment compounding** — your reasoning patterns become explicit, transferable, and improvable

## Who is it NOT for?

Be honest: there are tools that already serve these users better. If you fit one of these, use them.

| Profile | Use this instead |
|---|---|
| Software engineer working in a git repo with code-agent team | [oh-my-codex (OMX)](https://github.com/Yeachan-Heo/oh-my-codex) — worktree-isolated multi-agent pipeline, MCP-backed state, `ralph`/`team`/`tdd` skills |
| Enterprise PM running structured sprint backlogs | [Atlassian AI Agents](https://www.atlassian.com/agile/project-management/ai-agents) — coordination, status sync, enterprise integration |
| Team lead running self-driving project workspaces | [Taskade Genesis / Workspace DNA](https://www.taskade.com/blog/autonomous-project-management) — 100+ integrations, prompt → running project |
| Solo non-coder wanting low-friction agent task execution | [Claude Cowork](https://www.scrum.org/resources/blog/claude-cowork-ai-agents-email-moment-non-coding-agile-practitioners) — packaging code-agent power for non-coders |

**FlowGrid's niche:** single-operator, non-coding knowledge work (marketing, strategy, research, creative ideation) where the deliverable is *decisions, drafts, briefs* — not code, not sprints, not running apps. Local-first, plain-text ledger, resumable project state, no SaaS, no team coordination layer.

If your work is "figure out what to do" rather than "do it at scale", FLG is for you.

## Installation

```bash
pip install -e .
flg version
```

## Development Mode

Run through the editable-installed console script:

```bash
pip install -e .
flg version
```

Run without installation by using the source tree directly:

```bash
PYTHONPATH=src python -m flg.cli version
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH="src"
python -m flg.cli version
```

## Quick Start

### 1. Initialize a project

```bash
mkdir my-project && cd my-project
flg init "My Project" --type proposal --client "Client Name"
```

This creates:
- `PROJECT.md` - Project overview
- `FRAMING.md` - Problem definition
- `DECISIONS.md` - Decision log
- `SNAPSHOT.md` - Current state
- `PROGRESS.md` - Progress log
- `.flg/` - FLG internal directory

### 2. Frame the problem

```bash
flg frame
```

This checks FRAMING.md for missing fields and generates a patch with suggested questions.

### 3. Close out a session

```bash
flg closeout --transcript path/to/transcript.md
```

This extracts decisions, risks, and progress from a transcript and generates a closeout patch.

Use raw meeting notes, session transcripts, or files under `.flg/sessions/`.
Do not use structured ledger files such as `PROGRESS.md`, `SNAPSHOT.md`, or `DECISIONS.md` as closeout input unless you explicitly know why and pass `--force`.

## Project Structure

```
my-project/
├── PROJECT.md
├── FRAMING.md
├── DECISIONS.md
├── SNAPSHOT.md
├── PROGRESS.md
├── GOAL_EVOLUTION.md
├── CONSTRAINTS.md
└── .flg/
    ├── CONTRACT.md
    ├── state.json
    ├── index.json
    ├── patches/
    ├── sessions/
    └── memory/
```

## Patch-First Write Strategy

FlowGrid uses a patch-first approach to avoid AI accidentally overwriting important project files:

- **Low risk** (progress logs): Can be appended directly
- **Medium risk** (snapshot updates): Generate patch for review
- **High risk** (goal/boundary changes): Must generate patch + human confirmation

All patches are stored in `.flg/patches/` and require human review before merging.

### Two-Layer State (Agent Startup Protocol)

When an agent starts working on a FLG project, it must read **two layers** of state:

**Layer 1 - Formal Ledger (merged facts):**
- `PROJECT.md`, `FRAMING.md`, `SNAPSHOT.md`, `DECISIONS.md`, `PROGRESS.md`

**Layer 2 - Pending Patches (unmerged facts):**
- `.flg/patches/` 中所有 `status: pending_review` 的 patch
- Pending patches are not formal facts, but represent "pending project state"
- Agents must read and understand pending patches before continuing

This ensures multi-agent relay works correctly: Agent B can see Agent A's closeout output even before human review.

## CLI Commands

| Command | Description |
|---------|-------------|
| `flg init <name>` | Initialize a new project |
| `flg frame` | Check framing completeness |
| `flg closeout --transcript <file>` | Generate closeout patch |
| `flg review --patch <file>` | Accept candidate decisions into DECISIONS.md |
| `flg merge --patch <file>` | Merge pending patch into formal ledger |
| `flg handoff` | Generate agent handoff summary |
| `flg audit <path>` | Audit existing project directory |
| `flg extract-decisions <path>` | Extract candidate decisions |
| `flg import <source>` | Import existing project into FLG |
| `flg status` | Show project status |
| `flg version` | Show FLG version |

## Smoke Test

Run a repo-local smoke test after installation:

```bash
python scripts/smoke_test.py
pytest -q
```

The smoke test creates a temporary project, runs `init`, `frame`, `closeout`, `handoff`, and `status`, then prints the generated files.

## v0.1 Core Scope

This version includes:
- `flg init` - Project initialization
- `flg frame` - Framing completeness check
- `flg closeout` - Session closeout with transcript extraction
- `flg merge` - Merge pending patches into formal ledger
- `flg handoff` - Generate agent handoff summary
- `flg audit` - Audit existing project directories
- `flg extract-decisions` - Extract candidate decisions
- `flg import` - Import existing projects
- Basic keyword-based extraction (no LLM)
- Patch generation for all medium/high risk writes
- Project state management
- Two-layer state protocol (formal ledger + pending patches)

## v0.1.5 Legacy (Implemented)

Legacy Audit features:
- `flg audit --report-only` - Audit existing projects
- `flg extract-decisions --dry-run` - Extract candidate decisions
- `flg import --dry-run` - Import existing project files

## History

FlowGrid keeps `FLG` as its technical shorthand, CLI prefix, and `.flg/` project directory. Earlier iterations used the name "Framing Ledger", but the external product name was changed because "FlowGrid" reads more like a tool while preserving the existing FLG technical surface.

## Protocol

FlowGrid is not just a Python CLI. It is a local project protocol:

- the filesystem is the source of truth
- markdown files hold the durable project state
- `.flg/` holds runtime and review state
- agents may propose changes, but medium/high-risk updates stay reviewable

See [docs/protocol.md](./docs/protocol.md) for the protocol-level model.

## AI Host Usage

FlowGrid is designed to work inside Codex, Claude, OpenHands, Hermes, or any AI agent work product that can read files and run commands.

The intended pattern is:

- the user speaks in natural language
- the AI host decides when to call `flg`
- FlowGrid writes durable local project state

See [docs/host-usage.md](./docs/host-usage.md) for host-style usage.

## Inspiration

FLG is inspired by [Oh My Codex (OMX)](https://github.com/Yeachan-Heo/oh-my-codex), an orchestration layer that enhances Codex CLI for developers. OMX pioneered the idea that the project directory itself should be the source of truth — agents read rules, state persists across sessions, and the filesystem is the coordination layer.

FLG takes this same engineering philosophy and applies it to non-coding knowledge work:

| | OMX | FLG |
|---|---|---|
| **Target user** | Developers | Strategy / Marketing / Ops / Solution professionals |
| **Deliverable** | Code, PRs, running apps | Strategies, briefs, proposals, campaigns |
| **Project structure** | Git repo + worktree | Plain-text ledger directory |
| **Agent coordination** | Multi-agent code pipeline | Single-operator agent relay |

The core idea is the same: *make the project directory the single source of truth so any agent can pick up where the last one left off.* The difference is whose work it serves.

## License

MIT
