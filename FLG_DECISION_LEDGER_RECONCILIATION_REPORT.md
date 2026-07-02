# FLG Decision Ledger Reconciliation Report

**Date:** 2026-06-25
**Version:** v0.1.5-alpha
**Status:** 对账完成，待人工确认

---

## 1. 当前 DECISIONS.md 总体质量判断

**总体评估：** ⚠️ 中等质量

**优点：**
- 每条决策都有完整的推导结构（备选方案、决策理由、放弃理由、风险判断）
- 决策内容基本准确
- 与项目演进基本一致

**问题：**
- 编号重复（D-010 出现两次）
- 内容重复（D-001 和 D-008 都是命名）
- 内容矛盾（D-007 和 D-009 关于 Legacy Audit）
- 层级混乱（实现细节与核心决策混在一起）
- 遗漏重要决策

---

## 2. 决策数量统计

| 统计项 | 数量 |
|--------|------|
| 当前总决策数 | 12 |
| 独立决策数 | 11（D-010 重复） |
| 重复决策 | 2（D-001/D-008, D-007/D-009） |
| 遗漏决策 | 4（待确认） |
| 过细决策 | 1（D-010a Typer） |

---

## 3. 重复决策

### 3.1 D-001 和 D-008（产品命名）

**问题：** 两条都是关于产品命名

**分析：**
- D-001：产品名暂定 Framing Ledger / FLG
- D-008：产品名从 OMP 调整为 Framing Ledger / FLG

**关系：** D-008 是 D-001 的修正/取代

**建议：**
- D-001 标记为 superseded（被取代）
- D-008 保留为 accepted（当前有效）

### 3.2 D-007 和 D-009（Legacy Audit）

**问题：** 两条内容矛盾

**分析：**
- D-007：v0.1 必须新增 Legacy Audit 模块
- D-009：v0.1 Core 聚焦 init/frame/closeout，Legacy Audit 拆到 v0.1.5

**关系：** D-009 取代了 D-007

**建议：**
- D-007 标记为 superseded（被取代）
- D-009 保留为 accepted（当前有效）

---

## 4. 遗漏决策

### 4.1 候选决策 A：不追求技术精度，追求认知事件级精度

**来源：** MEMORY 中的用户偏好

**内容：** Framing Ledger 的核心价值不是技术层面的全自动准确提取，而是捕捉项目推进中的认知事件

**证据：**
> 产品哲学："不追求技术精度，追求认知事件级精度"

**建议分类：** Project Decision

**建议处理：** add_missing（补充到正式 DECISIONS.md）

**理由：** 这是产品核心哲学，影响所有设计决策

### 4.2 候选决策 B：改造现有结构而非新建目录

**来源：** MEMORY 中的用户偏好

**内容：** FLG 应优先适配和改造用户已有项目结构，而不是强制用户迁移到全新目录结构

**证据：**
> 板子偏好"改造现有结构"而非"新建目录"

**建议分类：** Architecture Decision

**建议处理：** add_missing（补充到正式 DECISIONS.md）

**理由：** 这是架构核心原则，影响 audit/import 设计

### 4.3 候选决策 C：先做再改

**来源：** MEMORY 中的用户偏好

**内容：** 当前开发方式采用快速实现、验收、暴露问题、再修协议的方式推进

**证据：**
> 板子偏好"先做再改"

**建议分类：** Workflow Decision

**建议处理：** add_missing（补充到正式 DECISIONS.md）

**理由：** 这是工作方式决策，影响开发节奏

### 4.4 候选决策 D：Harness Engineering 不是 Scaffolding

**来源：** MEMORY 中的概念定义

**内容：** Harness Engineering（H开头，像马鞍）= 约束框架工程（输入/输出/行为/质量约束），不是 Scaffolding

**证据：**
> Harness Engineering（H开头，像马鞍）= 约束框架工程（输入/输出/行为/质量约束），不是Scaffolding

**建议分类：** Project Decision

**建议处理：** needs_human_review（需要确认是否与 FLG 相关）

**理由：** 这是概念定义，但需要确认是否是 FLG 的核心概念

---

## 5. 过细决策

### D-010a：v0.1 Core 使用 Typer 作为 CLI 框架

