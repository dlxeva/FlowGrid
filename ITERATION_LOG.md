# FlowGrid (FLG) — 迭代日志

> 记录实际使用中暴露的问题。原则：先记录，不急改，边用边优化。
> 同一问题被多次验证或痛点累积后再动手改，避免过早迭代引入噪音。
> 格式：每次使用后追加一节，标注日期、场景、发现的问题、状态。
> 权威入口：本文件是 FlowGrid 产品迭代事实源。Vault 中的同名文件保留为历史来源档案，不再作为并行写入口。
> 新记录使用日期型稳定 ID（如 `FLG-ITER-20260808-01`），不再依赖会冲突的连续“发现 N”编号。

## 状态约定

- `observed`：观察到，待更多验证
- `confirmed`：多次验证，已确认是真问题，待改
- `fixing`：正在改
- `fixed`：已改（标注 commit / PR）
- `wontfix`：评估后决定不改（写明理由）

---

## 2026-08-17：真实 Windows 兼容性报告回灌

### FLG-ITER-20260817-01：GBK 首次初始化、MSYS 路径和 Windows 测试链暴露兼容性缺口 [fixing — P0]

**场景**：一位外部测试者在 Windows 11、PowerShell 5.1 代码页 936、PortableGit Git Bash 和 Python 3.13.14 上，按项目提供的测试任务运行合并提交 `4cd893b`。测试使用真实营销讨论作为 raw session，原始报告和私有素材不进入公开仓库。

