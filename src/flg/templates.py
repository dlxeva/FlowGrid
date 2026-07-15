"""Templates for FlowGrid project files."""

from datetime import datetime

from . import __version__


def get_iso_now() -> str:
    """Return current time in ISO format."""
    return datetime.now().isoformat(timespec="seconds")


PROJECT_MD = """# {project_name}

## Basic Info

- **Project Type:** {project_type}
- **Client/Sponsor:** {client}
- **Current Stage:** {current_stage}
- **Core Deliverables:** {deliverables}
- **Timeline:** {timeline}
- **Key Constraints:** {constraints}

## Background

{background}

---

*Created: {created_at}*
*Last Updated: {updated_at}*
"""

FRAMING_MD = """# Problem Definition

## Problem Statement

{problem_statement}

## Evidence Basis

- **Overall basis:** (direct / verified / secondary / speculative)
- **Direct evidence:** (what was observed or explicitly confirmed)
- **Verification needed before commitment:** (what still needs first-hand validation)

## Requirements

### Explicit Requirements

{explicit_requirements}

### Real Needs Hypothesis

{real_needs}

## Goals

{goals}

## Non-Goals

{non_goals}

## User Objects

{user_objects}

## Review Objects

{review_objects}

## Success Criteria

{success_criteria}

## Constraints

{constraints}

## Open Questions

{open_questions}

---

*Created: {created_at}*
*Last Updated: {updated_at}*
"""

DECISIONS_MD = """# Decision Log

> 每条决策记录"为什么这么做"，不只是"做了什么"。
> 记录背景、备选方案、放弃理由和复盘入口，让未来的你或Agent能理解判断链条。

<!-- 复制以下模板，每条决策一个 -->

## D-001 | 标题

### 决策时间
(日期)

### 所属阶段
(立项/创意策划/执行/复盘)

### 决策背景
(为什么需要做这个判断？当时发生了什么？)

### 核心问题
(到底在问什么？)

### 备选方案
A. (方案A)
B. (方案B)
C. (方案C)

### 最终决策
(选了什么)

### 决策理由
(为什么选这个？依据是什么？)

### 放弃理由
(为什么不选其他方案？)

### 风险判断
(这个选择有什么风险？)

### 后续验证
(怎么验证这个判断对不对？)

### 复盘入口
(什么情况下需要重新审视这个决策？)

---

*Created: {created_at}*
*Last Updated: {updated_at}*
"""

SNAPSHOT_MD = """# Project Snapshot

**Updated:** {updated_at}

## Current Stage

{current_stage}

## Current Core Goal

{current_goal}

## Current Core Judgments

{judgments}

## Confirmed

{confirmed}

## Unconfirmed

{unconfirmed}

## Current Risks

{risks}

## Next Highest Priority Action

{next_action}

---

*Last Updated: {updated_at}*
"""

GOAL_EVOLUTION_MD = """# Goal Evolution

> 记录目标如何变化，而不只是记录最终拍板的决策。
> 每次目标变化都写清楚：从什么变成什么，为什么变，影响到哪些文档或动作。

<!-- 复制以下模板，每次目标变化一条 -->

## Goal Shift 001

- **When:** (日期)
- **Previous Goal:** (之前的目标)
- **New Goal:** (现在的目标)
- **Trigger:** (触发变化的事件 / 信息 / 约束)
- **Impact:** (影响了哪些文档 / 动作 / 边界)

---

*Created: {created_at}*
*Last Updated: {updated_at}*
"""

CONSTRAINTS_MD = """# Constraints and Rules

> 这里记录项目中的规则、约束、例外条件和复核触发器。
> 适合运营机制、解决方案边界、交付条件、审批条件等内容。

## Constraint Blocks

<!-- 复制以下模板，每条约束一个 -->

### Constraint 001

- **If:** (触发条件)
- **Then:** (应采取的动作 / 判断)
- **Unless:** (例外条件；没有就写 none)
- **Owner:** (负责确认的人或角色)
- **Review Trigger:** (什么情况下必须重新检查这条约束)

---

*Created: {created_at}*
*Last Updated: {updated_at}*
"""

