"""flg review command - Review candidate decisions and write accepted ones."""

from __future__ import annotations

import json
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


EVIDENCE_INDEX_PATH = Path(".flg") / "context" / "evidence_index.json"


# Placeholder markers that indicate a field was never filled in.
# If what_decided is empty OR why/alternatives/rejected/reversal are all
# placeholders, the candidate is a "shell" and --accept-all must skip it.
_PLACEHOLDER_VALUES = {
    "(not detected in context)",
    "(not detected by llm)",
    "(not provided by ai)",
    "(none detected)",
}


def _is_shell_decision_for_review(decision: dict) -> bool:
    """Detect a shell candidate decision that has no real context.

    A shell is either:
    - no what_decided content at all, or
    - why + alternatives + rejected + reversal all placeholder/empty.

    --accept-all skips these to keep DECISIONS.md trustworthy. Interactive
    review still allows a human to force-accept after seeing the warning.
    """
    what = (decision.get("what_decided") or "").strip()
    if not what:
        return True

    context_fields = (
        (decision.get("why") or "").strip().lower(),
        (decision.get("alternatives") or "").strip().lower(),
        (decision.get("rejected") or "").strip().lower(),
        (decision.get("reversal") or "").strip().lower(),
    )

    def _is_empty_or_placeholder(v: str) -> bool:
        if not v:
            return True
        return any(p in v for p in _PLACEHOLDER_VALUES)

    return all(_is_empty_or_placeholder(f) for f in context_fields)


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


def _load_evidence_index(root: Path) -> dict:
    index_path = root / EVIDENCE_INDEX_PATH
    if not index_path.exists():
        return {"version": 1, "items": {}}
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": 1, "items": {}}
    if not isinstance(data, dict):
        return {"version": 1, "items": {}}
    if "items" not in data or not isinstance(data["items"], dict):
        data["items"] = {}
    return data


def _save_evidence_index(root: Path, index: dict) -> Path:
    index_path = root / EVIDENCE_INDEX_PATH
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return index_path


def _extract_source_session_from_patch(content: str) -> str:
    for line in content.splitlines():
        if line.startswith("source_file:") or line.startswith("source_transcript:") or line.startswith("transcript:"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def _evidence_entry(
    decision_id: str,
    decision: dict,
    patch_path: Path,
    patch_info: dict,
    patch_content: str,
    reviewed_at: str,
) -> dict:
    return {
        "decision_id": decision_id,
        "status": "confirmed",
        "authority": "high",
        "source_type": "review_action",
        "source_patch": str(Path(".flg") / "patches" / patch_path.name),
        "source_session": _extract_source_session_from_patch(patch_content),
        "source_excerpt": decision.get("excerpt") or decision.get("what_decided") or "",
        "patch_id": patch_info.get("patch_id", "unknown"),
        "source_command": patch_info.get("source_command", "unknown"),
        "reviewed_at": reviewed_at,
        "title": decision.get("title") or "Accepted decision",
        "rationale": decision.get("why") or "",
        "rejected_alternatives": decision.get("rejected") or decision.get("alternatives") or "",
        "reversal_conditions": decision.get("reversal") or "",
    }


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
    accepted_evidence_entries = []
    skipped_shells = 0
    reviewed_at = datetime.now().isoformat(timespec="seconds")

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

        # Quality gate: shell decisions (no reasoning/alternatives/reversal)
        # must not be silently accepted via --accept-all. They pollute
        # DECISIONS.md with empty entries that look like real decisions.
        is_shell = _is_shell_decision_for_review(decision)
        if is_shell and accept_all:
            console.print("  [yellow]⚠ Skipped (shell decision: no reasoning/alternatives/reversal).[/yellow]")
            console.print("  [dim]--accept-all will not write shell decisions. Run without --accept-all to force-accept after review.[/dim]")
            skipped_shells += 1
            continue
        elif is_shell:
            console.print("  [yellow]⚠ Shell decision: no reasoning/alternatives/reversal detected.[/yellow]")
            console.print("  [dim]Recommended: reject and re-extract with more context, or fill in the why before accepting.[/dim]")

        default_accept = True if not is_shell else False
        accepted = accept_all or Confirm.ask("Accept this decision into DECISIONS.md?", default=default_accept)
        if accepted:
            decision_id = f"D-{next_number:03d}"
            accepted_entries.append(_build_decision_entry(next_number, decision))
            accepted_evidence_entries.append(
                _evidence_entry(
                    decision_id=decision_id,
                    decision=decision,
                    patch_path=patch_path,
                    patch_info=patch_info,
                    patch_content=content,
                    reviewed_at=reviewed_at,
                )
            )
            next_number += 1

    if not accepted_entries:
        if skipped_shells:
            console.print(f"[yellow]No decisions accepted. {skipped_shells} shell decision(s) skipped by --accept-all.[/yellow]")
            console.print("[dim]Re-run without --accept-all to force-accept shells after manual review, or re-extract with more context.[/dim]")
        else:
            console.print("[yellow]No decisions accepted.[/yellow]")
        raise typer.Exit(0)

    decisions_content = decisions_content.rstrip() + "\n\n" + "\n\n---\n".join(accepted_entries) + "\n"
    decisions_path.write_text(decisions_content, encoding="utf-8")

    evidence_index = _load_evidence_index(root)
    for item in accepted_evidence_entries:
        evidence_index["items"][item["decision_id"]] = item
    evidence_index["updated_at"] = datetime.now().isoformat(timespec="seconds")
    evidence_index_path = _save_evidence_index(root, evidence_index)

    state = load_state(root)
    if state and state.get("pending_patches"):
        for patch in state["pending_patches"]:
            if patch.get("patch_id") == patch_info.get("patch_id"):
                patch["decision_reviewed_at"] = reviewed_at
                patch["decision_review_status"] = "accepted"
                patch["evidence_index"] = str(EVIDENCE_INDEX_PATH)
                break
        save_state(root, state)

    console.print()
    console.print(f"[bold green]✓ Accepted {len(accepted_entries)} decision(s) into DECISIONS.md[/bold green]")
    if skipped_shells:
        console.print(f"[yellow]  {skipped_shells} shell decision(s) skipped (no reasoning/alternatives/reversal).[/yellow]")
    console.print(f"[bold green]✓ Evidence index updated:[/bold green] {evidence_index_path}")
    console.print("[dim]Run `flg merge --patch <file>` next to merge progress/risk/open-question updates.[/dim]")
