# Judgment Capture Pipeline — Design RFC

- **Status:** draft
- **Created:** 2026-07-08
- **Author:** FlowGrid maintainers
- **Scope:** v0.4 前置设计，不等 v0.3 全部完成即可开始设计讨论

---

## 1. 问题定义

### 1.1 当前状态

FLG v0.3 的决策捕获链路是 **批量的、事后的**：

```
会话结束 → closeout（扫描 transcript）→ review patch → merge → DECISIONS.md
```

时间窗口：从"判断产生"到"写入决策日志"的延迟等于整个会话时长。

### 1.2 目标状态

增加一条 **实时的、逐条的** 链路：

```
用户说话 → Agent 检测判断 → capture add → review → DECISIONS.md
```

时间窗口：从"话音刚落"到"写入候选池"在秒级。

两条链路**互补不互斥**：
- closeout 继续做批量扫尾 + 提示遗漏
- capture 做实时逐条捕获

### 1.3 核心挑战

"实时捕获"的关键难题不在 CLI 命令设计，而在 **Agent 层的检测触发机制**：

1. **什么时候触发？** 用户自然语言中如何识别"这是一个判断"？
2. **粒度怎么定？** 一句话 = 一条判断？还是一段推理 = 一条判断？
3. **噪音怎么控制？** 不是每句"我觉得"都是判断，过度捕获比漏掉更糟糕
4. **证据怎么保留？** 实时捕获的优势是证据新鲜，但需要 Agent 能从对话中提取原话

这些问题不由 FLG CLI 解决，而是由 AI Agent（Hermes/Codex/Claude）在调用 FLG 之前解决。FLG CLI 只负责：**接收结构化数据，写入标准化格式**。

---

## 2. 设计原则

### 2.1 不对 GPT 建议照单全收

GPT 的建议整体方向正确，但需要结合 FLG 现有架构做判断。以下是我**挑战 GPT 建议的点**：

| GPT 建议 | 我的判断 | 理由 |
|----------|----------|------|
| 两套命令族（capture + decision） | **不建新族，扩展现有链路** | FLG 已有 closeout→review→merge，capture 产出汇入同一个 review 流程即可。新建 decision 命令族会造成两个并行体系 |
| status: candidate / merged | **对齐现有 judgment-status-model** | 已有 pending_review / confirmed / rejected。不需要 candidate/merged |
| judgment_profile 文件 | **P0 不做，预留扩展点** | 有价值但 P0 过度设计。Agent 检测逻辑用触发词即可，不序列化为 profile |
| 没有讨论 Agent 层检测 | **补充 Agent 层设计** | 这是实时捕获的核心难点，不能只设计 CLI 而忽略调用方 |

### 2.2 对齐现有架构

- **状态模型：** judgment-status-model.md 已定义 `pending_review` / `confirmed` / `rejected` / `superseded` 等，不新增
- **存储位置：** `.flg/captures/` 目录，和 `.flg/patches/` 对等——patches 是"待审核的文档变更"，captures 是"待审核的判断候选"
- **正式账本：** DECISIONS.md 只存 confirmed decision，candidate 不直接写入
- **patch-first 原则：** capture 产出是 candidate（pending_review），不是正式事实。Agent 可以读取但不能当作 confirmed truth

---

## 3. 数据模型

### 3.1 Capture 文件格式

```
.flg/captures/cap-20260708-153000-a1b2c3.md
```

每个 capture 一个文件，YAML frontmatter + markdown body：

```yaml
---
id: cap-20260708-153000-a1b2c3
created_at: 2026-07-08T15:30:00
type: judgment                # P0: judgment | decision | principle
status: pending_review        # 对齐 judgment-status-model
confidence: inferred          # P0: inferred | confirmed
source: user_text             # user_text | agent_summary
review_required: true

# 以下字段来自现有 DECISIONS_MD 模板
question: "技术栈选型"
claim: "使用 PostgreSQL 替代 MongoDB"
rationale: "数据关系复杂需要 JOIN 查询，MongoDB 的文档模型不适合"
alternatives:
  - "MongoDB"
  - "MySQL"
risks: "团队 PostgreSQL 运维经验不足"
raw_evidence: "板子原话：'我觉得应该用 PG 而不是 Mongo，因为后面肯定要做复杂查询，Mongo 那个文档模型搞不了 JOIN'"

# 扩展字段（P1+）
tags: ["tech", "infra"]
reversal_conditions:
  - "如果团队招聘到 MongoDB 专家"
related_decisions: []
---
```