PROGRESS_MD = """# Progress Log

## Document Evolution

> 记录重要文档的演化关系：谁写的、什么时候来的、用途是什么、替代了哪份。
> 文档版本关系不再散落在聊天和记忆里。

<!-- 复制以下模板，每条文档演化记录一个 -->

### [文档名称]

- **File:** (文件路径)
- **Role:** (文档职责，自由填写)
- **Provenance:** internal | external | mixed
- **Created:** (创建日期)
- **Supersedes:** (被替代的文件路径，无则写"无")
- **Why:** (为什么生成这份文档？解决了什么问题？)
- **Status:** active | superseded | archived

---

*Created: {created_at}*
*Last Updated: {updated_at}*
"""

CONTRACT_MD = f"""# FlowGrid Contract

## Core Rules

1. **Project directory is the highest priority source of truth.**
   AI memory is only temporary cache. When conflicts arise, project files win.

2. **AI memory is temporary cache only.**
   Do not rely on AI memory for project facts. Always verify against project files.

3. **Agent startup reading protocol (TWO-LAYER STATE):**

   **Layer 1 - Formal Ledger (已合并事实):**
   - `.flg/CONTRACT.md`
   - `PROJECT.md`
   - `FRAMING.md`
   - `SNAPSHOT.md`
   - `DECISIONS.md`
   - `PROGRESS.md`

   **Layer 2 - Pending Patches (待审核事实):**
   - `.flg/patches/` 中所有 `status: pending_review` 的 patch
   - Pending patches 不是正式事实，但属于"待确认项目状态"
   - Agent 必须读取并理解 pending patches 的内容

4. **Agent must distinguish four types of facts:**
   - **已合并事实 (Merged facts):** 正式账本中的内容
   - **待审核事实 (Pending facts):** pending patches 中的内容
   - **冲突事实 (Conflicting facts):** pending patches 与正式账本冲突的内容
   - **需要人工确认的事实 (Human-confirmable facts):** 高风险变更

5. **If pending patches are relevant to current task, Agent must report:**
   - Which pending patches were read
   - What candidate progress/decisions/snapshot updates exist
   - What content is not yet merged
   - Whether to recommend merge first or continue in pending-aware mode

6. **Before execution, check:**
   - Goals
   - Boundaries
   - User objects
   - Success criteria
   - Constraints

7. **Session end requires closeout.**
   Execute `flg closeout` or generate closeout recommendations.

8. **Low risk writes can be appended directly.**
   Progress logs, discussion notes, and non-critical updates.

9. **Medium/high risk writes must enter patch.**
   - Target changes
   - Boundary changes
   - Strategy judgments
   - Decision updates
   - Snapshot updates

10. **Never directly overwrite core files for medium/high risk changes.**
    All such changes go to `.flg/patches/` for human review.

11. **When agent memory conflicts with project files:**
    - Project files win
    - Generate conflict patch
    - Explain source and reasoning
    - Wait for human confirmation

12. **Multi-agent relay protocol:**
    - Later agents must read BOTH formal ledger AND pending patches
    - Then continue from current state (including pending state)
    - Closeout before leaving

13. **Project materials live in `docs/`.**
    - `docs/` is the user's free zone for research, meeting notes, background
      docs, client intelligence, and other process materials.
    - FLG does NOT scan or audit `docs/` — it is outside the formal ledger.
    - `docs/README.md` is the index: list what's inside so a new agent knows
      what materials exist without crawling the directory.
    - Materials in `docs/` are reference, not truth. When a material contradicts
      the formal ledger, the ledger wins (Core Rule 1).

## Agent Startup Context Protocol

When an agent enters a FLG project, it MUST read these three sources in order.
Total payload: ~3-4KB. Every source is a plaintext file — the user can inspect,
modify, and verify what the agent sees. No black-box memory.

### 1. SNAPSHOT.md (~2KB) — Current State

The project snapshot gives the agent immediate situational awareness:
current stage, core goal, confirmed/unconfirmed judgments, risks, and the next
highest-priority action. Always read first.

### 2. Most Recent 1-2 Decisions from DECISIONS.md (~1KB) — Decision Boundary

The agent must know what has already been decided (and why) before making new
recommendations. Reading the most recent decisions prevents re-suggesting
rejected alternatives and keeps the agent within the project's current judgment
boundary.

### 3. `next_actions` from `.flg/state.json` (~0.5KB) — Immediate Task

The agent must know what the project considers the next concrete actions. This
is the bridge between "understanding the project" and "doing something useful."

### Why This Protocol

Without this protocol, agents re-discover the project from scratch every session.
They read arbitrary files, skip important ones, and the user has no visibility
into what was loaded. This protocol makes agent startup:
- **Predictable** — same 3 sources every time
- **Auditable** — user can read the same files the agent reads
- **Efficient** — 3-4KB instead of 40KB+ of history dump
- **Host-agnostic** — works for Hermes, Codex, Claude Code, or any agent

Run `flg context` to see exactly what an agent would get on startup.

## Write Risk Levels

| Risk Level | Files | Strategy |
|------------|-------|----------|
| Low | PROGRESS.md | Direct append |
| Medium | SNAPSHOT.md, FRAMING.md (supplement) | Generate patch |
| High | FRAMING.md (modify goals/boundaries), DECISIONS.md (override), PROJECT.md | Must patch + human confirm |

## State Schema (`.flg/state.json`)

FlowGrid maintains a project state file at `.flg/state.json`. The schema is split into two layers:

### Core Fields (CLI depends on these)

These 13 fields are required for CLI operations. When reading a state file, the CLI normalizes variant field names (see map below) and auto-fills safe defaults for missing fields.

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Schema version for migration ("1") |
| `project_id` | string | Unique project identifier |
| `project_name` | string | Human-readable project name |
| `flg_version` | string | FLG version that last wrote this state |
| `created_at` | string | ISO timestamp of project creation |
| `updated_at` | string | ISO timestamp of last update |
| `current_stage` | string | Current project stage |
| `last_closeout_at` | string/null | Last closeout timestamp |
| `pending_patches` | array | List of pending patch objects |
| `next_actions` | array | List of next action strings |
| `active_agent` | string/null | Currently active agent |
| `dirty_files` | array | Files with uncommitted changes |
| `last_snapshot_hash` | string/null | Hash of last snapshot |

### Variant Field Map (legacy compatibility)

The CLI reads these alternative key names from older or skill-written states. No forced rewrite — compatibility is handled at read time.

| Canonical | Variants |
|-----------|----------|
| `project_name` | `name` |
| `created_at` | `created`, `date_created` |
| `updated_at` | `updated`, `last_updated` |
| `current_stage` | `phase`, `current_phase`, `phase_status`, `status` |
| `flg_version` | `version` |

### Extension Fields

Any key not in the core set is treated as a **project-specific extension**. The CLI preserves these fields but never depends on them. Examples from real projects: `linked_projects`, `platforms_tracked`, `database_path`, `decision_log_format`, `content_lines`.

### Schema Health

Run `flg state-schema` to see your project's state health:
- **ok** — all core fields present, no variant mappings needed
- **legacy** — variant field names detected, but all core fields can be resolved
- **degraded** — some core fields are missing and cannot be autofilled

## Decision Log Protocol

Decision logs are the most durable asset in a project. They record not just what was decided, but why — the context, alternatives considered, reasoning, and conditions under which the decision should be revisited.

When an agent reads DECISIONS.md, it should:
1. Understand the reasoning chain, not just the conclusions
2. Avoid re-suggesting rejected alternatives without new evidence
3. Reference past decisions when making new recommendations

When an agent generates a closeout, it should extract:
- What was decided (confirmation/trade-off signals)
- Why it was decided (reasoning from the conversation)
- What was rejected (alternatives mentioned and why they were dropped)
- What could reverse the decision (trigger conditions)

## Agent Capabilities

When working on a FLG project, an agent should be capable of three things:

### Memory QA (项目记忆问答)
User: "我们之前为什么不做KOL？"
Agent: Reads DECISIONS.md, finds D-XXX, returns the reasoning chain.

### Context Enhance (上下文增强)
User: "我想做一个新的推广方案"
Agent: Reads FRAMING.md + DECISIONS.md + SNAPSHOT.md, then asks:
  "基于之前的判断（预算有限、私域优先），你这次想沿用还是调整？"

### Context Critic (上下文审计)
User: "客户说要投KOL"
Agent: Reads DECISIONS.md, finds D-XXX (rejected KOL), then says:
  "之前判断过KOL ROI不确定（D-XXX）。有新信息改变了这个判断吗？"

---

*FlowGrid v{__version__}*
"""

