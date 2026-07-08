"""flg decision command - Strong commitment direct write to DECISIONS.md."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..core.files import is_flg_project, read_file_safe

console = Console()
EVIDENCE_INDEX_PATH = Path(".flg") / "context" / "evidence_index.json"


def decision_add(
    decision: str = typer.Option(
        ..., "-d", "--decision", help="决策内容（必填）"
    ),
    rationale: str = typer.Option(
        ..., "-r", "--rationale", help="决策理由（必填）"
    ),
    principle: bool = typer.Option(
        False, "--principle", help="标记为工作原则"
    ),
    question: Optional[str] = typer.Option(
        None, "-q", "--question", help="这条决策回答什么问题"
    ),
    alternatives: Optional[str] = typer.Option(
        None, "-a", "--alternatives", help="备选方案（逗号分隔）"
    ),
    risks: Optional[str] = typer.Option(
        None, "-k", "--risks", help="风险判断"
    ),
    evidence: Optional[str] = typer.Option(
        None, "-e", "--evidence", help="证据来源（用户原话等）"
    ),
) -> None:
    """强承诺信号直接写入 DECISIONS.md（跳过 capture 阶段）。

    仅在用户明确说"记一条/定了/写进决策日志/后续按这个推进/这个作为原则"时使用。
    """
    root = Path.cwd()
    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)

    decisions_path = root / "DECISIONS.md"
    decisions_content = read_file_safe(decisions_path) or "# Decision Log\n"

    numbers = [int(m) for m in re.findall(r"## D-(\d+)", decisions_content)]
    next_num = max(numbers, default=0) + 1
    decision_id = f"D-{next_num:03d}"

    today = datetime.now().strftime("%Y-%m-%d")
    reviewed_at = datetime.now().isoformat(timespec="seconds")

    type_label = "原则" if principle else "决策"
    alt_list = [a.strip() for a in alternatives.split(",") if a.strip()] if alternatives else []
    alt_str = "、".join(alt_list) if alt_list else "未记录备选方案"

    entry = f"""## {decision_id} | {decision[:50]}

### 决策时间
{today}

### 所属阶段
执行

### 决策背景
用户明确指令：直接写入决策日志（`flg decision add`）。

### 核心问题
{question or '项目推进中的关键判断'}

### 备选方案
A. {alt_str}

### 最终决策
{decision}

### 决策理由
{rationale}

### 放弃理由
选择了当前方案，放弃其他备选方案。

### 风险判断
{risks or '待结合项目上下文补充'}

### 后续验证
通过后续执行结果和项目反馈验证。

### 复盘入口
如果关键前提变化或出现新的替代方案，需要重新评估。

---

*{type_label} | Source: {evidence if evidence else '用户明确指令'}*
"""

    decisions_content = decisions_content.rstrip() + "\n\n" + entry
    decisions_path.write_text(decisions_content, encoding="utf-8")

    # Update evidence index
    evidence_index_path = root / EVIDENCE_INDEX_PATH
    evidence_index: dict = {"version": 1, "items": {}}
    if evidence_index_path.exists():
        try:
            evidence_index = json.loads(evidence_index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    evidence_index.setdefault("items", {})[decision_id] = {
        "decision_id": decision_id,
        "status": "confirmed",
        "authority": "high",
        "source_type": "user_confirmation",
        "source_excerpt": evidence or decision,
        "reviewed_at": reviewed_at,
        "title": decision[:60],
        "rationale": rationale,
        "rejected_alternatives": ", ".join(alt_list),
    }
    evidence_index["updated_at"] = reviewed_at
    evidence_index_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_index_path.write_text(json.dumps(evidence_index, ensure_ascii=False, indent=2), encoding="utf-8")

    console.print()
    console.print(f"[bold green]✓ Decision recorded:[/bold green] [cyan]{decision_id}[/cyan]")
    console.print(f"  Type: {'principle' if principle else 'decision'}  |  Status: confirmed")
    console.print(f"  {decision}")
    console.print()