### 3.2 字段说明

| 字段 | 来源 | P0/P1 | 说明 |
|------|------|-------|------|
| id | FLG 生成 | P0 | `cap-{timestamp}-{random}` |
| created_at | FLG 生成 | P0 | ISO 8601 |
| type | Agent 提供 | P0 | `judgment`（取舍判断）/ `decision`（强承诺）/ `principle`（工作原则） |
| status | FLG 管理 | P0 | `pending_review` → `confirmed` / `rejected` |
| confidence | Agent 提供 | P0 | `inferred`（Agent 推断）/ `confirmed`（用户明确确认） |
| source | Agent 提供 | P0 | `user_text`（用户原话）/ `agent_summary`（Agent 归纳） |
| review_required | FLG 计算 | P0 | type=judgment 且 confidence=inferred → true |
| question | Agent 提供 | P0 | 这条判断回答什么问题 |
| claim | Agent 提供 | P0 | 判断主张 |
| rationale | Agent 提供 | P0 | 判断理由 |
| alternatives | Agent 提供 | P1 | 被放弃的备选方案 |
| risks | Agent 提供 | P1 | 风险判断 |
| raw_evidence | Agent 提供 | P0 | 用户原话引用 |
| tags | Agent 提供 | P2 | 分类标签 |
| reversal_conditions | Agent 提供 | P2 | 什么条件下需要重新审视 |

### 3.3 type 和 status 是两个正交维度

```
type（判断性质）              status（生命周期）
─────────────                ─────────────
judgment   → 取舍型判断       pending_review → 候选，待审核
decision   → 强承诺决策       confirmed      → 已确认
principle  → 工作原则         rejected       → 已拒绝
                             superseded     → 已被新判断替代
```

一个 `type=judgment` 的 capture 经过 review 后 status 变为 `confirmed`，它就是正式决策——不需要改变 type。

---

## 4. 命令设计

### 4.1 新增命令

```bash
# 捕获候选判断
flg capture add \
  -c "使用 PostgreSQL 替代 MongoDB" \
  -r "数据关系复杂需要 JOIN" \
  -t judgment \
  -q "技术栈选型" \
  -e "板子原话：我觉得应该用 PG"

flg capture list                  # 列出所有 candidate（按状态筛选）
flg capture list --status pending_review
flg capture show cap-20260708-001 # 查看单条

# 批量审核
flg capture review                # 交互式逐条审核 candidate
flg capture review --auto-confirm # 自动确认 confidence=inferred 的 candidate（危险，需确认）
```

### 4.2 强承诺信号直入 Decision

只有以下信号触发时，跳过 capture 阶段直接写入 DECISIONS.md：

- "记一条"
- "定了"
- "写进决策日志"
- "后续按这个推进"
- "这个作为原则"

```bash
flg decision add \
  -d "技术栈确定为 PostgreSQL" \
  -r "已验证两周无问题，团队已培训" \
  --principle                    # 标记为 principle 类型
```

`flg decision add` 不走 capture 流程，直接写入 DECISIONS.md（status=confirmed）。这是"用户明确指令驱动的写入"，不走 patch——和 `flg capture add` 的直接写入理由一致：都是用户明确触发的。

### 4.3 与现有命令的关系

```
现有链路（批量）：
  closeout → review --patch → merge → DECISIONS.md

新增链路（实时单条）：
  capture add → capture review ──→ merge → DECISIONS.md
                                └─→ 拒绝（status=rejected）

新增链路（强承诺直入）：
  decision add → DECISIONS.md（跳过 capture 和 review）
```

`capture review` 确认的 candidate 通过**现有 `flg merge`** 写入 DECISIONS.md——不新建 merge 命令。