**观察**：`flg version`、smoke、`C:\` 和 `C:/` session 路径通过；pytest 为 `7 failed, 221 passed`。中文和空格目录已经完成文件写入，但 `init` 打印字面量 checkmark 时触发 GBK `UnicodeEncodeError`。Git Bash `/c/...` 目标没有经过已有路径归一化，被创建到 `C:\c\...`。

**逐项复核**：7 个 pytest failure 中，路径显示、`PYTHONPATH` 分隔符、manifest 路径和 Rich 表格宽度属于测试可移植性问题；`current-state` 分类器把 Windows `Path` 字符串与 Git 的 POSIX 路径直接比较，属于真实脚本兼容性缺陷。不能把 7 项统一归为测试错误。

**本地候选方向**：首次初始化成功标记改为 GBK 可编码 ASCII；`init --dir` 接入 `normalize_user_path`；修复跨平台断言和 current-state 路径分类；增加 Windows Python 3.12 CI。`doctor` 缺少 repo-map 当前只显示信息，不单独导致 strict 失败，本轮不改变这一产品语义。

**本地候选验证**：Windows 定向回归 `10 passed`，全量 `231 passed`，强制 repository source-tree smoke、current-state freshness、workflow YAML 解析与 `git diff --check` 均通过。Windows CI 已加入候选，尚未通过远端 runner 执行。

**首次 Windows CI**：`fef01e0` 的 Windows Python 3.12 job 为 `38 failed, 193 passed`。日志逐项显示其中 37 项来自测试和 fixture 的无编码 `pathlib` I/O 在 Windows 默认落到 `cp1252`，另 1 项来自 Rich 表格对 `pending_review` 的平台相关截断。后续候选把 UTF-8 明确为 Windows 测试进程契约，在 job 设置 `PYTHONUTF8=1`，并将 status 回归改为验证 pending warning 语义。

**第二次 Windows CI**：UTF-8 修复将结果收敛到 `1 failed, 230 passed`。残余失败揭示 BIZ 批量导入在 Windows 同一时钟刻度内生成相同 capture ID，后一条覆盖前一条。候选保留原有 ID 形态，改用独立 UUID 后缀，并增加冻结时钟下的唯一性回归。

**边界**：本地与 GitHub CI 不能替代原 Windows 主机复测。候选通过后仍只能说明代码与回归闭环完成，现场修复状态保持待验证。

## 2026-08-16：中文 owner 范围收拢与外部 Windows 案例收口

### FLG-ITER-20260816-01：中文 owner 范围收拢在短句与长口述中重复漏提取 [confirmed — P0]

**场景**：2026-08-11，FlightModeAI owner 用长段中文口述把产品收拢为飞行学习包，说明飞行前选主题、飞行中完成、落地后分享的闭环，也指出端侧模型体验与互动方式仍待验证。`closeout` 只触发 lessons，正式候选为 0。2026-08-16，owner 又用一句“我们主要做 Canvas Prompt FlowGrid 其他我觉得意义不大”收拢资源范围，`closeout` 再次返回空候选。

**发现**：两次样本长度不同，暴露的是同一缺陷。中文 owner 通过“收拢、定义为、主要做、其他意义不大”等自然口语表达范围取舍时，现有入口和提取器不能稳定保存来源明确的候选。[confirmed]

**影响**：安全 review gate 阻止了错误自动写入，但 owner 已经明确的范围可能静默丢失。宿主随后只能人工使用 `decision add` 或 confirmed capture 补账，正式决策还可能夹带无证据的模板字段。

**处理方向**：一句带明确 owner 来源的短判断走 source-backed capture 草稿；会议、长讨论和包含范围、闭环、体验证据、待验证问题的口述走 `closeout`。长口述只有在保留 `User:` 归因、范围收拢信号和流程信号时生成 pending candidate；普通项目名列表 abstain。正式决策只写真实存在的字段，继续保留 review 与来源门。

**本地候选验证**：新增 8 月 11 日真实长口述 fixture、8 月 16 日短 capture 回归和无来源实体列表反例。外部 Windows + WorkBuddy 案例另建隐私安全的冷启动输入预检，普通项目文件提供 1/6 个连续性不变量，FlowGrid Context Pack 提供 6/6；该结果只度量输入信息，不证明 Agent 输出更好、用户满意或跨会话增益。

---

## 2026-08-08：主线优化审计与合并收口

**场景**：项目主编排同时核对映射 runtime、Vault 治理层、遗留开发 worktree、`flg status`、`flg capture list`、`doctor --strict` 和全量测试。

**收口证据**：PR #42 已合并到 `master`，merge commit 为 `73902fc`；合并后全量测试为 `189 passed`。以下 01–05 均依据该合并与测试证据收口为 `fixed`。

### FLG-ITER-20260808-01：三份迭代日志已形成并行事实源 [fixed — P0]

**现象**：映射 runtime 的日志只有 137 行并带 8 月 6 日未提交记录；Vault 同名日志有 1777 行并记录到 8 月 4 日；遗留 `agent/english-ledger-closeout` 分支又包含一组 7 月 17—18 日记录。三份文件出现重复编号和不同状态。

**影响**：不同 Agent 会从不同工作目录得到不同的产品优先级；同一缺陷可能在一份日志中仍是 `observed`，在另一份日志中已经跨项目复现为 `confirmed`。

**处理方向**：代码仓本文件成为唯一产品迭代事实源；Vault 文件只保留为历史来源档案或生成镜像；迁移时保留来源路径、原日期和原状态，不删除历史文件。规则见 `docs/product/iteration-log-governance.md`。

**修复**：PR #42 将代码仓日志和治理规则合并到 `master`（`73902fc`）；Vault 同名文件保持历史档案边界。

### FLG-ITER-20260808-02：短确认与用户方向归因已跨项目重复 [fixed — P0]

**现象**：五个相互独立的产品、恢复和市场验证项目均出现“Assistant 展开方案 + User 回复同意/可以/没问题”后 closeout 漏掉真实方向，或只生成 Assistant shell candidate。历史来源 `vault@2026-07-22#96`、`vault@2026-07-31#100`、`vault@2026-08-01#105`、`vault@2026-08-04#110` 与本轮会话属于同一模式。

**影响**：安全门阻止了错误写入，但重要方向仍依赖宿主人工补账；只依赖 closeout 的宿主会静默丢失用户已经确认的决策。

**处理方向**：只在前文存在单一明确方案时，将短确认绑定为带 `source_actor=user`、确认原文和方案范围的 candidate；多方案或歧义上下文 abstain；candidate 仍须经过 review，不得自动写正式账本。

**修复验证**：PR #42 已合并合成回归与真实 PBL Markdown 会话回放；原始确认、`source_actor=user` 和带 inline code 的确认范围均保留。

### FLG-ITER-20260808-03：Project identity 通过不代表映射 runtime 可复现 [fixed — P0]

**现象**：repo-map 的 ledger root、code repo 和 HEAD commit 均匹配时，映射 runtime 即使存在未提交代码，`doctor --strict` 仍显示 `Project identity OK`。