**问题：** 这是实现细节，不是核心决策

**建议处理：** downgrade_to_implementation_note（降级为实现说明）

**理由：**
- 不影响产品方向
- 不影响架构设计
- 可以在 IMPLEMENTATION_REPORT.md 中记录

---

## 6. 缺推导过程的决策

**检查结果：** ⚠️ 大部分决策有推导过程

| 决策 | 推导过程 | 备选方案 | 放弃理由 |
|------|---------|---------|---------|
| D-001 | ✅ | ✅ | ✅ |
| D-002 | ✅ | ✅ | ✅ |
| D-003 | ✅ | ✅ | ✅ |
| D-004 | ✅ | ✅ | ✅ |
| D-005 | ✅ | ✅ | ✅ |
| D-006 | ✅ | ✅ | ✅ |
| D-007 | ✅ | ✅ | ✅ |
| D-008 | ✅ | ✅ | ✅ |
| D-009 | ✅ | ✅ | ✅ |
| D-010a | ✅ | ✅ | ✅ |
| D-011 | ✅ | ✅ | ✅ |
| D-010b | ✅ | ✅ | ✅ |

**结论：** 推导过程完整

---

## 7. 缺来源证据的决策

**检查结果：** ⚠️ 大部分决策缺来源证据

| 决策 | 来源类型 | 来源路径 | 证据 |
|------|---------|---------|------|
| D-001 | dialogue | ChatGPT 对话 | ⚠️ 缺具体证据 |
| D-002 | dialogue | ChatGPT 对话 | ⚠️ 缺具体证据 |
| D-003 | dialogue | ChatGPT 对话 | ⚠️ 缺具体证据 |
| D-004 | dialogue | ChatGPT 对话 | ⚠️ 缺具体证据 |
| D-005 | dialogue | ChatGPT 对话 | ⚠️ 缺具体证据 |
| D-006 | dialogue | ChatGPT 对话 | ⚠️ 缺具体证据 |
| D-007 | dialogue | ChatGPT 对话 | ⚠️ 缺具体证据 |
| D-008 | dialogue | ChatGPT 对话 | ⚠️ 缺具体证据 |
| D-009 | dialogue | ChatGPT 对话 | ⚠️ 缺具体证据 |
| D-010a | implementation | 代码实现 | ✅ 有 |
| D-011 | implementation | 代码实现 | ✅ 有 |
| D-010b | test | Handoff Test | ✅ 有 |

**结论：** 需要补充来源证据

---

## 8. 编号修复建议

### 编号映射表

```
旧编号 → 新编号 → 决策标题 → 处理方式
D-001 → D-001 → 产品名暂定 Framing Ledger / FLG → superseded (被 D-008 取代)
D-002 → D-002 → 服务对象确定为策略、营销、运营、解决方案工作者 → keep
D-003 → D-003 → v0.1 优先服务提案/方案型项目 → keep
D-004 → D-004 → 采用本地文件夹 + CLI + Markdown 协议 → keep
D-005 → D-005 → 项目目录是最高优先级事实源 → keep
D-006 → D-006 → 写入策略采用 patch-first → keep
D-007 → D-007 → v0.1 必须新增 Legacy Audit 模块 → superseded (被 D-009 取代)
D-008 → D-008 → 产品名从 OMP 调整为 Framing Ledger / FLG → keep
D-009 → D-009 → v0.1 Core 聚焦 init/frame/closeout，Legacy Audit 拆到 v0.1.5 → keep
D-010a → N/A → v0.1 Core 使用 Typer 作为 CLI 框架 → downgrade_to_implementation_note
D-011 → D-011 → v0.1 Core 使用关键词提取而非 LLM → keep
D-010b → D-010 → Agent 启动时必须读取 pending patches → renumber

新增:
D-012 → 不追求技术精度，追求认知事件级精度 → add_missing
D-013 → 改造现有结构而非新建目录 → add_missing
D-014 → 先做再改 → add_missing
D-015 → Harness Engineering 不是 Scaffolding → needs_human_review
```

---

## 9. 决策分类建议

### Project Decision（产品定位/目标/范围）