DOCS_README_MD = """# Project Materials Index

> 本目录存放项目素材：调研报告、会议纪要、背景资料、客户情报等过程性文档。
> FLG 不扫描也不审计 docs/，这里不是正式账本，是参考区。
> 当素材与正式账本冲突时，以账本为准。
> 用这个文件作为索引，让接手的 agent 一眼看到 docs/ 里有什么。

## 素材清单

> 每加一个素材文件，在这里登记一行。格式：`- [文件名](文件名) — 一句话说明`

- (尚无素材)

## 建议子目录

如果素材变多，可按类型分子目录：

- `research/` — 调研报告、行业分析
- `meetings/` — 会议纪要
- `background/` — 背景资料、客户情报
- `assets/` — 图片、PDF 等非文本素材

子目录是可选的，项目早期可以直接把文件放 docs/ 根目录。
"""

ANCHORS_MD = """# Authoritative Anchors

> 定义当前项目的权威锚点文件。
> 同一主题下只有一份文件是"当前真相"，其他版本只能当参考或汇报壳。
> Agent 接手时应优先读取锚点文件，冲突时以锚点为准。

## Anchors

<!-- 复制以下模板，每条锚点一个 -->

### [主题名称]

- **File:** (文件路径)
- **Role:** (文档职责，自由填写，如：技术基线 / 预算口径 / 汇报稿 / 创意brief)
- **Authority:** authoritative | working | reference_only
- **Provenance:** internal | external | mixed
- **Lifecycle:** active | superseded | archived
- **Updated:** (日期)
- **Notes:** (简要说明为什么这份是锚点)

---

*Created: {created_at}*
*Last Updated: {updated_at}*
"""

