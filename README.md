# FlowGrid (FLG)

[English](./README.md) | [简体中文](./README.zh-CN.md)

> A local project-state context engine for rationale-heavy, non-coding business projects.
> Designed for AI agents to preserve reviewed judgments, project state, and reasoning chains in local files.

![Stage](https://img.shields.io/badge/stage-v0.4--validation-4c6ef5)
![Runtime](https://img.shields.io/badge/runtime-local--first-2b8a3e)
![Interface](https://img.shields.io/badge/interface-CLI%20%2B%20project%20protocol-495057)
![Tests](https://img.shields.io/badge/tests-125%20passed-2f9e44)

FlowGrid helps business-project knowledge workers turn messy AI work sessions into reviewed, traceable, and resumable project context.

> **Current status:** the codebase reports `v0.3.0` and is in v0.4 core validation. The current focus is entry reliability, rebuildable ledger state, and real-project continuation; v0.4 is not presented as a released version yet.

It is built for long-running work where the deliverable is not just a document, but a defensible judgment chain: why this proposal makes sense, why this direction was chosen, what alternatives were rejected, and when a past judgment should be revised.

## Quick Links

- [Why it exists](#what-is-flowgrid)
- [30-second demo](#30-second-demo)
- [Who it is for](#who-is-it-for)
- [Quick start](#quick-start)
- [CLI commands](#cli-commands)
- [User pain model](./docs/product/user-pain-model.md)
- [Protocol docs](./docs/protocol.md)
- [Host usage](./docs/host-usage.md)
- [Chinese README](./README.zh-CN.md)

## At a Glance

- **Local-first:** project truth lives in files, not chat memory
- **Context-first:** agent startup should load reviewed project state, not raw history dumps
- **Judgment-aware:** decisions store why, rejected options, assumptions, and reversal conditions
- **Patch-first:** medium/high-risk updates stay reviewable before merge
- **Host-agnostic:** works inside Codex, Hermes, OpenClaw, Claude, or any agent shell that can read files and run commands
- **Business-project oriented:** built for proposals, campaigns, briefs, strategies, mechanisms, and retrospectives

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

You can run that flow from Codex, Hermes, OpenClaw, Claude, or any AI agent work product that can read files and run commands.

## What is FlowGrid?

FlowGrid (FLG) is a local project-state context engine for rationale-heavy, non-coding business projects.

It gives AI agents a durable local protocol for preserving project judgments, current state, pending changes, and handoff context across sessions.

The core problem it addresses:

> Long-running AI collaboration produces more history than an agent should reload, but less structure than a business project needs to stay trustworthy.

FlowGrid separates raw discussion, candidate judgments, reviewed decisions, pending patches, and current project state.

## Who is it for?

FlowGrid is for business-project knowledge workers who own fuzzy projects and must repeatedly clarify, judge, revise, explain, and hand off project state.

Typical roles include:

- operations leads designing mechanisms, rhythms, and retrospectives
- marketing leads planning campaigns, briefs, and content directions
- strategy / growth leads making trade-offs and project recommendations
- solution and proposal owners translating client needs into deliverable logic
- creative or research-oriented operators building long-running judgment chains
- independent consultants and small-team owners who do several of these at once

FlowGrid serves a work structure, not a job title.

Best-fit task modes:

- **Proposal persuasion:** why this proposal, campaign, or deck makes sense
- **Mechanism progression:** how the project keeps moving under real constraints
- **Judgment revision:** why a previous judgment should change now

## How is it different from prompt workflows?

| Dimension | Prompt Workflow | FlowGrid |
|-----------|----------------|----------|
| Scope | Single conversation | Full project lifecycle |
| Memory | AI memory (temporary) | Project files (persistent) |
| Truth source | Scattered across conversations | Unified project ledger |
| Judgment chain | Easily buried | Reviewable and traceable |
| Portability | Tied to specific AI | Any local agent can continue |

## Why Decision Logs Matter

Your AI may lose the reasoning behind a decision every conversation. FLG keeps it in the project.

`DECISIONS.md` records *what* you decided, *why* you decided it, *what you rejected*, and *under what conditions you would reverse the call*. This is the difference between a history log and a judgment tool.

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
- **Agent relay continuity** — any agent picking up your project sees the judgment chain, not only the current task
- **Judgment compounding** — your reasoning patterns become explicit, transferable, and improvable

## Who is it NOT for?

There are tools that already serve these users better:

| Profile | Use this instead |
|---|---|
| Software engineer working in a git repo with code-agent team | [oh-my-codex (OMX)](https://github.com/Yeachan-Heo/oh-my-codex) — worktree-isolated multi-agent pipeline, MCP-backed state, `ralph`/`team`/`tdd` skills |
| Enterprise PM running structured sprint backlogs | [Atlassian AI Agents](https://www.atlassian.com/agile/project-management/ai-agents) — coordination, status sync, enterprise integration |
| Team lead running self-driving project workspaces | [Taskade Genesis / Workspace DNA](https://www.taskade.com/blog/autonomous-project-management) — 100+ integrations, prompt → running project |
| Solo non-coder wanting low-friction agent task execution | [Claude Cowork](https://www.scrum.org/resources/blog/claude-cowork-ai-agents-email-moment-non-coding-agile-practitioners) — packaging code-agent power for non-coders |

**FlowGrid's niche:** single-operator, non-coding, rationale-heavy business project work where the deliverable is a proposal, strategy, brief, mechanism, campaign, retrospective, or defensible judgment chain.

If your work is to figure out what should be done and why it should be done, FLG is for you.

## Installation

```bash
pip install -e .
flg version
```

## First Run

After installation, run onboarding to check your environment, try a guided demo of the core loop, and install the FLG skill into your AI host:

```bash
flg onboard
```

This will:
1. **Check your environment** — FLG version, PATH status, detected AI hosts (Codex, Hermes, ZCode, Claude), and whether the FLG skill is installed in each.
2. **Run a guided demo** — a 5-minute walkthrough of `init → closeout → review → merge → context` using a built-in sample transcript. Skip with `--skip-demo`.
3. **Install the skill** — symlinks `skills/flowgrid-operator/` into each detected host's skills directory so your AI agent knows when and how to call `flg`.

Use `flg onboard --yes` for non-interactive mode (CI, scripts).

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

For an English-first project, initialize the formal ledger in English:

```bash
flg init "My Project" --language en
```

The language is stored in `.flg/state.json`; existing projects remain compatible and default to Chinese unless explicitly migrated.

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
It also reports when the framing has no declared evidence basis or relies on
secondary/speculative evidence.

### 3. Close out a session

```bash
flg closeout --transcript path/to/transcript.md
```

This extracts decisions, risks, and progress from a transcript and generates a closeout patch. External raw transcripts are automatically copied into `.flg/sessions/` so the evidence path is durable.

English transcripts are supported, including confirmation, trade-off, risk, question, rationale, rejection, and reversal language. Review low-confidence candidates before accepting them.

Use raw meeting notes, session transcripts, or files under `.flg/sessions/`.
Do not use structured ledger files such as `PROGRESS.md`, `SNAPSHOT.md`, or `DECISIONS.md` as closeout input unless you explicitly know why and pass `--force`.

To archive a raw transcript before closeout:

```bash
flg session save path/to/transcript.md --name 20260715-topic
flg closeout --transcript .flg/sessions/20260715-topic.md
```

To inspect or repair cross-file state:

```bash
flg doctor
flg reindex
```

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
| `flg context --mode resume` | Generate bounded agent startup Context Pack |
| `flg evidence <decision-id>` | Show evidence behind a reviewed decision |
| `flg merge --patch <file>` | Merge pending patch into formal ledger |
| `flg handoff` | Generate agent handoff summary |
| `flg audit <path>` | Audit existing project directory |
| `flg extract-decisions <path>` | Extract candidate decisions |
| `flg import <source>` | Import existing project into FLG |
| `flg status` | Show project status |
| `flg version` | Show FLG version |
| `flg capture add -c <claim> -r <reason>` | Capture a judgment candidate in real-time |
| `flg capture list` | List judgment candidates (filter by type/status) |
| `flg capture review` | Review candidates → accept into DECISIONS.md or reject |
| `flg decision add -d <decision> -r <reason>` | Direct decision write (strong commitment only) |

> `flg trace` is planned future work and is not implemented in the current CLI.

## Smoke Test

Run a repo-local smoke test after installation:

```bash
python scripts/smoke_test.py
pytest -q
```

The smoke test creates a temporary project, runs `init`, `frame`, `closeout`, `review`, `evidence`, `context`, `handoff`, and `status`, then prints the generated files.

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

FlowGrid is not just a Python CLI. It is a local project-state protocol:

- the filesystem is the source of truth
- markdown files hold the durable project state
- `.flg/` holds runtime and review state
- agents may propose changes, but medium/high-risk updates stay reviewable

See [docs/protocol.md](./docs/protocol.md) for the protocol-level model.

## AI Host Usage

FlowGrid is designed to work inside Codex, Hermes, OpenClaw, Claude, or any AI agent work product that can read files and run commands.

The intended pattern is:

- the user speaks in natural language
- the AI host decides when to call `flg`
- FlowGrid writes durable local project state

See [docs/host-usage.md](./docs/host-usage.md) for host-style usage.

## Inspiration

FLG is inspired by [Oh My Codex (OMX)](https://github.com/Yeachan-Heo/oh-my-codex), an orchestration layer that enhances Codex CLI for developers. OMX pioneered the idea that the project directory itself should be the source of truth — agents read rules, state persists across sessions, and the filesystem is the coordination layer.

FLG takes this same engineering philosophy and applies it to rationale-heavy, non-coding business project work:

| | OMX | FLG |
|---|---|---|
| **Target user** | Developers | Business-project knowledge workers |
| **Deliverable** | Code, PRs, running apps | Proposals, briefs, campaigns, mechanisms, judgments |
| **Project structure** | Git repo + worktree | Plain-text project ledger directory |
| **Agent coordination** | Multi-agent code pipeline | Single-operator agent relay |

The core idea is the same: *make the project directory the single source of truth so any agent can pick up where the last one left off.* The difference is whose work it serves.

## License

MIT