| 新编号 | 决策标题 | 状态 |
|--------|---------|------|
| D-001 | 产品名暂定 Framing Ledger / FLG | superseded |
| D-002 | 服务对象确定为策略、营销、运营、解决方案工作者 | accepted |
| D-003 | v0.1 优先服务提案/方案型项目 | accepted |
| D-008 | 产品名从 OMP 调整为 Framing Ledger / FLG | accepted |
| D-012 | 不追求技术精度，追求认知事件级精度 | pending |
| D-015 | Harness Engineering 不是 Scaffolding | needs_review |

### Architecture Decision（架构/协议/状态层）

| 新编号 | 决策标题 | 状态 |
|--------|---------|------|
| D-004 | 采用本地文件夹 + CLI + Markdown 协议 | accepted |
| D-005 | 项目目录是最高优先级事实源 | accepted |
| D-006 | 写入策略采用 patch-first | accepted |
| D-009 | v0.1 Core 聚焦 init/frame/closeout，Legacy Audit 拆到 v0.1.5 | accepted |
| D-010 | Agent 启动时必须读取 pending patches | accepted |
| D-013 | 改造现有结构而非新建目录 | pending |

### Workflow Decision（工作方式/开发模式）

| 新编号 | 决策标题 | 状态 |
|--------|---------|------|
| D-014 | 先做再改 | pending |

### Implementation Decision（技术实现）

| 决策标题 | 处理方式 |
|---------|---------|
| v0.1 Core 使用 Typer 作为 CLI 框架 | 降级为 implementation note |
| v0.1 Core 使用关键词提取而非 LLM | 保留在 DECISIONS.md（影响产品方向） |

---

## 10. 正式决策与候选决策的边界

**正式决策（DECISIONS.md）：**
- 影响产品方向
- 影响架构设计
- 影响工作方式
- 有完整推导过程
- 有来源证据

**候选决策（.flg/patches/）：**
- 由 closeout 提取
- 由 extract-decisions 提取
- 状态为 pending_review
- 需要人工确认

**当前问题：**
- 当前 DECISIONS.md 中的决策是 AI 手动整理的，不是通过标准流程生成的
- 需要补充来源证据

---

## 11. 是否建议现在 merge

**建议：** ⚠️ 部分 merge

**建议立即 merge：**
- D-001 标记为 superseded
- D-007 标记为 superseded
- D-010a 降级为 implementation note

**建议人工确认后 merge：**
- D-012（不追求技术精度，追求认知事件级精度）
- D-013（改造现有结构而非新建目录）
- D-014（先做再改）
- D-015（Harness Engineering 不是 Scaffolding）

---

## 12. 人工确认清单

| 项目 | 需要确认 |
|------|---------|
| D-001 是否标记为 superseded | ✅ 是 |
| D-007 是否标记为 superseded | ✅ 是 |
| D-010a 是否降级为 implementation note | ✅ 是 |
| D-012 是否补充到 DECISIONS.md | ✅ 是 |
| D-013 是否补充到 DECISIONS.md | ✅ 是 |
| D-014 是否补充到 DECISIONS.md | ✅ 是 |
| D-015 是否补充到 DECISIONS.md | ✅ 是（需要确认是否与 FLG 相关） |
| 是否为每条决策补充来源证据 | ✅ 是 |

---

## 13. 审计结论

**当前 DECISIONS.md 状态：** 中等质量，可以改进

**关键发现：**
1. 决策内容基本准确
2. 推导过程完整
3. 但存在重复、矛盾、遗漏、层级混乱
4. 缺少来源证据
5. 不是通过标准流程生成

**FLG 当前是否解决了决策日志治理？**

**部分解决：**
- ✅ 有地方记录决策（DECISIONS.md）
- ✅ 有机制提取候选决策（closeout/extract-decisions）
- ✅ 有机制合并决策（merge）
- ⚠️ 但当前决策是 AI 手动整理的，不是工具自动生成的
- ⚠️ 关键词提取机制还很粗糙

**缺的下一步能力：**
1. LLM 集成，提升提取精度
2. 来源证据自动记录
3. 决策状态自动管理
4. 冲突检测

---

*对账完成时间：2026-06-25*
*待人工确认*