# --- Fixed enums (universal, any project) ---

DOC_AUTHORITIES = [
    "authoritative",         # 当前权威版本，冲突时以此为准
    "working",               # 工作版本，可能随时更新
    "reference_only",        # 仅参考，不作为实施依据
]

DOC_PROVENANCES = [
    "internal",              # 内部产出
    "external",              # 外部输入
    "mixed",                 # 多方混合
]

DOC_LIFECYCLES = [
    "active",                # 当前有效
    "superseded",            # 已被新版本替代
    "archived",              # 已归档
]

# --- Open fields (examples, not enums — user defines per project) ---

DOC_ROLE_EXAMPLES = [
    "technical_baseline",    # 技术基线：定义真实可交付边界
    "budget_scope",          # 预算口径：解释预算和工作包
    "reporting_draft",       # 汇报稿：对上讲顺、讲大、讲成立
    "submission_draft",      # 报送稿：外部报送/联合稿
    "external_input",        # 外部输入：合作方回传，仅参考
    "creative_brief",        # 创意简报
    "data_report",           # 数据报告
    "client_proposal",       # 客户提案
]

ROLE_TEMPLATES = {
    "strategy": {
        "project_type": "strategy",
        "problem_statement": "需要澄清目标、边界、评审逻辑和推进路径。",
        "explicit_requirements": "- 明确这次判断要服务的业务问题\n- 明确评审对象与评审标准",
        "real_needs": "- 用户可能真正需要的是更清晰的取舍逻辑，而不是更多材料",
        "goals": "- 明确高层目标\n- 形成至少一条可推进的路径",
        "non_goals": "- 不在本轮展开完整执行计划",
        "user_objects": "- 决策人 / 业务负责人 / 方案拥有者",
        "review_objects": "- 是否讲清楚目标、边界、取舍、推进路径",
        "success_criteria": "- 评审人能明确说出为什么做、为什么不做",
        "constraints": "- 时间有限\n- 信息不完整",
        "open_questions": "- 当前最高优先级目标是否稳定？\n- 本轮不做什么是否已经讲清？",
        "goal_evolution": "## Goal Shift 001\n\n- **When:** {created_at}\n- **Previous Goal:** (none)\n- **New Goal:** Clarify business goal, boundary, and review logic\n- **Trigger:** Project initialized with strategy template\n- **Impact:** FRAMING.md / SNAPSHOT.md / decision criteria\n",
        "constraint_block": "### Constraint 001\n\n- **If:** 目标与资源不匹配\n- **Then:** 优先收缩范围，而不是继续扩展讨论\n- **Unless:** 决策人明确要求做多方案并行推演\n- **Owner:** strategy lead\n- **Review Trigger:** 评审对象变化或资源假设变化\n",
    },
    "marketing": {
        "project_type": "marketing",
        "problem_statement": "需要把 campaign 判断、brief、素材方向和交接状态收成一个可续接项目。",
        "explicit_requirements": "- 明确 campaign 目标\n- 明确关键素材与上线节奏",
        "real_needs": "- 用户可能真正需要的是减少反复解释创意方向和预算边界",
        "goals": "- 锁定 campaign 方向\n- 让素材、判断、时间点能关联起来",
        "non_goals": "- 本轮不搭完整投放后台",
        "user_objects": "- 营销负责人 / 内容负责人 / 设计协作方",
        "review_objects": "- brief 是否清楚\n- 关键动作是否能按节奏推进",
        "success_criteria": "- 团队能明确当前方向、素材缺口和下一步动作",
        "constraints": "- 时效性高\n- 预算变化快\n- 素材版本多",
        "open_questions": "- 当前核心素材版本是哪一版？\n- 哪些判断已经确认，哪些只是创意草案？",
        "goal_evolution": "## Goal Shift 001\n\n- **When:** {created_at}\n- **Previous Goal:** (none)\n- **New Goal:** Align campaign direction, key assets, and launch rhythm\n- **Trigger:** Project initialized with marketing template\n- **Impact:** brief / asset list / rollout plan\n",
        "constraint_block": "### Constraint 001\n\n- **If:** campaign 上线时间提前\n- **Then:** 优先冻结素材范围和审核路径\n- **Unless:** 目标人群或投放渠道被同时调整\n- **Owner:** marketing lead\n- **Review Trigger:** 预算、上线日期或素材负责人发生变化\n",
    },
    "operations": {
        "project_type": "operations",
        "problem_statement": "需要把机制设计、节奏、约束和复盘依据收成可复用、可续接的规则结构。",
        "explicit_requirements": "- 明确运行规则\n- 明确节奏和责任边界",
        "real_needs": "- 用户可能真正需要的是避免机制靠口头传递、每次重新对齐",
        "goals": "- 让机制规则可追踪\n- 让复盘时能回溯为什么这样设计",
        "non_goals": "- 本轮不接复杂自动化平台",
        "user_objects": "- 运营负责人 / 执行人 / 复盘人",
        "review_objects": "- 规则是否清晰\n- 例外条件是否明确",
        "success_criteria": "- 新接手的人能按规则运行而不需要反复口头解释",
        "constraints": "- 条件逻辑多\n- 依赖数据验证\n- 多项目并行",
        "open_questions": "- 哪些规则是硬约束，哪些是经验性建议？\n- 哪些数据是复盘必需证据？",
        "goal_evolution": "## Goal Shift 001\n\n- **When:** {created_at}\n- **Previous Goal:** (none)\n- **New Goal:** Capture operating rules, cadence, and exception logic\n- **Trigger:** Project initialized with operations template\n- **Impact:** rules / reviews / handoff expectations\n",
        "constraint_block": "### Constraint 001\n\n- **If:** 指标连续两周未达标\n- **Then:** 触发复盘并重审当前机制\n- **Unless:** 外部依赖或资源供给已被确认异常\n- **Owner:** operations lead\n- **Review Trigger:** 节奏、指标口径或责任人发生变化\n",
    },
    "solution": {
        "project_type": "solution",
        "problem_statement": "需要把客户需求翻译成方案判断和可交付路径，并追踪变更影响。",
        "explicit_requirements": "- 明确客户需求\n- 明确交付边界与验收条件",
        "real_needs": "- 用户可能真正需要的是减少需求变化导致的交付路径重建成本",
        "goals": "- 把需求、方案、交付路径挂起来\n- 让需求变化的影响可回溯",
        "non_goals": "- 本轮不做完整项目管理平台",
        "user_objects": "- 客户 / 方案负责人 / 交付负责人",
        "review_objects": "- 需求是否翻译准确\n- 交付边界是否说清",
        "success_criteria": "- 任一需求变更都能快速定位受影响的方案和动作",
        "constraints": "- 需求变化频繁\n- 商务与技术语言并存",
        "open_questions": "- 当前哪份文档定义了真实交付边界？\n- 哪些需求是确认的，哪些仍在讨论？",
        "goal_evolution": "## Goal Shift 001\n\n- **When:** {created_at}\n- **Previous Goal:** (none)\n- **New Goal:** Translate customer demand into a clear solution and delivery path\n- **Trigger:** Project initialized with solution template\n- **Impact:** requirements / proposal / delivery planning\n",
        "constraint_block": "### Constraint 001\n\n- **If:** 客户新增需求影响交付范围\n- **Then:** 必须重新评估方案、时间和成本影响\n- **Unless:** 新增需求仅属于文案表述调整\n- **Owner:** solution lead\n- **Review Trigger:** 需求、预算或验收标准发生变化\n",
    },
}

