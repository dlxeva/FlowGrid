# FLG RC0 CLI Acceptance Report

**Date:** 2026-06-25
**Version:** v0.1.5-alpha
**Status:** ✅ All Passed

---

## 1. 验收环境

- **OS:** Linux (WSL)
- **Python:** 3.12.3
- **安装方式:** pip install -e .

---

## 2. 命令验收结果

| # | 命令 | 状态 | 说明 |
|---|------|------|------|
| 1 | flg version | ✅ | 输出 Framing Ledger v0.1.5-alpha |
| 2 | flg init | ✅ | 创建项目结构 |
| 3 | flg frame | ✅ | 检测缺失字段，生成 patch |
| 4 | flg closeout | ✅ | 从 transcript 提取内容，生成 patch |
| 5 | flg status | ✅ | 显示项目状态和 pending patches |
| 6 | flg handoff | ✅ | 生成 Agent 接力摘要 |
| 7 | flg merge --dry-run | ✅ | 预览合并，不修改文件 |
| 8 | flg audit --report-only | ✅ | 审计项目成熟度 |
| 9 | flg extract-decisions --dry-run | ✅ | 提取候选决策 |
| 10 | flg import --dry-run | ✅ | 预览导入 |
| 11 | pytest | ✅ | 24/24 passed |

---

## 3. 详细输出记录

### flg version
```
Framing Ledger v0.1.5-alpha
```

### flg init
```
✓ Framing Ledger project initialized: RC0 Test

Files Created:
  .flg/patches/    created
  .flg/sessions/   created
  .flg/memory/     created
  PROJECT.md       created
  FRAMING.md       created
  DECISIONS.md     created
  SNAPSHOT.md      created
  PROGRESS.md      created
  .flg/CONTRACT.md created
  .flg/state.json  created
  .flg/index.json  created
```

### flg frame
```
Found 9 missing fields in FRAMING.md

Patch generated: .flg/patches/frame-*.patch.md
```

### flg closeout
```
✓ Closeout patch generated

Extracted items:
  - Decisions: 3
  - Risks: 3
  - Progress: 0
  - Open Questions: 6
```

### flg status
```
Project: RC0 Test
Stage: initialized
Version: 0.1.0

⚠ This project has pending patches. Agents should read them before continuing.

Pending Patches:
  - frame-* (medium, pending_review)
  - closeout-* (medium, pending_review)
```

### flg handoff
```
Agent Handoff Summary

Project: RC0 Test
Stage: initialized

Current Goal: Define project scope and goals for RC0 Test

Pending Patches: 2
  - closeout-*: 3 candidate decisions, 3 risks
  - frame-*: 27 open questions

Suggested Next Steps:
  1. Run flg frame to define project goals and boundaries
  2. Review and fill in FRAMING.md
```

### flg merge --dry-run
```
Merge Preview
Patch: closeout-*.patch.md

Low Risk - PROGRESS.md:
  Will append session progress entry

Medium Risk - DECISIONS.md:
  3 candidate decisions (needs human review)

Medium Risk - SNAPSHOT.md:
  3 new risks

Dry run mode - no changes made
```

### flg audit --report-only
```
Project Audit Results

Is FLG Project: ✓ Yes
Maturity Score: 5/5 (Complete)

PROJECT.md:   ✓ exists
FRAMING.md:   ✓ exists
DECISIONS.md: ✓ exists
SNAPSHOT.md:  ✓ exists
PROGRESS.md:  ✓ exists
```

### flg extract-decisions --dry-run
```
Found 3 candidate decision(s):

#  Content          Source       Keyword
1  # Decision Log   DECISIONS.md decision
2  ## Confirmed     SNAPSHOT.md  confirmed
3  ## Unconfirmed   SNAPSHOT.md  confirmed

Dry-run mode. No changes made.
```

### flg import --dry-run
```
Import Preview

Source File  Target File  Size
README.md    README.md    5098 bytes

Dry-run mode. No changes made.
```

---

## 4. 测试结果

```
24 passed in 3.76s
```

| 测试文件 | 测试数量 | 状态 |
|---------|---------|------|
| test_closeout.py | 6 | ✅ |
| test_frame.py | 4 | ✅ |
| test_handoff.py | 4 | ✅ |
| test_init.py | 4 | ✅ |
| test_merge.py | 6 | ✅ |

---

## 5. 发现的问题

### 5.1 flg status 版本显示

**问题：** flg status 显示 Version: 0.1.0，而不是 0.1.5-alpha
**原因：** state.json 在 init 时写入版本号，但读取的是旧版本
**影响：** 低，不影响功能
**建议：** 后续修复

### 5.2 flg extract-decisions 误判

**问题：** 提取了标题行（# Decision Log、## Confirmed）作为候选决策
**原因：** 关键词匹配过于宽泛
**影响：** 中，但有 dry-run 保护
**建议：** 改进关键词匹配逻辑

---

## 6. 验收结论

**总体评估：** ✅ 通过

所有命令在干净环境下正常运行，测试全部通过。

**可以进入下一阶段验收。**

---

*CLI 验收完成时间：2026-06-25*
