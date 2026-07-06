# FlowGrid（FLG）

[English](./README.md) | [简体中文](./README.zh-CN.md)

> 面向非编码知识工作的 AI-native 本地项目协议层。
> 设计目标是嵌入任何 AI agent work 产品中：自然语言是界面，本地文件是事实源。

![阶段](https://img.shields.io/badge/stage-v0.2.1--alpha-4c6ef5)
![运行方式](https://img.shields.io/badge/runtime-local--first-2b8a3e)
![接口](https://img.shields.io/badge/interface-CLI%20%2B%20project%20protocol-495057)
![测试](https://img.shields.io/badge/tests-58%20passed-2f9e44)

FlowGrid 用来把策略、营销、调研、运营、解决方案这类“问题还没完全定义清楚”的工作，收成一个可推进、可复核、可交接的项目系统。

它把项目记忆放在明文文件里，让不同 AI agent work 产品都能围绕同一个目录继续工作，并把决策、进展、待审核 patch 都当作正式项目状态的一部分。

## 快速入口

- [它到底是什么](#什么是-flowgrid)
- [30 秒 demo](#30-秒-demo)
- [适合谁用](#适合谁用)
- [快速开始](#快速开始)
- [CLI 命令](#cli-命令)
- [协议文档](./docs/protocol.md)
- [宿主使用说明](./docs/host-usage.md)
- [English README](./README.md)

## 一眼看懂

- **本地优先：** 项目真相在文件里，不在聊天记忆里
- **宿主无关：** 可嵌入 Codex、Claude、OpenClaw、Hermes 或任何能读文件/跑命令的 AI agent work 产品
- **可续接优先：** 后来的 Agent 和后续会话读取同一套账本和 pending patches
- **决策有上下文：** 不只记“做了什么”，也记“为什么这么做”
- **patch-first：** 中高风险更新先生成 patch，再审核合并
- **面向非编码工作：** 更适合 brief、提案、判断、规划，而不是代码协作

## 30 秒 demo

```bash
mkdir demo && cd demo
flg init "Launch Proposal" --type proposal --client "Client A"
flg frame
flg closeout --transcript meeting-notes.md
flg handoff
```

跑完以后，你会得到：

- 一套本地项目账本：`PROJECT.md`、`FRAMING.md`、`DECISIONS.md`、`SNAPSHOT.md`、`PROGRESS.md`
- 一个协议目录：`.flg/`
- 一批可审查的待合并变更：`.flg/patches/`
- 一份可续接的 handoff 摘要，给下次会话或下一个 Agent 用

这条流程可以运行在 Codex、Claude、OpenClaw、Hermes 或其他 AI agent work 产品里，不要求用户改用新的工作台。

## 什么是 FlowGrid

FlowGrid（技术简称 FLG）是一套面向非代码知识工作的 AI-native 本地项目协议，面向策略、营销、运营、调研、解决方案等场景。

它的目标不是替代你的写作或思考，而是把模糊项目收成一套有边界、有状态、有决策链、可被后续 Agent 接手的项目结构。

## 适合谁用

- **策略人员：** 需要定义目标、边界、评审逻辑和推进路径
- **营销人员：** 需要管理 campaign 判断、brief、方案和交接
- **运营人员：** 需要把机制设计、节奏、约束和复盘沉淀下来
- **解决方案人员：** 需要把客户需求翻译成可交付路径和项目判断

## 它和普通提示词工作流有什么区别

| 维度 | 普通提示词工作流 | FlowGrid |
|------|------------------|----------|
| 范围 | 一次对话 | 整个项目生命周期 |
| 记忆 | AI 临时记忆 | 项目文件长期保存 |
| 事实源 | 散落在聊天里 | 统一项目账本 |
| 可审计性 | 几乎不可审计 | 明文、可追踪 |
| 可迁移性 | 绑定具体 AI | 任何本地 Agent 都可继续 |

## 为什么决策日志重要

AI 每次对话都可能忘记你之前为什么这么判断，FLG 不会。

`DECISIONS.md` 记录的不只是“决定了什么”，还包括：

- 当时的背景
- 为什么这样选
- 放弃了什么方案
- 什么条件会让这个判断反转

这让项目判断不是一次性输出，而是可追溯、可复盘、可交接的资产。

## 不适合谁

如果你更像下面这些场景，别勉强用它：

| 场景 | 更适合的工具 |
|------|--------------|
| 在 git 仓库里做多 Agent 代码协作 | [oh-my-codex (OMX)](https://github.com/Yeachan-Heo/oh-my-codex) |
| 企业 PM 管理冲刺、需求池、团队状态 | [Atlassian AI Agents](https://www.atlassian.com/agile/project-management/ai-agents) |
| 团队级自治工作空间、自动化协同 | [Taskade Genesis / Workspace DNA](https://www.taskade.com/blog/autonomous-project-management) |
| 只想低门槛找个 Agent 帮你跑任务 | [Claude Cowork](https://www.scrum.org/resources/blog/claude-cowork-ai-agents-email-moment-non-coding-agile-practitioners) |

**FlowGrid 的定位：** 单兵、非编码、判断型知识工作。交付物更偏决策、brief、提案、方案和推进结构，而不是代码、Sprint 或 SaaS 工作台。

## 安装

```bash
pip install -e .
flg version
```

## 开发模式

通过 editable install 的控制台脚本运行：

```bash
pip install -e .
flg version
```

不安装，直接从源码树运行：

```bash
PYTHONPATH=src python -m flg.cli version
```

Windows PowerShell：

```powershell
$env:PYTHONPATH="src"
python -m flg.cli version
```

## 快速开始

### 1. 初始化一个项目

```bash
mkdir my-project && cd my-project
flg init "My Project" --type proposal --client "Client Name"
```

会创建这些核心文件：

- `PROJECT.md`：项目概览
- `FRAMING.md`：问题定义
- `DECISIONS.md`：决策日志
- `SNAPSHOT.md`：当前快照
- `PROGRESS.md`：进展记录
- `.flg/`：FLG 内部协议目录

### 2. 检查 framing 完整度

```bash
flg frame
```

它会检查 `FRAMING.md` 缺哪些关键字段，并生成 patch 建议。

### 3. 会话结束时 closeout

```bash
flg closeout --transcript path/to/transcript.md
```

它会从对话或记录里提取决策、风险、进展，并生成 closeout patch。

推荐输入原始会议纪要、原始对话记录，或 `.flg/sessions/` 下的 session 文件。
不要直接拿 `PROGRESS.md`、`SNAPSHOT.md`、`DECISIONS.md` 这类结构化账本文件做 closeout，除非你明确知道自己在做什么，并显式加 `--force`。

## 项目结构

```text
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

## patch-first 写入策略

FlowGrid 默认不让 AI 直接覆盖重要项目文件。

- **低风险：** 进展日志可直接追加
- **中风险：** 快照更新先生成 patch
- **高风险：** 目标/边界/关键判断变更必须 patch + 人工确认

所有 patch 都放在 `.flg/patches/` 里，审核后再合并。

### Two-Layer State（Agent 启动协议）

Agent 开始工作时，必须读取两层状态：

**Layer 1 - Formal Ledger（已合并事实）**

- `PROJECT.md`
- `FRAMING.md`
- `SNAPSHOT.md`
- `DECISIONS.md`
- `PROGRESS.md`

**Layer 2 - Pending Patches（待审核事实）**

- `.flg/patches/` 中所有 `status: pending_review` 的 patch

这样 Agent B 即使接手时 patch 还没 merge，也不会丢掉 Agent A 的 closeout 结果。

## CLI 命令

| 命令 | 说明 |
|------|------|
| `flg init <name>` | 初始化项目 |
| `flg frame` | 检查 framing 完整度 |
| `flg closeout --transcript <file>` | 生成 closeout patch |
| `flg review --patch <file>` | 审核候选决策并写入 DECISIONS.md |
| `flg merge --patch <file>` | 将 patch 合并到正式账本 |
| `flg handoff` | 生成 Agent 接力摘要 |
| `flg audit <path>` | 审计已有项目目录 |
| `flg extract-decisions <path>` | 提取候选决策 |
| `flg import <source>` | 导入已有项目 |
| `flg status` | 查看项目状态 |
| `flg version` | 查看 FLG 版本 |

## Smoke Test

安装后可以跑仓库内 smoke test：

```bash
python scripts/smoke_test.py
pytest -q
```

smoke test 会在临时目录里创建 demo 项目，依次运行 `init`、`frame`、`closeout`、`handoff`、`status`，最后打印生成的文件。

## 历史与命名

FlowGrid 保留 `FLG` 作为技术简称、CLI 前缀和 `.flg/` 项目目录。更早的迭代里，这个项目曾使用 `Framing Ledger` 作为全称；现在对外切到 `FlowGrid`，是为了让第一次看到的人更容易把它理解成一个工具，而不是一个过于内部的方法论术语。

## 协议层

FlowGrid 不只是一个 Python CLI，它更是一套本地项目协议：

- 文件系统是事实源
- Markdown 文件承载持久项目状态
- `.flg/` 目录承载运行态与审查态
- Agent 可以提出修改，但中高风险更新必须可审查

详细说明见 [docs/protocol.md](./docs/protocol.md)。

## AI 宿主使用方式

FlowGrid 的更自然用法，不是让用户整天手敲 CLI，而是：

- 用户继续在 Codex / Claude / OpenClaw / Hermes 等 AI agent work 产品里自然说话
- AI 在合适的时候调用 `flg`
- FlowGrid 负责把项目状态稳定落盘

详细说明见 [docs/host-usage.md](./docs/host-usage.md)。

## 灵感来源

FLG 的灵感来自 [Oh My Codex (OMX)](https://github.com/Yeachan-Heo/oh-my-codex)。OMX 把“项目目录本身就是事实源”这件事做得很彻底：规则在文件里、状态能持久化、文件系统就是协作层。

FlowGrid 把这套思路迁移到非编码知识工作：

| | OMX | FLG |
|---|---|---|
| **目标用户** | 开发者 | 策略 / 营销 / 运营 / 解决方案人员 |
| **主要交付物** | 代码、PR、运行中的应用 | 提案、brief、方案、判断与推进结构 |
| **项目结构** | Git repo + worktree | 明文项目账本目录 |
| **Agent 协作方式** | 多 Agent 代码流水线 | 单兵 + Agent 接力 |

核心思想没变：**让项目目录成为事实源，让后来的 Agent 能从同一个地方继续工作。**

## License

MIT