LESSONS_LEARNED_MD = """# Lessons Learned

> 记录"后来验证对不对"。决策日志记录"当时为什么这么做"，这里记录"结果如何"。
> 阶段结果出现后，校验原判断，沉淀可复用经验。

---

*Created: {created_at}*
*Last Updated: {updated_at}*
"""

RATIONALE_TRAIL_MD = """# Rationale Trail

> 记录思考过程：争议、摇摆、灵感来源、外部信息、AI对话中的判断变化。
> 决策日志记录"收束点"，这里记录"推导过程"。

---

*Created: {created_at}*
*Last Updated: {updated_at}*
"""

DECISION_PROMPT_TEMPLATE = """# FLG Decision Extraction Prompt

## 你的任务

从以下对话记录中，识别所有关键决策，并按9字段模板生成结构化决策日志。

## 9字段模板

每条决策必须包含以下字段（如果对话中找不到信息，标注"对话中未提及"）：

```
## D-XXX | 标题

### 决策时间
(从对话中推断日期，或写"对话日期")

### 所属阶段
(立项/创意策划/执行/复盘/收手)

### 决策背景
(为什么需要做这个判断？当时发生了什么？遇到了什么问题？)

### 核心问题
(到底在问什么？要解决什么？)

### 备选方案
A. (方案A)
B. (方案B)
C. (方案C)
(如果对话中只提到一个方案，写"对话中未提及其他备选方案")

### 最终决策
(选了什么？结论是什么？)

### 决策理由
(为什么选这个？依据是什么？数据/经验/逻辑是什么？)

### 放弃理由
(为什么不选其他方案？其他方案有什么问题？)

### 风险判断
(这个选择有什么风险？有什么不确定性？)

### 后续验证
(怎么验证这个判断对不对？什么指标/反馈能说明问题？)

### 复盘入口
(什么情况下需要重新审视这个决策？什么条件变了就需要改？)
```

## 规则

1. 只提取真正的决策（做了选择、定了方向、拍了板），不要提取讨论、问题、状态描述
2. 如果对话中没有明确的决策，输出"本轮对话无明确决策"
3. 每条决策必须有"决策理由"——如果对话中没说为什么，标注"对话中未说明理由"
4. 保留对话中的原始措辞，不要过度概括
5. 输出格式为Markdown，可直接作为DECISIONS.md的追加内容

## 对话记录

{transcript}

## 输出

请按上述模板，输出所有识别到的决策。如果本轮无明确决策，输出"本轮对话无明确决策"。
"""

