"""flg review command - Review candidate decisions and write accepted ones."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Confirm

from ..core.files import is_flg_project, read_file_safe
from ..core.state import load_state, save_state
from .handoff import parse_patch_for_handoff

console = Console()


def _next_decision_number(decisions_content: str) -> int:
    numbers = [int(match) for match in re.findall(r"## D-(\d+)", decisions_content)]
    return max(numbers, default=0) + 1


def _build_decision_entry(number: int, decision: dict) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    title = decision.get("title") or f"Accepted decision {number}"
    what_decided = decision.get("what_decided") or decision.get("excerpt") or "(to be reviewed)"
    why = decision.get("why") or "对话中未说明理由"
    alternatives = decision.get("alternatives") or "对话中未提及其他备选方案"
    rejected = decision.get("rejected") or "对话中未说明"
    reversal = decision.get("reversal") or "如果关键前提变化，需要重新评估"

    return f"""
## D-{number:03d} | {title}

### 决策时间
{today}

### 所属阶段
执行

### 决策背景
由 `flg review` 从待审核 patch 中确认写入。

### 核心问题
本轮项目推进中的关键判断。

### 备选方案
A. {alternatives}

### 最终决策
{what_decided}

### 决策理由
{why}

### 放弃理由
{rejected}

### 风险判断
待结合项目上下文补充。

### 后续验证
通过后续执行结果和项目反馈验证。

### 复盘入口
{reversal}
"""


def review_patch(
    patch_file: str = typer.Option(..., "--patch", "-p", help="Patch file to review"),
    accept_all: bool = typer.Option(False, "--accept-all", help="Accept all candidate decisions without prompting"),
) -> None:
    """Review candidate decisions from a patch and append accepted ones to DECISIONS.md."""
    root = Path.cwd()
    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)

    patch_path = Path(patch_file)
    if not patch_path.exists():
        patch_path = root / ".flg" / "patches" / patch_file
        if not patch_path.exists():
            console.print(f"[red]Patch not found: {patch_file}[/red]")
            raise typer.Exit(1)

    content = read_file_safe(patch_path)
    if not content:
        console.print("[red]Patch is empty.[/red]")
        raise typer.Exit(1)

    patch_info = parse_patch_for_handoff(content)
    decisions = patch_info["decisions"]
    if not decisions:
        console.print("[yellow]No candidate decisions found in this patch.[/yellow]")
        raise typer.Exit(0)

    decisions_path = root / "DECISIONS.md"
    decisions_content = read_file_safe(decisions_path) or "# Decision Log\n"
    next_number = _next_decision_number(decisions_content)
    accepted_entries = []

    console.print()
    console.print(f"[bold]Reviewing candidate decisions from[/bold] {patch_path.name}")
    console.print()

    for decision in decisions:
        console.print(f"[cyan]{decision.get('title', 'Untitled decision')}[/cyan]")
        if decision.get("what_decided"):
            console.print(f"  What: {decision['what_decided']}")
        if decision.get("why"):
            console.print(f"  Why: {decision['why']}")
        if decision.get("excerpt"):
            console.print(f"  Excerpt: {decision['excerpt']}")

        accepted = accept_all or Confirm.ask("Accept this decision into DECISIONS.md?", default=True)
        if accepted:
            accepted_entries.append(_build_decision_entry(next_number, decision))
            next_number += 1

    if not accepted_entries:
        console.print("[yellow]No decisions accepted.[/yellow]")
        raise typer.Exit(0)

    decisions_content = decisions_content.rstrip() + "\n\n" + "\n\n---\n".join(accepted_entries) + "\n"
    decisions_path.write_text(decisions_content, encoding="utf-8")

    state = load_state(root)
    if state and state.get("pending_patches"):
        for patch in state["pending_patches"]:
            if patch.get("patch_id") == patch_info.get("patch_id"):
                patch["decision_reviewed_at"] = datetime.now().isoformat(timespec="seconds")
                patch["decision_review_status"] = "accepted"
                break
        save_state(root, state)

    console.print()
    console.print(f"[bold green]✓ Accepted {len(accepted_entries)} decision(s) into DECISIONS.md[/bold green]")
    console.print("[dim]Run `flg merge --patch <file>` next to merge progress/risk/open-question updates.[/dim]")
