# FLG Decision Log Generation Audit

**Date:** 2026-06-25
**Version:** v0.1.5-alpha / RC0
**Auditor:** Hermes

---

## 1. 审计目标

验证 Framing Ledger 的决策日志生成机制是否符合以下原则：
- 正式决策不能被 closeout 或 extract-decisions 直接污染
- 候选决策必须经过人工确认或 flg merge 才能进入 DECISIONS.md
- 决策分层必须清晰（正式 / 候选 / 历史）

---

## 2. 决策分层架构

### 第一层：正式决策日志（DECISIONS.md）

**含义：**
- 已确认项目事实
- 已经过人工确认或 flg merge 合并
- Agent 启动时视为正式项目事实

**当前状态：** ✅ 正确
- DECISIONS.md 只包含人工确认的决策
- 没有自动写入路径

### 第二层：候选决策 patch（.flg/patches/*.patch.md）

**含义：**
- 由 flg closeout 从 transcript 提取
- 或由 flg frame / flg audit / flg import 生成
- 状态为 pending_review
- 不等于正式决策

**当前状态：** ✅ 正确
- closeout 只生成候选决策
- 候选决策标记为 pending_review
- 不直接写入 DECISIONS.md

### 第三层：历史候选决策报告（FLG_CANDIDATE_DECISIONS.md）

**含义：**
- 从历史项目文件提取的候选决策
- 只能作为迁移建议
- 不能直接写入 DECISIONS.md

**当前状态：** ✅ 正确
- extract-decisions 默认 dry-run
- 只输出报告，不写入

---

## 3. 命令审计

### 3.1 flg closeout

**规则检查：**

| 规则 | 状态 | 说明 |
|------|------|------|
| 只能生成候选决策 | ✅ | 输出到 patch，不直接写入 |
| 候选决策进入 .flg/patches/ | ✅ | 正确 |
| 不得直接写入 DECISIONS.md | ✅ | 没有写入逻辑 |
| 标记 status: pending_review | ✅ | 正确 |
| 包含来源 transcript 路径 | ✅ | source_transcript 字段 |
| 包含证据摘录 | ✅ | Evidence Excerpts section |
| 标记 needs_human_review | ✅ | Needs Human Review section |

**结论：** ✅ 符合要求

### 3.2 flg extract-decisions

**规则检查：**

| 规则 | 状态 | 说明 |
|------|------|------|
| 默认 dry-run | ✅ | --dry-run 默认开启 |
| 只输出候选决策报告 | ✅ | 只打印到终端 |
| 不得直接写入 DECISIONS.md | ✅ | 没有写入逻辑 |
| 包含来源文件路径 | ✅ | Source 列 |
| 包含证据摘录 | ⚠️ | 只显示行内容，不是完整证据 |
| 包含可信度 | ❌ | 缺少 confidence 字段 |
| 包含是否需要人工确认 | ⚠️ | 隐含（所有都需要） |

**发现问题：**
1. 缺少 confidence 字段
2. 证据摘录不够完整

**建议修复：** 添加 confidence 字段到输出表格

### 3.3 flg merge

**规则检查：**

| 规则 | 状态 | 说明 |
|------|------|------|
| 只合并用户指定 patch | ✅ | --patch 参数 |
| dry-run 不得修改文件 | ✅ | 正确 |
| high-risk 决策不得自动合并 | ✅ | 标记需人工确认 |
| 涉及目标/边界/策略必须人工确认 | ✅ | 高风险标记 |
| merge 后生成 merge log | ✅ | .flg/merge_logs/ |
| merge 后更新 patch status | ✅ | pending_review → merged |
| merge 后更新 state.json | ✅ | 正确 |
| 合并失败不留下半写入状态 | ⚠️ | 未验证异常情况 |

**发现问题：**
1. 需要验证异常情况下的状态一致性

**结论：** 基本符合要求，需要加强异常处理

---

## 4. 正式决策结构审计

**当前 DECISIONS.md 字段：**