# ── v0.2.3: Closeout-specific LLM prompt (JSON-structured output) ──────────
# This prompt is used by flg closeout --llm to extract decisions with
# structured fields that map to the keyword-extraction patch format.

CLOSEOUT_LLM_PROMPT_TEMPLATE = """你是一个项目决策提取器。从以下会话记录中提取所有关键决策。

## 什么是决策

决策 = 做了选择、定了方向、拍了板、明确了取舍。不是讨论、不是问题、不是状态描述。

特别注意以下类型的决策（它们往往不包含"确认/决定/优先"等明显触发词）：
- 机制设计判断（如"审批触发条件应基于金额阈值而非角色层级"）
- 架构取舍（如"用A方案而不用B，因为..."）
- 范围界定（如"这个阶段只做X不做Y"）
- 顺序决策（如"先做X，Y延后到下一阶段"）
- 边界划分（如"这个不属于我们的scope"）

## 输出格式

严格输出一个JSON对象，包含一个 `decisions` 数组。每条决策包含以下字段：

```json
{{
  "decisions": [
    {{
      "id": "D-LLM-001",
      "what": "决定了什么（核心内容，一句话说清）",
      "type": "explicit_confirmation | tradeoff | state_change | mechanism_design | scope_boundary",
      "confidence": "high | medium | low",
      "why": "为什么做这个决策（理由、依据、数据/经验/逻辑）",
      "rejected": "放弃了什么替代方案（如果有）。没有则填\"对话中未提及其他方案\"",
      "reverse_condition": "什么条件下这个决策可能需要推翻",
      "source_excerpt": "对话中做出该判断的原句（直接引用）"
    }}
  ]
}}
```

## 规则

1. 每条决策的 `what` 必须是对决策内容的精确概括，保留原始措辞
2. `why` 必须从对话中提取，如果对话中没说明理由，填"对话中未说明理由"
3. 不要虚构字段内容——找不到就写"对话中未提及"
4. 如果对话中没有明确决策，输出 `{{"decisions": []}}`
5. 只输出JSON，不要额外文字解释

## 会话记录

{transcript}

## 输出

只输出JSON，无其他内容。
"""