### 4.4 为什么不需要 capture 独立的 merge

GPT 建议 `flg decision confirm <capture_id>`。但我认为不需要。

现有 `flg merge --patch` 的语义是"将待审核内容合并到正式账本"，capture review 确认后生成一个内部 merge patch，走同一个 `flg merge` 路径。新建 `decision confirm` 会让用户困惑："capture review 和 decision confirm 有什么区别？"

**一个原则：review 和 merge 的职责不耦合到 capture 命令里。** capture 只负责"捕获候选"，review 负责"审核"，merge 负责"入账"。

---

## 5. Agent 层检测机制

### 5.1 这不是 FLG CLI 的职责

FLG CLI 不知道用户什么时候说了判断。检测由 AI Agent 完成，FLG 只暴露 capture add 接口。

### 5.2 检测触发条件

Agent 在以下条件**同时满足**时，调用 `flg capture add`：

1. **包含判断信号词**（取舍/方向/边界/改变类关键词）
2. **不是纯陈述**（"PostgreSQL 支持 JSON"是陈述，"我们应该用 PostgreSQL"是判断）
3. **不是对话管理**（"先做A再做B"是任务排序不是判断）
4. **判断有理由支撑**（"选A"没有理由 → 不捕获；"选A因为B"有理由 → 捕获）

### 5.3 触发模式

| 模式 | 触发条件 | 行为 |
|------|----------|------|
| 提示模式（默认） | 检测到判断信号 | 主动问"要不要记一条？"→ 确认后调 capture add |
| 自主模式（GDM 中） | 检测到判断信号 | 自动调 capture add，confidence=inferred，closeout 时统一 review |
| 强承诺模式 | 用户说"记一条/定了/写进决策日志" | 直接调 decision add，跳过 capture |

### 5.4 误报处理

Agent 的检测不可能 100% 准确。设计上接受误报：

- **误报（假阳性）：** capture review 时 reject → 成本低，一条 rejected candidate
- **漏报（假阴性）：** closeout 批量扫描补充 → 二次保障

不做"完美检测"——closeout 就是安全网。

---

## 6. 与现有文档的冲突分析

### 6.1 CONTRACT.md

CONTRACT 定义"决策更新属于高风险写入，必须走 patch"。

- `flg capture add` 写入 `.flg/captures/`（candidate），**不修改 DECISIONS.md** → 不冲突
- `flg decision add` 直接写 DECISIONS.md（用户明确指令）→ **冲突**，需在 CONTRACT 中增加例外条款

**建议：** 在 CONTRACT.md 的 Write Risk Levels 表中增加一行：

```
| Direct （用户明确指令）| DECISIONS.md（通过 flg decision add） | 用户明确触发的写入，不走 patch |
```

### 6.2 DECISIONS.md

DECISIONS.md 仍只存 confirmed decision。candidate 在 `.flg/captures/`。✅ 不冲突。

### 6.3 closeout 命令

当前 closeout 从 transcript 提取决策。capture 不替代 closeout，两者并存。✅ 不冲突。

未来 (P3) 可以调整 closeout 的职责：
- 不再从零提取决策（因为已在 capture 中逐条记录）
- 改为：扫描 `.flg/captures/` 中 pending_review 的 candidate，提示用户审核
- 同时扫描 transcript 中可能遗漏的判断

### 6.4 judgment-status-model.md

capture 的 status 字段直接使用现有模型（pending_review / confirmed / rejected）。✅ 不冲突。

### 6.5 v0.3-plan.md

v0.3 计划聚焦 Context Pack + Evidence Trace + Eval Set。capture pipeline 不在当前计划中。⚠ 需插入占位。

### 6.6 current-state.md

stop rule 明确："Do not add new commands before README patch and test rerun are complete."

capture 命令实现应排在 v0.3 基础稳定之后。设计文档可以先落，代码实现不抢跑。

---

## 7. P0 / P1 / P2 范围

