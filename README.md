# FlowGrid (FLG)

[English](./README.md) | [简体中文](./README.zh-CN.md)

> A local project-state context engine for rationale-heavy, non-coding business projects.
> Designed for AI agents to preserve state-aware judgments, project state, and reasoning chains in local files.

![Stage](https://img.shields.io/badge/stage-v0.4--validation-4c6ef5)
![Runtime](https://img.shields.io/badge/runtime-local--first-2b8a3e)
![Interface](https://img.shields.io/badge/interface-CLI%20%2B%20protocol-495057)
[![CI](https://github.com/dlxeva/FlowGrid/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/dlxeva/FlowGrid/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-%3E%3D3.10-3776AB?logo=python&logoColor=white)
[![License](https://img.shields.io/github/license/dlxeva/FlowGrid)](./LICENSE)

FlowGrid helps business-project knowledge workers turn messy AI work sessions into state-aware, traceable, and resumable project context.

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
- [Independent runtime experiments](#independent-runtime-experiments)
- [Chinese README](./README.zh-CN.md)

## At a Glance

- **Local-first:** project truth lives in files, not chat memory
- **Context-first:** agent startup should load bounded project state, not raw history dumps
- **Judgment-aware:** decisions store why, rejected options, assumptions, and reversal conditions
- **Background-safe writes:** the host processes routine patches without making the user operate a ledger workflow
- **Host-agnostic:** works inside Codex, Hermes, OpenClaw, Claude, or any agent shell that can read files and run commands
- **Business-project oriented:** built for proposals, campaigns, briefs, strategies, mechanisms, and retrospectives

## 30-Second Demo

```bash
mkdir demo && cd demo
flg init "Launch Proposal" --type proposal --client "Client A"
flg frame
flg closeout --transcript meeting-notes.md
flg review --patch .flg/patches/<closeout-patch>.md --report-only
flg review --patch .flg/patches/<closeout-patch>.md --autonomous
flg merge --patch .flg/patches/<closeout-patch>.md --yes
flg context --mode resume
flg handoff
```

After that, you will have:

- a local project ledger: `PROJECT.md`, `FRAMING.md`, `DECISIONS.md`, `SNAPSHOT.md`, `PROGRESS.md`
- a protocol directory: `.flg/`
- reviewable pending changes in `.flg/patches/`
- a resumable handoff summary for the next session or agent

In host-integrated use, the review and merge lines run in the background. The
user continues the project in natural language. Background automation only
adopts candidates that preserve explicit user or client attribution; agent-authored,
unattributed, shell, and ambiguous candidates remain pending. A host closes its
patch after preserving the audit trail, while a material unresolved ambiguity
remains pending.

You can run that flow from Codex, Hermes, OpenClaw, Claude, or any AI agent work product that can read files and run commands.

## Independent Runtime Experiments

FlowGrid's local-first CLI and protocol are the main product. Two hackathon
repositories validate the same judgment-state semantics in bounded external
runtimes:

- [FlowGrid Memory Runtime](https://github.com/dlxeva/flowgrid-memory-runtime)
  uses synthetic data to demonstrate confirmed, pending, and superseded
  judgment state on CockroachDB and AWS.
- [FlowGrid MemoryAgent for Qwen Cloud](https://github.com/dlxeva/flowgrid-qwen-memory-agent)
  demonstrates Qwen-driven candidate extraction, human authorization, and
  constrained confirmed-state retrieval on Alibaba Cloud.

They show that the lifecycle can run across models and deployment stacks. They
do not make AWS, CockroachDB, Qwen, or Alibaba Cloud dependencies of FlowGrid
Core, and they do not establish user adoption, retention, or product-market
fit. Core validation remains focused on natural-language host operation,
rebuildable local ledger state, and real-project continuation.

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

English transcripts are supported, including confirmation, trade-off, risk, question, rationale, rejection, and reversal language. Low-confidence candidates remain pending for background handling.

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
- **High risk** (goal/boundary changes): Must retain provenance and an explicit action boundary

All patches are stored in `.flg/patches/` and processed by the host in the
background. `--report-only` is available for diagnostics; `--autonomous` adopts
only clear candidates with explicit user or client attribution, at medium
authority. Agent-authored, unattributed, shell, and ambiguous candidates stay
out of the formal ledger. Candidate risks and next actions remain in the patch
until they have their own confirmation path. The host then merges routine
updates or discards a non-adoptable patch, keeping its raw source and closed
patch for audit.

### Two-Layer State (Agent Startup Protocol)

When an agent starts working on a FLG project, it must read **two layers** of state:

**Layer 1 - Formal Ledger (merged facts):**
- `PROJECT.md`, `FRAMING.md`, `SNAPSHOT.md`, `DECISIONS.md`, `PROGRESS.md`

**Layer 2 - Pending Patches (unmerged facts):**
- `.flg/patches/` 中所有 `status: pending_review` 的 patch
- Pending patches are not formal facts, but represent "pending project state"
- Agents must read and understand pending patches before continuing

This ensures multi-agent relay works correctly: Agent B can see Agent A's closeout output while the host preserves pending and ambiguous state internally.

## CLI Commands

| Command | Description |
|---------|-------------|
| `flg init <name>` | Initialize a new project |
| `flg frame` | Check framing completeness |
| `flg closeout --transcript <file>` | Generate closeout patch |
| `flg onboard [--yes]` | Check the environment, run the guided demo, and install the host skill |
| `flg session save <file>` | Archive a raw session before closeout |
| `flg review --patch <file> [--report-only] [--autonomous]` | Inspect candidates internally, then process eligible decisions in the background |
| `flg context --mode resume` | Generate bounded agent startup Context Pack |
| `flg evidence <decision-id>` | Show evidence behind a reviewed decision |
| `flg merge --patch <file> [--yes]` | Merge routine patch updates without a prompt |
| `flg handoff` | Generate agent handoff summary |
| `flg audit <path>` | Audit existing project directory |
| `flg extract-decisions <path>` | Extract candidate decisions |
| `flg import <source>` | Import existing project into FLG |
| `flg status` | Show project status |
| `flg version` | Show FLG version |
| `flg doctor` | Check cross-file ledger and index consistency |
| `flg reindex` | Rebuild runtime indexes from the formal ledger |
| `flg capture add -c <claim> -r <reason>` | Capture a judgment candidate in real-time |
| `flg capture list` | List judgment candidates (filter by type/status) |
| `flg capture review` | Process candidates in the background → accept or keep pending |
| `flg decision add -d <decision> -r <reason>` | Direct decision write (strong commitment only) |

> `flg trace` is planned future work and is not implemented in the current CLI.

## Current v0.4 Validation Focus

- stable ingestion of raw sessions into `.flg/sessions/`
- reliable background processing before candidate judgments enter the formal ledger
- rebuilding runtime indexes from formal project files with `doctor` and `reindex`
- continuation by a later agent using real, long, and contradictory project history

Automatic quadrant routing, a blindspot engine, and `flg trace` are not completed
capabilities in the current version.

## Smoke Test

Run a repo-local smoke test after installation:

```bash
python scripts/smoke_test.py
pytest -q
```

The smoke test creates a temporary project, runs `init`, `frame`, `closeout`, `review`, `evidence`, `context`, `handoff`, and `status`, then prints the generated files.

## Historical v0.1 Core Scope

The original v0.1 scope included:
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

## Historical v0.1.5 Legacy (Implemented)

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

## Open Core Boundary

FlowGrid Core is a local-first, auditable, host-agnostic open-source core.

- **User project data always belongs to the user.** FlowGrid has no mandatory
  hosted backend. Project state is stored in local files. If you enable a remote
  LLM provider, selected transcript content may be sent to that provider under
  its terms. Remote extraction requires the explicit
  `--allow-remote-llm` flag. Use the default local extraction or a local
  provider for fully local processing.
- **The public repository does not contain real user training data.** All tests
  and examples use synthetic data.
- **Advanced hosted features, team collaboration, industry templates, and
  research data** may be offered in other versions, but the core protocol and
  CLI remain open and independently usable.
- **The protocol is designed for portability.** Your project state is plain-text
  markdown — you can read it, edit it, and migrate it without lock-in.

See [docs/governance/OPEN_SOURCE_BOUNDARY.md](./docs/governance/OPEN_SOURCE_BOUNDARY.md)
for the full boundary definition.

## Governance

- [LICENSE](./LICENSE) — MIT
- [CONTRIBUTING.md](./CONTRIBUTING.md) — contribution guidelines
- [SECURITY.md](./SECURITY.md) — security reporting policy
- [TRADEMARK.md](./TRADEMARK.md) — name and branding usage
- [Open-Source Audit](./docs/governance/OPEN_SOURCE_AUDIT.md) — file classification report
- [Open-Source Boundary](./docs/governance/OPEN_SOURCE_BOUNDARY.md) — public/private boundary definition
- [Future Direction](./docs/product/future-direction.md) — product roadmap insights

## License

MIT