**影响**：主编排无法区分远端可复现基线与本地候选行为，测试和账本维护可能实际运行在未记录的代码上。

**处理方向**：runtime attestation 同时报告 branch、HEAD 和 dirty state；没有 repo-map 的普通项目保持兼容；strict 行为必须显式、可测试。

**修复验证**：PR #42 已合并 runtime branch、HEAD 与 dirty state 报告；branch/HEAD 漂移使 strict 失败，dirty 当前只告警。

### FLG-ITER-20260808-04：status 未显示 pending captures [fixed — P1]

**现象**：`flg status` 显示没有待审 patch，但同一项目的 `flg capture list` 有 4 个 `pending_review` capture。

**影响**：自然语言宿主和接手 Agent 容易把“没有 patch”误读成“没有待审判断”。

**处理方向**：status 独立汇总 pending captures，不把 capture 和 patch 合并成同一种生命周期。

**修复验证**：PR #42 已合并 pending captures 独立汇总，真实治理根可同时显示“无 pending patch”和“4 pending captures”。

### FLG-ITER-20260808-05：init 创建路径在窄终端被截断 [fixed — P2]

**现象**：全量测试在默认窄终端下为 `174 passed, 1 failed`；失败用例显示 `Created in:` 的长路径被 Rich 截断。将终端宽度扩大后用例通过。

**影响**：用户在最需要确认项目落点的首次初始化阶段，可能看不到完整目录。

**处理方向**：路径输出使用不截断的 plain/overflow-safe 渲染，并保留窄终端回归测试。

**修复验证**：PR #42 已合并 30 列终端宽度回归；合并后全量测试为 `189 passed`。

### FLG-ITER-20260808-06：Context Pack 的近期状态与长期叙事需要分层召回 [partially fixed — P1]

**现象**：历史评估已经证明 Context Pack 对短而干净的原始历史并不占优；另有真实任务分别出现旧 Next Actions 继续进入 resume pack，以及早期产品母叙事未被默认 pack 召回。来源簇：`vault@2026-07-22#90`、`vault@2026-08-01#104`、`vault@2026-08-04#112`。

**影响**：无差别扩大默认上下文会破坏压缩价值，只保留最近状态又可能让品牌、叙事和长期策略任务缺少关键历史。

**处理方向**：保持默认 resume pack 有界；后续以显式任务意图或主题查询实验“近期执行状态 + 长期母叙事”分层召回，并把 stale/superseded 检查放在增加更多内容之前。

**当前状态**：Continuity Manifest v1 已实现“紧凑地图 → 按判断 ID 展开”的第一段纵切，复用正式账本与现有 evidence/trace 入口，保持 resume 兼容。长期母叙事的主题召回仍未实现，因此本条只标记为 partially fixed。

### FLG-ITER-20260808-07：长期判断账本与任务执行层仍靠宿主纪律交接 [observed — P1]

**现象**：多个任务级沙盒和实时控制实验表明，FLG 能提供长期边界，执行层能提供 scope、验收和当前任务状态，但二者之间尚无最小、可审计的交接字段。pending captures 对 status 不可见是这一问题的一个具体表现。来源簇：`vault@2026-07-27#97-99`、`vault@2026-08-01#102`。

**影响**：宿主漏读长期边界或漏回写重要执行证据时，项目状态与实际推进会分叉。

**处理方向**：先固定最小交接字段（decision/evidence 引用、task id、scope、validation、completion evidence），不把任务调度并入 FLG Core；跨项目重复后再考虑机器校验。

### FLG-ITER-20260808-08：阶段、锚点和旧 patch 的生命周期仍不完整 [confirmed — P1]

**现象**：已修复的 rejected/superseded 过滤不能覆盖全部生命周期问题。真实项目仍出现 framing 完整后阶段停留在 initialized、多版本锚点缺少 current/freshness 入口，以及目标文件已经补齐但旧 frame patch 仍需人工 supersede。来源簇：`dev-worktree@2026-07-18#14-15`、`vault@2026-07-31#101`、`vault@2026-08-04#111`。

**影响**：结构健康的项目仍可能暴露过期阶段、锚点或待办，接手 Agent 需要从多个文件人工推断当前状态。

**处理方向**：分别设计 stage 变更、锚点 freshness 和同源旧 patch 收口，不以一个新的总状态机同时解决；本轮先保留为下一阶段 backlog。

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
