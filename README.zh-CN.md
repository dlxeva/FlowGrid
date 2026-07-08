# FlowGrid（FLG）

[English](./README.md) | [简体中文](./README.zh-CN.md)

> 面向推导密集型非代码业务项目的本地项目状态上下文引擎。
> 设计目标是让 AI Agent 把经过审核的判断、项目状态和推导链稳定保存在本地文件中。

![阶段](https://img.shields.io/badge/stage-v0.2.1--alpha-4c6ef5)
![运行方式](https://img.shields.io/badge/runtime-local--first-2b8a3e)
![接口](https://img.shields.io/badge/interface-CLI%20%2B%20project%20protocol-495057)
![测试](https://img.shields.io/badge/tests-58%20passed-2f9e44)

FlowGrid 帮助业务项目型知识工作者，把混乱的 AI 协作过程转成经过审核、可追溯、可恢复的项目上下文。

它适合长期推进的模糊项目。此类项目的交付物通常不只是一份文档，还包括一条能被解释和质询的判断链：为什么这个方案成立，为什么选择这个方向，哪些备选被放弃，什么情况下旧判断需要修正。

## 快速入口

- [它到底是什么](#什么是-flowgrid)
- [30 秒 demo](#30-秒-demo)
- [适合谁用](#适合谁用)
- [快速开始](#快速开始)
- [CLI 命令](#cli-命令)
- [用户痛点模型](./docs/product/user-pain-model.md)
- [协议文档](./docs/protocol.md)
- [宿主使用说明](./docs/host-usage.md)
- [English README](./README.md)

## 一眼看懂

- **本地优先：** 项目真相在文件里，不在聊天记忆里
- **上下文优先：** Agent 启动时读取经过审核的项目状态，避免直接吞整段历史
- **判断链优先：** 决策记录为什么选、放弃了什么、依赖哪些前提、什么条件会反转
- **patch-first：** 中高风险更新先生成 patch，再审核合并
- **宿主无关：** 可嵌入 Codex、Claude、OpenClaw、Hermes 或任何能读文件/跑命令的 AI agent work 产品
- **业务项目导向：** 面向提案、campaign、brief、策略、机制设计和复盘

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

FlowGrid（技术简称 FLG）是面向推导密集型非代码业务项目的本地项目状态上下文引擎。

它为 AI Agent 提供一套本地协议，用来保存项目判断、当前状态、待审核变更和跨会话 handoff 上下文。

它处理的核心问题：

> 长期 AI 协作会产生大量历史记录，但 Agent 每次重启时不应该直接读取整段历史；业务项目又需要足够结构化的判断链，才能保持可信。

FlowGrid 会区分原始讨论、候选判断、已审核决策、待审核 patch 和当前项目状态。

## 适合谁用

FlowGrid 适合业务项目型知识工作者。这里的核心不是岗位名称，而是工作结构：你负责一个模糊项目，需要反复澄清、判断、修正、解释和交接项目状态。

典型角色包括：

- 运营负责人：设计机制、节奏、约束和复盘
- 营销负责人：管理 campaign、brief、内容方向和传播判断
- 策略 / 增长负责人：做取舍、定方向、形成项目建议
- 方案负责人：把客户需求翻译成可交付逻辑
- 创意或研究型业务人员：维护长期选题、观点和方向判断
- 独立顾问或小团队 owner：同时承担上面多种职责

FlowGrid 服务的是一种工作结构，不是一个岗位标签。

最适合的任务模式：

- **方案说服：** 为什么这个方案、campaign 或 deck 成立
- **机制推进：** 项目如何在真实约束下继续推进
- **判断修正：** 为什么旧判断现在需要调整

## 它和普通提示词工作流有什么区别

| 维度 | 普通提示词工作流 | FlowGrid |
|------|------------------|----------|
| 范围 | 一次对话 | 整个项目生命周期 |
| 记忆 | AI 临时记忆 | 项目文件长期保存 |
| 事实源 | 散落在聊天里 | 统一项目账本 |
| 判断链 | 容易被埋掉 | 可审核、可追溯 |
| 可迁移性 | 绑定具体 AI | 任何本地 Agent 都可继续 |

## 为什么决策日志重要

AI 每次换会话，都可能丢掉你之前为什么这样判断。FLG 会把这件事放进项目文件。

`DECISIONS.md` 记录“决定了什么”，也记录：

- 当时的背景
- 为什么这样选
- 放弃了什么方案
- 什么条件会让这个判断反转

这让项目判断成为可追溯、可复盘、可交接的资产。

## 不适合谁

如果你更像下面这些场景，别勉强用它：

| 场景 | 更适合的工具 |
|------|--------------|
| 在 git 仓库里做多 Agent 代码协作 | [oh-my-codex (OMX)](https://github.com/Yeachan-Heo/oh-my-codex) |
| 企业 PM 管理冲刺、需求池、团队状态 | [Atlassian AI Agents](https://www.atlassian.com/agile/project-management/ai-agents) |
| 团队级自治工作空间、自动化协同 | [Taskade Genesis / Workspace DNA](https://www.taskade.com/blog/autonomous-project-management) |
| 只想低门槛找个 Agent 帮你跑任务 | [Claude Cowork](https://www.scrum.org/resources/blog/claude-cowork-ai-agents-email-moment-non-coding-agile-practitioners) |

**FlowGrid 的定位：** 单兵、非编码、推导密集型业务项目。交付物更偏提案、brief、campaign、机制、策略、复盘和可辩护判断链。

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
| `flg context --mode resume` | 生成 Agent 启动上下文包 |
| `flg evidence <decision-id>` | 查看决策背后的证据来源 |
| `flg merge --patch <file>` | 将 patch 合并到正式账本 |
| `flg handoff` | 生成 Agent 接力摘要 |
| `flg audit <path>` | 审计已有项目目录 |
| `flg extract-decisions <path>` | 提取候选决策 |
| `flg import <source>` | 导入已有项目 |
| `flg status` | 查看项目状态 |
| `flg version` | 查看 FLG 版本 |

> `flg trace` 已规划，当前版本尚未实现。

## Smoke Test

安装后可以跑仓库内 smoke test：

```bash
python scripts/smoke_test.py
pytest -q
```

smoke test 会在临时目录里创建 demo 项目，依次运行 `init`、`frame`、`closeout`、`review`、`evidence`、`context`、`handoff`、`status`，最后打印生成的文件。

## 历史与命名

FlowGrid 保留 `FLG` 作为技术简称、CLI 前缀和 `.flg/` 项目目录。更早的迭代里，这个项目曾使用 `Framing Ledger` 作为全称；现在对外切到 `FlowGrid`，是为了让第一次看到的人更容易把它理解成一个工具，同时保留既有 FLG 技术表面。

## 协议层

FlowGrid 是一套本地项目协议：

- 文件系统是事实源
- Markdown 文件承载持久项目状态
- `.flg/` 目录承载运行态与审查态
- Agent 可以提出修改，但中高风险更新必须可审查

详细说明见 [docs/protocol.md](./docs/protocol.md)。

## AI 宿主使用方式

FlowGrid 的更自然用法是：

- 用户继续在 Codex / Claude / OpenClaw / Hermes 等 AI agent work 产品里自然说话
- AI 在合适的时候调用 `flg`
- FlowGrid 负责把项目状态稳定落盘

详细说明见 [docs/host-usage.md](./docs/host-usage.md)。

## 灵感来源

FLG 的灵感来自 [Oh My Codex (OMX)](https://github.com/Yeachan-Heo/oh-my-codex)。OMX 把“项目目录本身就是事实源”这件事做得很彻底：规则在文件里、状态能持久化、文件系统就是协作层。

FlowGrid 把这套思路迁移到推导密集型非代码业务项目：

| | OMX | FLG |
|---|---|---|
| **目标用户** | 开发者 | 业务项目型知识工作者 |
| **主要交付物** | 代码、PR、运行中的应用 | 提案、brief、campaign、机制、判断链 |
| **项目结构** | Git repo + worktree | 明文本地项目账本目录 |
| **Agent 协作方式** | 多 Agent 代码流水线 | 单兵 + Agent 接力 |

核心思想没变：**让项目目录成为事实源，让后来的 Agent 能从同一个地方继续工作。**

## License

MIT