| 字段 | 状态 | 说明 |
|------|------|------|
| 决策标题 | ✅ | D-xxx 格式 |
| 决策时间 | ✅ | YYYY-MM-DD |
| 决策状态 | ❌ | 缺少 accepted/superseded/rejected |
| 决策内容 | ✅ | 有 |
| 决策背景 | ✅ | 有 |
| 决策依据 | ✅ | 有 |
| 影响范围 | ✅ | 有 |
| 取代了什么旧判断 | ⚠️ | 部分有 |
| 可推翻条件 | ⚠️ | 部分有 |
| 来源 | ❌ | 缺少 source_type/source_path/patch_id |

**发现问题：**
1. 缺少决策状态字段（accepted/superseded/rejected）
2. 缺少来源字段（source_type/source_path/patch_id/evidence）

**建议修复：** 生成 normalization patch，为现有决策添加缺失字段

---

## 5. 候选决策结构审计

**当前 closeout patch 中的候选决策字段：**

| 字段 | 状态 | 说明 |
|------|------|------|
| 候选决策标题 | ⚠️ | 只有编号，没有标题 |
| status: pending_review | ✅ | 在 patch header 中 |
| confidence | ❌ | 缺少 |
| needs_human_review | ✅ | Needs Human Review section |
| source_type | ⚠️ | 只有 source_command |
| source_path | ✅ | source_transcript |
| evidence | ✅ | Evidence Excerpts section |
| 候选决策内容 | ✅ | 有 |
| 判断依据 | ⚠️ | 只有关键词匹配 |
| 建议写入位置 | ❌ | 缺少 |
| 风险等级 | ⚠️ | 只有 patch 级别 |
| 是否可能取代旧判断 | ❌ | 缺少 |

**发现问题：**
1. 缺少 confidence 字段
2. 缺少建议写入位置
3. 缺少是否可能取代旧判断

---

## 6. 决策提取质量审计

### 6.1 误判风险

**检查项：**
- 是否把普通讨论误判成决策？
- **风险：** 中等
- 关键词匹配可能把"我们应该..."误判为决策

**缓解措施：**
- 标记为 pending_review
- 需要人工确认

### 6.2 遗漏风险

**检查项：**
- 是否漏掉明显决策？
- **风险：** 中等
- 隐含决策可能被遗漏（如"按这个方案走"没有关键词）

**缓解措施：**
- 添加更多关键词
- 后续集成 LLM

### 6.3 区分能力

**检查项：**
- 是否区分"想法/假设/决策"？
- **当前状态：** ❌ 无法区分
- 关键词匹配无法理解上下文

**缓解措施：**
- 人工确认
- 后续集成 LLM

### 6.4 自动污染风险

**检查项：**
- 是否存在自动污染 DECISIONS.md 的路径？
- **当前状态：** ✅ 不存在
- closeout 和 extract-decisions 都不直接写入

---

## 7. 当前风险评估

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| 候选决策误判 | 中 | 关键词匹配可能误判 | 人工确认 |
| 候选决策遗漏 | 中 | 隐含决策可能被遗漏 | 添加关键词/LLM |
| 正式决策缺字段 | 低 | 缺少状态和来源 | normalization patch |
| 候选决策缺字段 | 低 | 缺少 confidence | 添加字段 |
| merge 异常处理 | 低 | 未验证异常情况 | 加强测试 |

---

## 8. 修复建议

### 8.1 立即修复（RC0 之前）

1. ✅ 确认 closeout 不直接写入 DECISIONS.md
2. ✅ 确认 extract-decisions 不直接写入 DECISIONS.md
3. ⚠️ 为 extract-decisions 添加 confidence 字段
4. ⚠️ 为候选决策添加建议写入位置

### 8.2 后续修复（v0.2）

1. 为正式决策添加状态字段
2. 为正式决策添加来源字段
3. 集成 LLM 提升提取精度
4. 添加异常处理测试

---

## 9. 审计结论

**总体评估：** ✅ 符合 RC0 要求

**关键发现：**
1. 决策分层架构正确
2. closeout 和 extract-decisions 不会直接污染 DECISIONS.md
3. 候选决策必须经过人工确认或 merge
4. 存在一些字段缺失，但不影响核心安全性

**建议：**
1. 可以进入 RC0 阶段
2. 后续版本补充缺失字段
3. 后续版本集成 LLM 提升精度

---

*审计完成时间：2026-06-25*
