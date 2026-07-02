# FLG v0.1.5 Legacy Audit Report

**Date:** 2026-06-25
**Goal:** v0.1.5 Legacy Audit
**Status:** ✅ Complete

---

## 1. 本轮目标

实现历史项目审计的 dry-run 版本。

## 2. 实现内容

### 新增命令

| 命令 | 状态 | 说明 |
|------|------|------|
| `flg audit --report-only` | ✅ | 审计项目目录，输出成熟度评分 |
| `flg extract-decisions --dry-run` | ✅ | 提取候选决策 |
| `flg import --dry-run` | ✅ | 预览导入 |

### 功能详情

**flg audit:**
- 检查是否为 FLG 项目
- 检查核心文件是否存在
- 计算成熟度评分（0-5）
- 识别中文文件名
- 生成建议

**flg extract-decisions:**
- 扫描项目文件
- 识别决策关键词（中英文）
- 输出候选决策表格
- 不写入 DECISIONS.md

**flg import:**
- 扫描源目录
- 映射文件名（支持中文→英文）
- 预览导入
- 支持 dry-run 模式

## 3. 测试结果

```
24 passed in 3.33s
```

## 4. 已知限制

1. `flg audit` 暂不扫描子目录
2. `flg extract-decisions` 关键词匹配较简单
3. `flg import` 暂不支持增量导入

## 5. 下一步建议

所有 Goal 1-4 已完成。建议：
1. 用户测试完整工作流
2. 收集反馈
3. 考虑 v0.2 功能

---

*v0.1.5 Legacy Audit 完成时间：2026-06-25*
