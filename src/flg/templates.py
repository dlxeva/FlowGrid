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

## Reading Priority (when context is limited)

1. `.flg/CONTRACT.md`
2. `SNAPSHOT.md`
3. `FRAMING.md`
4. `DECISIONS.md`
5. `.flg/patches/` (all pending_review patches)

## Write Risk Levels

| Risk Level | Files | Strategy |
|------------|-------|----------|
| Low | PROGRESS.md | Direct append |
| Medium | SNAPSHOT.md, FRAMING.md (supplement) | Generate patch |
| High | FRAMING.md (modify goals/boundaries), DECISIONS.md (override), PROJECT.md | Must patch + human confirm |

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
