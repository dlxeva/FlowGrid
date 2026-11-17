"""Offline synthetic evidence visibility, not agent reasoning or saved-time evaluation.

Run from the repository root with PYTHONDONTWRITEBYTECODE=1 and PYTHONPATH=src.
This file is also an independent pytest target.
Only disposable projects are initialized; the command prints a report to stdout.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import hashlib
import inspect
import json
from pathlib import Path
import re
import tempfile
from unittest.mock import patch

from typer.testing import CliRunner

from flg.cli import app
from flg.commands import context as ctx


BUDGET = 4000
MAX_CHARS = BUDGET * 4  # Same approximate-token convention as Resume, not a tokenizer.
BASE = "df919cb00df4ba18a28e78d3ff55203c7deebda9"
ACTION = "Review the local draft without sending it."
CONSTRAINT = "Never publish or spend without explicit approval."
MODES = ("raw_ledger", "default_resume", "query_resume")


@dataclass(frozen=True)
class Evidence:
    ident: str
    statement: str
    reversal: str = ""
    status: str = "confirmed"


@dataclass(frozen=True)
class Scenario:
    name: str
    query: str
    ledger: str
    evidence: tuple[Evidence, ...]
    expected_matches: tuple[str, ...]
    expected_current: tuple[str, ...]
    expected_history: tuple[str, ...] = ()


BRAND = Evidence("D-001", "User agency is the brand promise; never promise autonomous authority.")
FUNDING = Evidence(
    "D-002", "Defer the laboratory plan while the funding budget remains capped.",
    "Reconsider only if audited funding exceeds 250000 and a sponsor approves the budget.",
)
CHINESE = Evidence("D-003", "保留本地账本作为可审计事实源，公开传播不得替代用户授权。")
SUPERSEDED = Evidence("D-004", "Use the cloud migration route for the retired archive.", status="superseded")
REJECTED = Evidence("D-005", "Buy the platinum subscription for the abandoned rollout.", status="rejected")


def entry(item: Evidence, title: str, rationale: str = "A bounded local choice.") -> str:
    return (
        f"## {item.ident} | {title}\n\n### Status\n{item.status}\n\n"
        f"### Final Decision\n{item.statement}\n\n### Decision Rationale\n{rationale}\n\n"
        "### Rejected Alternatives\nUnreviewed expansion.\n\n"
        f"### Reversal Conditions\n{item.reversal or 'Recheck after new evidence.'}\n\n"
    )


def noise(number: int, *, long: bool = False) -> str:
    return entry(
        Evidence(f"D-{number:03d}", f"Use layout option {number}."),
        f"Local formatting {number}",
        "Typesetting spacing margins alignment. " * (16 if long else 1),
    )


def scenarios() -> tuple[Scenario, ...]:
    """Fixed oracles declared independently of selector results, before evaluation."""
    ledger = "# Synthetic decision ledger\n\n" + "".join((
        entry(BRAND, "Brand narrative and user agency"),
        entry(FUNDING, "Funding budget and laboratory plan"),
        entry(CHINESE, "保留本地账本和用户授权"),
        entry(SUPERSEDED, "Cloud migration"),
        entry(REJECTED, "Platinum subscription"),
        *(noise(i) for i in range(6, 14)),
    ))
    fallback = tuple(f"D-{i:03d}" for i in range(9, 14))
    def selected(ident: str) -> tuple[str, ...]:
        return (ident, *fallback[-4:])
    late = Evidence("D-041", "Retain the cobalt charter until the operator approves a revision.")
    long_ledger = "# Synthetic long ledger\n\n" + "".join(noise(i, long=True) for i in range(1, 41))
    long_ledger += entry(late, "Cobalt charter") + "".join(noise(i) for i in range(42, 50))
    recent = Evidence("D-014", "Keep the maple checklist beside the local draft.")
    return (
        Scenario("early_brand_beyond_recent_five", "brand narrative user agency", ledger,
                 (BRAND,), ("D-001",), selected("D-001")),
        Scenario("old_budget_and_reversal", "funding budget", ledger,
                 (FUNDING,), ("D-002",), selected("D-002")),
        Scenario("old_chinese_judgment", "本地账本用户授权", ledger,
                 (CHINESE,), ("D-003",), selected("D-003")),
        Scenario("superseded_history_only", "cloud migration", ledger,
                 (SUPERSEDED,), ("D-004",), fallback, ("D-004",)),
        Scenario("rejected_history_only", "platinum subscription", ledger,
                 (REJECTED,), ("D-005",), fallback, ("D-005",)),
        Scenario("unrelated_noise_no_fabrication", "qzxvnoise nebulaquartz", ledger,
                 (), (), fallback),
        Scenario("explicit_decision_id", "D-001", ledger,
                 (BRAND,), ("D-001",), selected("D-001")),
        Scenario("long_ledger_target_after_raw_cap", "cobalt charter", long_ledger,
                 (late,), ("D-041",), ("D-041", "D-046", "D-047", "D-048", "D-049")),
        Scenario("short_recent_positive_control", "maple checklist", ledger + entry(recent, "Maple checklist"),
                 (recent,), ("D-014",), ("D-014", "D-010", "D-011", "D-012", "D-013")),
    )


def snapshot(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def init_fixture(root: Path, case: Scenario) -> None:
    # Explicit --dir prevents ever initializing the caller's checkout.
    result = CliRunner().invoke(app, ["init", "Synthetic availability", "--language", "en", "--dir", str(root)])
    assert result.exit_code == 0, result.output
    (root / "DECISIONS.md").write_text(case.ledger, encoding="utf-8")
    (root / "SNAPSHOT.md").write_text(
        "# Snapshot\n\n## Current Core Goal\nPrepare the local brief.\n\n"
        f"## Next Highest Priority Action\n{ACTION}\n\n## Hard Constraints\n- {CONSTRAINT}\n",
        encoding="utf-8",
    )
    # Replace date-bearing template prose so output and repeat checks are stable.
    for filename, content in {
        "FRAMING.md": "# Framing\n\n## Goals\nPrepare the local brief.\n\n## Review Objects\nLocal draft.\n",
        "PROGRESS.md": "# Progress\n\nLocal synthetic draft prepared.\n",
        "CONSTRAINTS.md": f"# Constraints\n\n- {CONSTRAINT}\n",
        "GOAL_EVOLUTION.md": "# Goal evolution\n",
    }.items():
        (root / filename).write_text(content, encoding="utf-8")


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 11, 17, 0, 0, 0, tzinfo=tz)


def section(content: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)", content, re.M | re.S)
    return match.group(1) if match else ""


def visible(content: str, item: Evidence) -> dict:
    # Query echoes, source links, or evidence references alone do not count as an ID hit.
    ident = bool(re.search(rf"^(?:#{{2,3}} {item.ident}\s*[|｜]|- {item.ident} status=)", content, re.M))
    needles = {"id": ident, "statement": item.statement in content}
    if item.reversal:
        needles["reversal"] = item.reversal in content
    return {"id": item.ident, "needles": needles, "all_visible": all(needles.values())}


def evaluate_case(root: Path, case: Scenario) -> dict:
    init_fixture(root, case)
    before = snapshot(root)
    with patch.object(ctx, "datetime", FrozenDatetime):
        default, default_meta = ctx.build_context_pack(root, mode="resume", budget=BUDGET)
        focused, meta = ctx.build_context_pack(root, mode="resume", budget=BUDGET, query=case.query)
        again, again_meta = ctx.build_context_pack(root, mode="resume", budget=BUDGET, query=case.query)
        default_after, default_meta_after = ctx.build_context_pack(root, mode="resume", budget=BUDGET)
    assert snapshot(root) == before, f"{case.name}: context mutated the fixture"
    assert (focused, meta) == (again, again_meta), f"{case.name}: unstable query output"
    assert (default, default_meta) == (default_after, default_meta_after), "default path changed after query"
    assert "task_focus" not in default_meta
    focus = meta["task_focus"]
    assert {"current_ids", "matches", "historical"} <= focus.keys()
    assert focus["current_ids"] == list(case.expected_current), (case.name, focus)
    assert [m["id"] for m in focus["matches"]] == list(case.expected_matches), (case.name, focus)
    assert [h["id"] for h in focus["historical"]] == list(case.expected_history), (case.name, focus)
    assert focus["formal_state_changed"] is False
    assert meta["current_action"] == default_meta["current_action"]
    for content, metadata in ((default, default_meta), (focused, meta)):
        assert ACTION in content and CONSTRAINT in content
        assert metadata["chars"] == len(content) <= MAX_CHARS
    for item in case.evidence:
        assert visible(focused, item)["all_visible"], (case.name, visible(focused, item))
        confirmed = section(focused, "Confirmed Decisions")
        if item.status in {"superseded", "rejected"}:
            history = section(focused, "Task-related History")
            assert "Non-current history" in history
            assert f"{item.ident} status={item.status}" in history and item.statement in history
            assert item.ident not in confirmed and item.statement not in confirmed
            assert item.ident not in section(default, "Confirmed Decisions")
        else:
            assert item.ident in confirmed and item.statement in confirmed
        if item.reversal:
            match = next(m for m in focus["matches"] if m["id"] == item.ident)
            assert match["reversal_terms"], "fixture must actually exercise reversal overlap"
            assert "No condition is confirmed met" in focused
    if not case.evidence:
        assert not focus["matches"] and not focus["historical"]
        assert "No additional lexical match" in focused
    outputs = {"raw_ledger": case.ledger[:MAX_CHARS], "default_resume": default, "query_resume": focused}
    modes = {}
    for name, content in outputs.items():
        checks = [visible(content, item) for item in case.evidence]
        modes[name] = {
            "chars": len(content), "approx_tokens": (len(content) + 3) // 4,
            "truncated": len(case.ledger) > MAX_CHARS if name == "raw_ledger" else bool(
                (default_meta if name == "default_resume" else meta)["truncated"]),
            "checks": checks,
            "available": sum(c["all_visible"] for c in checks), "total": len(checks),
        }
    return {
        "scenario": case.name, "query": case.query,
        "ledger_chars": len(case.ledger),
        "ledger_sha256": hashlib.sha256(case.ledger.encode()).hexdigest(),
        "expected_evidence": [dict(id=e.ident, statement=e.statement, reversal=e.reversal, status=e.status)
                              for e in case.evidence],
        "modes": modes, "task_focus": focus,
        "checks": {"fixture_unchanged": True, "query_repeat_identical": True,
                   "default_unchanged_after_query": True, "action_and_constraints_retained": True,
                   "history_not_promoted": True, "metadata_matches_fixed_oracle": True},
    }


def evaluate() -> dict:
    if "query" not in inspect.signature(ctx.build_context_pack).parameters:
        raise RuntimeError("query core is not on disk yet; wait before running this evaluation")
    # Source hashes identify the actual uncommitted implementation, not just base HEAD.
    repo_root = Path(__file__).resolve().parents[1]
    source_files = (Path(ctx.__file__).resolve(), Path(ctx.__file__).resolve().parents[1] / "core/task_focus.py",
                    Path(__file__).resolve())
    for source in source_files:
        if not source.is_file():
            raise RuntimeError(f"core is not on disk yet: {source.relative_to(repo_root).as_posix()}")
    with tempfile.TemporaryDirectory(prefix="flg-task-focus-eval-") as tmp:
        rows = [evaluate_case(Path(tmp) / case.name, case) for case in scenarios()]
    totals = {
        mode: {"available": sum(row["modes"][mode]["available"] for row in rows),
               "total": sum(row["modes"][mode]["total"] for row in rows),
               "needles_visible": sum(sum(c["needles"].values()) for row in rows for c in row["modes"][mode]["checks"]),
               "needles_total": sum(len(c["needles"]) for row in rows for c in row["modes"][mode]["checks"])}
        for mode in MODES
    }
    return {"evaluation": "task-focus-availability-eval", "base": BASE, "budget": BUDGET,
            "max_chars": MAX_CHARS,
            "source_sha256": {p.relative_to(repo_root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in source_files},
            "totals": totals, "scenarios": rows}


def render_markdown(report: dict) -> str:
    lines = ["# 查询恢复包固定预算证据回放", "", "日期：2026-11-17。纯合成、离线、one-shot。", "",
             "## 实测结果", "", "| 输入 | 完整目标证据 | 精确检查点 |", "| --- | ---: | ---: |"]
    for mode, values in report["totals"].items():
        lines.append(f"| {mode} | {values['available']}/{values['total']} | "
                     f"{values['needles_visible']}/{values['needles_total']} |")
    lines += ["", "完整目标须同时出现决策记录 ID、预先指定的完整原句，以及有要求的完整反转条件。"
              "无匹配负例单列，不作为一次成功检索加入分母。", "",
              "| 场景 | raw ledger | 默认 Resume | query Resume | raw / 默认 / query 字符数 |",
              "| --- | --- | --- | --- | --- |"]
    for row in report["scenarios"]:
        cells = []
        for mode in MODES:
            item = row["modes"][mode]
            cells.append(f"{item['available']}/{item['total']}" if item["total"] else "负例，见下")
        lengths = " / ".join(str(row["modes"][m]["chars"]) for m in MODES)
        lines.append(f"| {row['scenario']} | {' | '.join(cells)} | {lengths} |")
    lines += ["", "## 固定方法与实际校验", "",
              "三个输入使用同一 budget=4000，沿用现有实现的 4 字符约等于 1 token 上限，最多16000字符。"
              "这不是真实模型 tokenizer 的4000 token，中文尤其可能有偏差。",
              "raw ledger 只取 DECISIONS.md 原始前缀16000字符，顺序固定、不按 query 重排。"
              "它不承担 Resume 的项目身份、当前行动、约束和安全提示开销，因此对 raw 保留更宽松的证据容量。"
              "未运行额外证据展开命令。长例是明确构造的前缀截断压力例，不能泛化为所有 raw 排序。",
              "短例 raw 通常不输；目标都在短账本内，包含 superseded/rejected 原始状态。"
              "query 的收益取决于默认最近5条的遗漏和固定原始前缀截断，未证明普遍更优。",
              "所有 fixture 使用临时目录 TemporaryDirectory 和显式 init --dir，退出自动清理。"
              "每例比较生成前后全部文件哈希，重复 query 比较正文与元数据，且确认生成 query 后默认 Resume 未变。"
              "固定时间只为消除 Generated 时间差；不存在网络、远端模型或真实业务数据。",
              "逐例断言 task_focus 的 current_ids、matches、historical 与预声明列表一致。"
              "superseded/rejected 必须标明原状态并留在 Non-current history，禁止进入 Confirmed Decisions。"
              "预算反转词命中只触发线索提示，并断言 No condition is confirmed met。"
              "无关噪声必须 matches=[]、historical=[]，current_ids 为固定最近5条且显示无额外命中。"
              "每个 Resume 保留同一当前行动与授权约束；query formal_state_changed=False。", "",
              "## 局限", "",
              "此评测只检测预先给定的 ID 和完整原句可见性、状态分区及只读契约。"
              "ID 单独出现在 query 回显、来源链接或 evidence 命令中不计可见。"
              "没有真实 agent 冷接手、回答或决策质量评审，也没有时间节省、用户体验或长期收益数据。"
              "词面命中不证明推理正确；未覆盖同义改写、跨语言语义、多目标竞争、长字段截断、"
              "生产规模、外部来源新鲜度与所有预算失败路径。无关噪声例仅证明该固定输入未伪造匹配。", "",
              "## 重复验证", "", "从仓库根目录运行，python 使用已安装项目依赖的解释器。", "", "```sh",
              "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B evals/task_focus_availability.py",
              "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m pytest "
              "-c /dev/null -p no:cacheprovider "
              "evals/task_focus_availability.py -q",
              "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B evals/task_focus_availability.py --json",
              "```", "", "默认打印报告，不写文件；--json 打印逐例机器可读数据。"
              "报告文件由 apply_patch 保存，评测入口自身不写仓库。", "", "## 实测摘要与源码哈希", "",
              "源码哈希键均为仓库相对路径。完整逐例数据通过上面的 --json 命令复现。", "",
              "```json", json.dumps({
                  **{key: report[key] for key in ("evaluation", "base", "budget", "max_chars", "source_sha256", "totals")},
                  "scenario_count": len(report["scenarios"]),
              }, ensure_ascii=False, indent=2), "```", ""]
    return "\n".join(lines)


def test_oracles_cover_required_scenarios():
    cases = scenarios()
    assert len(cases) == 9 and len({c.name for c in cases}) == 9
    assert all(len(c.ledger) < MAX_CHARS for c in cases if not c.name.startswith("long_"))
    assert next(c for c in cases if c.name.startswith("long_")).ledger.index("## D-041") > MAX_CHARS
    assert len({c.query for c in cases}) == len(cases)


def test_id_echo_and_incomplete_sentence_do_not_count():
    assert not visible("Query: D-001\nSource DECISIONS.md#D-001\nflg evidence D-001", BRAND)["needles"]["id"]
    probe = "### D-001 | Brand narrative\nUser agency is the brand promise;"
    assert visible(probe, BRAND)["needles"]["id"]
    assert not visible(probe, BRAND)["all_visible"]


def test_offline_availability_and_authority_contract():
    report = evaluate()
    assert set(report["source_sha256"]) == {
        "src/flg/commands/context.py", "src/flg/core/task_focus.py", "evals/task_focus_availability.py",
    }
    assert all(not Path(key).is_absolute() for key in report["source_sha256"])
    assert str(Path(__file__).resolve().parents[1]) not in json.dumps(report)
    rendered = render_markdown(report)
    assert str(Path(__file__).resolve().parents[1]) not in rendered
    assert "PYTHONPATH=src python -B evals/task_focus_availability.py --json" in rendered
    assert report["totals"]["query_resume"]["available"] == 8
    assert report["totals"]["raw_ledger"]["available"] == 7
    assert report["totals"]["default_resume"]["available"] == 1
    # All fixed short positive examples are genuinely available in raw input.
    for row in report["scenarios"]:
        if row["ledger_chars"] <= MAX_CHARS:
            assert row["modes"]["raw_ledger"]["available"] == row["modes"]["raw_ledger"]["total"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print full measured data instead of Markdown")
    args = parser.parse_args()
    report = evaluate()
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render_markdown(report), end="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