FRAME_PATCH_MD = """# FLG Patch

patch_id: {patch_id}
project: {project_name}
generated_at: {generated_at}
source_command: flg frame
risk_level: medium
status: pending_review

---

## 1. Frame Analysis Summary

{summary}

## 2. Missing Fields

{missing_fields}

## 3. Suggested Questions

{suggested_questions}

## 4. Draft Content for FRAMING.md

{draft_content}

## 5. Needs Human Review

- [ ] Review missing fields
- [ ] Answer suggested questions
- [ ] Confirm draft content before merging

---

*Generated by flg frame*
"""

CLOSEOUT_PATCH_MD = """# FLG Patch

patch_id: {patch_id}
project: {project_name}
generated_at: {generated_at}
source_command: flg closeout
source_transcript: {source_transcript}
risk_level: medium
status: pending_review

---

## 1. Session Summary

{summary}

## 2. Suggested PROGRESS.md Entry

```markdown
### {date}: Session Progress

- **What happened:** {what_happened}
- **What was produced:** {what_produced}
- **What was modified:** {what_modified}
- **What problems arose:** {what_problems}
- **Next step:** {next_step}
```

## 3. Candidate Decisions

{candidate_decisions}

## 4. Suggested SNAPSHOT.md Updates

{snapshot_updates}

## 5. New Open Questions

{open_questions}

## 6. New Risks

{risks}

## 7. Evidence Excerpts

{evidence}

## 8. Needs Human Review

- [ ] Review and approve PROGRESS.md entry
- [ ] Confirm or reject candidate decisions (including reasoning, alternatives, reversal conditions)
- [ ] Review SNAPSHOT.md updates
- [ ] Address new open questions
- [ ] Evaluate new risks

---

*Generated by flg closeout*
"""
