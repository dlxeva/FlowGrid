# 查询恢复包固定预算证据回放

日期：2026-11-17。纯合成、离线、one-shot。

## 实测结果

| 输入 | 完整目标证据 | 精确检查点 |
| --- | ---: | ---: |
| raw_ledger | 7/8 | 15/17 |
| default_resume | 1/8 | 2/17 |
| query_resume | 8/8 | 17/17 |

完整目标须同时出现决策记录 ID、预先指定的完整原句，以及有要求的完整反转条件。无匹配负例单列，不作为一次成功检索加入分母。

| 场景 | raw ledger | 默认 Resume | query Resume | raw / 默认 / query 字符数 |
| --- | --- | --- | --- | --- |
| early_brand_beyond_recent_five | 1/1 | 0/1 | 1/1 | 3589 / 4614 / 5207 |
| old_budget_and_reversal | 1/1 | 0/1 | 1/1 | 3589 / 4614 / 5487 |
| old_chinese_judgment | 1/1 | 0/1 | 1/1 | 3589 / 4614 / 5122 |
| superseded_history_only | 1/1 | 0/1 | 1/1 | 3589 / 4614 / 5591 |
| rejected_history_only | 1/1 | 0/1 | 1/1 | 3589 / 4614 / 5623 |
| unrelated_noise_no_fabrication | 负例，见下 | 负例，见下 | 负例，见下 | 3589 / 4614 / 5084 |
| explicit_decision_id | 1/1 | 0/1 | 1/1 | 3589 / 4614 / 5115 |
| long_ledger_target_after_raw_cap | 0/1 | 0/1 | 1/1 | 16000 / 4616 / 5154 |
| short_recent_positive_control | 1/1 | 1/1 | 1/1 | 3858 / 4624 / 5141 |

## 固定方法与实际校验

三个输入使用同一 budget=4000，沿用现有实现的 4 字符约等于 1 token 上限，最多16000字符。这不是真实模型 tokenizer 的4000 token，中文尤其可能有偏差。
raw ledger 只取 DECISIONS.md 原始前缀16000字符，顺序固定、不按 query 重排。它不承担 Resume 的项目身份、当前行动、约束和安全提示开销，因此对 raw 保留更宽松的证据容量。未运行额外证据展开命令。长例是明确构造的前缀截断压力例，不能泛化为所有 raw 排序。
短例 raw 通常不输；目标都在短账本内，包含 superseded/rejected 原始状态。query 的收益取决于默认最近5条的遗漏和固定原始前缀截断，未证明普遍更优。
所有 fixture 使用临时目录 TemporaryDirectory 和显式 init --dir，退出自动清理。每例比较生成前后全部文件哈希，重复 query 比较正文与元数据，且确认生成 query 后默认 Resume 未变。固定时间只为消除 Generated 时间差；不存在网络、远端模型或真实业务数据。
逐例断言 task_focus 的 current_ids、matches、historical 与预声明列表一致。superseded/rejected 必须标明原状态并留在 Non-current history，禁止进入 Confirmed Decisions。预算反转词命中只触发线索提示，并断言 No condition is confirmed met。无关噪声必须 matches=[]、historical=[]，current_ids 为固定最近5条且显示无额外命中。每个 Resume 保留同一当前行动与授权约束；query formal_state_changed=False。

## 局限

此评测只检测预先给定的 ID 和完整原句可见性、状态分区及只读契约。ID 单独出现在 query 回显、来源链接或 evidence 命令中不计可见。没有真实 agent 冷接手、回答或决策质量评审，也没有时间节省、用户体验或长期收益数据。词面命中不证明推理正确；未覆盖同义改写、跨语言语义、多目标竞争、长字段截断、生产规模、外部来源新鲜度与所有预算失败路径。无关噪声例仅证明该固定输入未伪造匹配。

## 重复验证

从仓库根目录运行，python 使用已安装项目依赖的解释器。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B evals/task_focus_availability.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m pytest -c /dev/null -p no:cacheprovider evals/task_focus_availability.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B evals/task_focus_availability.py --json
```

默认打印报告，不写文件；--json 打印逐例机器可读数据。报告文件由 apply_patch 保存，评测入口自身不写仓库。

## 本次验证回执

- 最终冻结核心版本重跑：独立评测 3 passed；联合 selector / context / eval：84 passed。
- 两次独立 CLI 回放的完整输出逐字一致（包括相对路径源码哈希）。
- 本轮仅更新此报告，评测脚本未改；未提交、未推送。未纳入私有回放内容。

## 实测摘要与源码哈希

源码哈希键均为仓库相对路径。完整逐例数据通过上面的 --json 命令复现。

```json
{
  "evaluation": "task-focus-availability-eval",
  "base": "df919cb00df4ba18a28e78d3ff55203c7deebda9",
  "budget": 4000,
  "max_chars": 16000,
  "source_sha256": {
    "src/flg/commands/context.py": "18bbe3a3b79f23f75aa9f2b64da4f533d03c37b286ef7630717d60fd8d4bcae7",
    "src/flg/core/task_focus.py": "b2380d5a5715b7c496bd8288498a9ce925357bd71ed121e87ad0dcd26563c9b9",
    "evals/task_focus_availability.py": "134e8a206555bfc70b71ed66b275bf70a9e12a18c20197edd1445cbfa54be4c4"
  },
  "totals": {
    "raw_ledger": {
      "available": 7,
      "total": 8,
      "needles_visible": 15,
      "needles_total": 17
    },
    "default_resume": {
      "available": 1,
      "total": 8,
      "needles_visible": 2,
      "needles_total": 17
    },
    "query_resume": {
      "available": 8,
      "total": 8,
      "needles_visible": 17,
      "needles_total": 17
    }
  },
  "scenario_count": 9
}
```