| 优先级 | 内容 | 依赖 | 理由 |
|--------|------|------|------|
| **P0** | Design RFC 文档（本文档） | 无 | 先锁定设计 |
| **P0** | `flg capture add` | Design RFC 完成 | 最小可用的实时捕获 |
| **P0** | `flg capture list` | capture add | 查看候选池 |
| **P0** | `flg capture show` | capture add | 查看详情 |
| **P1** | `flg capture review` | capture add/list | 审核流程闭环 |
| **P1** | `flg decision add` | capture add | 强承诺信号直入 |
| **P1** | Agent 检测逻辑（flg-workflow skill 更新） | capture add 可用 | Agent 层调用 |
| **P2** | type 扩展：thought / hypothesis | dogfood 后 | 需要验证粒度 |
| **P2** | judgment_profile 机制 | Agent 检测稳定后 | 个性化触发词 |
| **P3** | closeout 职责调整 | capture 链路跑通 | 收敛两条链路 |

---

## 8. 实现计划

### Phase 0 — Design Lock（当前）

- [x] 调研现有 FLG 设计文档
- [ ] Design RFC 完成并由板子终审
- [ ] v0.3-plan.md 插入 Phase 1.5 占位

### Phase 1 — CLI 骨架

依赖：v0.3 Phase 1-2（Context Pack + Protocol Alignment）完成后。

- [ ] 实现 `flg capture` 命令组（add / list / show）
- [ ] 创建 `.flg/captures/` 存储结构
- [ ] smoke test 覆盖 capture 命令

### Phase 2 — Review + Decision

- [ ] 实现 `flg capture review`（交互式逐条审核）
- [ ] 实现 `flg decision add`（强承诺直入）
- [ ] 更新 CONTRACT.md 补充 decision add 例外条款
- [ ] 和现有 merge 命令打通（capture review 确认后自动生成 merge patch）

### Phase 3 — Agent 层集成

- [ ] 更新 flg-workflow skill，加入 capture 触发逻辑
- [ ] dogfood：在真实项目中用 capture 逐条捕获判断
- [ ] 收集误报/漏报数据

### Phase 4 — 收敛

- [ ] 调整 closeout 职责（从"提取决策"到"审核候选 + 提示遗漏"）
- [ ] 评估是否扩展 type 到 thought / hypothesis

---

## 9. 设计决策记录

以下是我主动做出的判断（板子可以推翻）：

| # | 决策 | 理由 |
|---|------|------|
| 1 | 不建 capture + decision 两套命令族 | FLG 已有 review→merge 链路，capture 汇入即可。新建 decision 族会造成两个并行体系 |
| 2 | status 对齐现有 judgment-status-model | 已有 pending_review/confirmed/rejected，不需要 candidate/merged |
| 3 | judgment_profile P0 不做 | 有价值但过度设计。先跑通基本链路再抽象 |
| 4 | type 只做 judgment/decision/principle 三个 | thought/hypothesis 需要 dogfood 验证粒度，P1 加 |
| 5 | capture 产出存 .flg/captures/ 而非 CAPTURES.md | 单文件多 candidate 的 markdown 不利于程序化读取和 review |
| 6 | closeout 暂不调整职责 | 先让两条链路并存，P3 收敛。现在就改 closeout 破坏了 v0.3 的稳定目标 |
| 7 | decision add 直接写 DECISIONS.md 不走 patch | 这是用户明确指令驱动的写入，和 capture add 写入 .flg/captures/ 同逻辑——用户明确触发的不需要 patch 保护层 |

---

## 10. 待板子拍板的问题

1. **命令名用 `flg capture` 还是 `flg judgment`？** 我的建议是 capture（动词，直观），但 judgment 和现有文档术语一致。

2. **decision add 直接写 DECISIONS.md 是否接受？** 这打破了 patch-first 原则，但理由是"用户明确指令"。如果板子认为不妥，可以改为"decision add 也生成 patch，但 auto-approved"。

3. **capture review 确认后自动 merge 还是需要手动 flg merge？** 我倾向自动 merge（capture review --confirm 即合并），减少步数。

4. **type 字段是否应该叫别的名字？** "type" 和 Python 内置冲突，可能叫 "judgment_type" 更好，但 YAML frontmatter 没有这个问题。板子怎么看？
