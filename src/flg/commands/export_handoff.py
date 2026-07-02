"""flg export-handoff command - Export a resumable handoff pack."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console

from ..core.files import is_flg_project, read_file_safe
from .handoff import generate_handoff_summary

console = Console()


def export_handoff_pack(
    output: Path | None = typer.Option(None, "--output", "-o", help="Optional output path"),
) -> None:
    """Export a resumable handoff pack for future sessions or other agents."""
    root = Path.cwd()

    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)

    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = output or (root / ".flg" / "exports" / f"handoff-pack-{now}.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    handoff_summary = generate_handoff_summary(root)
    snapshot_content = read_file_safe(root / "SNAPSHOT.md") or "(missing)"
    goal_evolution = read_file_safe(root / "GOAL_EVOLUTION.md") or "(missing)"
    constraints_content = read_file_safe(root / "CONSTRAINTS.md") or "(missing)"
    anchors_content = read_file_safe(root / "ANCHORS.md") or "(missing)"

    content = f"""# FlowGrid Handoff Pack

Generated: {datetime.now().isoformat(timespec="seconds")}

## 1. Resume Summary

{handoff_summary}

## 2. Snapshot

{snapshot_content}

## 3. Goal Evolution

{goal_evolution}

## 4. Constraints

{constraints_content}

## 5. Authoritative Anchors

{anchors_content}
"""

    output_path.write_text(content, encoding="utf-8")

    console.print()
    console.print("[bold green]✓ Handoff pack exported[/bold green]")
    console.print()
    console.print(f"Output: {output_path}")
