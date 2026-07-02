# FLG Release Engineering Cleanup Report

**Date:** 2026-06-25
**Scope:** Goal 1 - Release Engineering Cleanup
**Status:** Complete

## 1. 本轮目标

让 `framing-ledger/` 成为一个可安装、可测试、可作为独立小型 Python CLI 仓库维护的代码目录。

## 2. 修改文件

- `.gitignore`
- `scripts/smoke_test.py`
- `README.md`
- `IMPLEMENTATION_REPORT.md`
- `src/flg/core/files.py`
- `tests/test_init.py`

## 3. git 仓库边界处理结果

- 已在 `framing-ledger/` 子目录内执行 `git init`
- 顶层 `Projects/Oh-My-Project/` 继续保持非 git 仓库
- 新增 `.gitignore`，屏蔽虚拟环境、缓存、构建产物和临时 FLG patch/merge log
- 修复 `is_flg_project()` 假阳性：仅有 `.flg/` 空目录或遗留目录时，不再误判为正式 FLG 项目

## 4. 安装体验验证结果

- 已验证：在临时 Windows venv 中执行 `pip install -e .`
- 已验证：`flg version`
- 已验证：`flg init`
- 已验证：`flg frame`
- 已验证：`flg closeout --transcript examples/demo-proposal-project/demo_transcript.md`
- 已验证：`flg handoff`
- 已验证：`flg status`

验证方式：
- 使用临时 Windows venv：`%TEMP%\\flg-release-venv`
- 使用临时项目目录：`%TEMP%\\flg-release-project`
- 命令通过安装后的 `flg.exe` 执行，而不是依赖 `PYTHONPATH=src`

## 5. smoke test 结果

- 已验证：`python scripts/smoke_test.py`
- 运行解释器：临时 venv 的 `python.exe`
- 命令解析：优先使用当前解释器同目录的 `flg.exe`
- 结果：成功创建临时项目，跑通 `version/init/frame/closeout/handoff/status`
- 输出：列出了生成文件清单，并以 `0` 退出

## 6. pytest 结果

- 已验证：`pytest -q`
- 结果：`25 passed`

## 7. 已知限制

- 根目录不是 git 仓库，发布边界必须保持在 `framing-ledger/`
- 项目仍是启发式规则提取，不是高精度自动理解系统
- Project Flow Quality 还未继续推进
- 当前 smoke test 覆盖的是核心 CLI 主链，不包含更复杂的 merge / import / audit 回归组合

## 8. 是否可以进入 Project Flow Quality

可以。Goal 1 的安装、仓库边界和烟测要求已满足，下一轮应继续 Goal 2：降低 closeout 噪音并提升 handoff 接力价值。
