# FlowGrid (FLG) — 迭代日志

> 记录实际使用中暴露的问题。原则：先记录，不急改，边用边优化。
> 同一问题被多次验证或痛点累积后再动手改，避免过早迭代引入噪音。
> 格式：每次使用后追加一节，标注日期、场景、发现的问题、状态。

## 状态约定

- `observed`：观察到，待更多验证
- `confirmed`：多次验证，已确认是真问题，待改
- `fixing`：正在改
- `fixed`：已改（标注 commit / PR）
- `wontfix`：评估后决定不改（写明理由）

---

## 2026-07-22：公开表面审计——仓库扫描遗漏 GitHub 元数据与生成工件 [fixed]

**场景**：产品开始对外推广后，对公共仓库、GitHub Issues、PR 描述和可达 Git 历史做了一次隐私审计。

### 发现 12：仅扫描 Git 跟踪文件不足以覆盖公共暴露面 [confirmed]

**现象**：源码树没有凭据，但公开 Issue/PR 正文仍保留 dogfood 项目名称，本地性能证明工件还包含绝对路径。它们都可被公开搜索，却不在普通工作树扫描范围内。

**根因**：开源边界审计只把 Git 跟踪文件当作公开表面，没有把 GitHub 元数据和生成报告的运行环境字段纳入固定检查。

**修复**：脱敏公开 Issue/PR 正文；将性能工件中的绝对路径替换为 `<repo>`、`<python>` 和 `<temp>` 占位符；更新审计报告中的历史样例。保留问题机制、性能结论和验证数据。

**后续约束**：发布前审计应同时检查 tracked files、Issue/PR body、评论、可达 Git 历史和生成工件；本机路径不得进入公共证据文件。

---

## 2026-07-15：客户项目（三轮）—— 会前假设全部错误，flg 未拦截

**场景**：7/15 客户会议录音揭示，会前所有 flg ledger 内容（FRAMING/MISSION_BRIEF/方案）基于错误事实。flg 全程绿灯（frame 通过、audit 5/5），但没有拦截住"基于二手信息构建了完整框架"这个系统性风险。

**使用路径**：会前基于转述+公开调研构建完整 ledger → flg frame/audit 全绿 → 会议录音推翻核心假设 → biz-retro 分析暴露问题。

### 发现 8：flg 没有"信息来源可信度"校验机制 [confirmed]

**现象**：会前 FRAMING.md 里的所有字段都填了，flg frame 报 10/10 通过，audit 报 5/5。但所有内容的来源是：项目负责人转述（二手）+ 公开 web 调研（三手）。没有任何一手信息（没见过客户亲口讲、没见过一线工作流、没见过真实样本）。

**根因**：flg 的 frame/audit 只校验"字段填没填"和"文件在不在"，不校验"内容来源是几手信息"。一个完全基于猜测填满的 FRAMING.md 能拿满分。

**影响**：会前所有准备建立在错误假设上（客户缺 OCR → 实际客户自己已验证 OCR 可行）。浪费了方案框架、说服弹药等物料。

**建议改法**（优先级：高）：
- FRAMING.md 模板增加 "Evidence Tier" 字段或标记机制
- frame 命令在检测到所有字段都是 Tier 3（公开/推测）时，输出警告："This framing is built on secondary/tertiary evidence only. Recommend reality capture before commitment."
- audit 命令增加"evidence sufficiency"维度，不只看文件完整性

### 发现 9（重建）：frame 字段标题层级不一致 [confirmed，历史遗留]

（同 7/13 首次发现，状态不变。8 个字段匹配 H2，2 个匹配 H3，无文档说明。）

### 发现 10（重建）：过时 patch 无官方清理机制 [confirmed，历史遗留]

（同 7/13 首次发现。patch 生命周期缺 supersede/discard 路径。）

### 发现 11（重建）：flg 缺项目素材管理机制 [confirmed，历史遗留]

（同 7/13 二轮发现。无 docs/ 约定，扁平结构在素材增多后不可维护。注：flg 仓库本身在 7/14 已迁到 docs/ 结构，但用户项目侧的约定仍需明确。）

---

## 2026-07-13：客户 AI 助手项目立项（首次实战）

### 发现 1：frame 字段标题层级不一致，无文档说明 [confirmed]

REQUIRED_FIELDS 里 8 个字段匹配 H2，2 个（Explicit Requirements / Real Needs Hypothesis）匹配 H3。无文档说明。每个新用户都踩坑。

### 发现 2：过时 patch 没有官方清理机制 [confirmed]

patch 生命周期只有 pending_review → merged，缺 supersede/discard。需手改 state.json。

### 发现 3：decision add 生成的格式与手写决策割裂 [observed]

D-001/002 手写简洁，D-003+ 是 add 生成的重型结构。

### 发现 4：status 把 superseded 的 patch 也列在 pending [observed]

与发现 2 相关。

### 发现 5：frame 验证缺少渐进式进度感 [observed]

体验问题。

### 发现 6：flg 没有项目素材管理机制 [confirmed]

无 docs/ 约定。

### 发现 7：核心文件 vs 用户扩展文件边界不清 [observed]

与发现 6 相关。

---

## 迭代节奏

不急着改。等以下信号再动手：
- 同一问题在 2-3 个不同项目重复出现 → 升级为 confirmed 并开改
- 单次场景但痛点极高 → 直接改
- 观察满 1 个月仍只出现一次 → 标 wontfix 或降级

每次实战使用后，追加一节到本文件顶部（新场景在上）。
