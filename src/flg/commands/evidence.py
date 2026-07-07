"""flg evidence command - Retrieve evidence for reviewed judgments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..core.files import is_flg_project, read_file_safe

console = Console()


EVIDENCE_INDEX_PATH = Path(".flg") / "context" / "evidence_index.json"


def _load_evidence_index(root: Path) -> dict[str, Any]:
    path = root / EVIDENCE_INDEX_PATH
    if not path.exists():
        return {"version": 1, "items": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": 1, "items": {}}
    if not isinstance(data, dict):
        return {"version": 1, "items": {}}
    if "items" not in data or not isinstance(data["items"], dict):
        data["items"] = {}
    return data


def _decision_block(decisions_content: str, decision_id: str) -> str:
    marker = f"## {decision_id}"
    start = decisions_content.find(marker)
    if start < 0:
        return ""
    next_start = decisions_content.find("\n## D-", start + len(marker))
    if next_start < 0:
        return decisions_content[start:].strip()
    return decisions_content[start:next_start].strip()


def evidence_command(decision_id: str = typer.Argument(..., help="Decision id, e.g. D-002")) -> None:
    """Show evidence behind a reviewed decision."""
    root = Path.cwd()
    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)

    normalized_id = decision_id.strip().upper()
    if not normalized_id.startswith("D-"):
        console.print("[red]Decision id must look like D-002.[/red]")
        raise typer.Exit(1)

    index = _load_evidence_index(root)
    item = index.get("items", {}).get(normalized_id)

    decisions_content = read_file_safe(root / "DECISIONS.md") or ""
    decision_block = _decision_block(decisions_content, normalized_id)

    if not item and not decision_block:
        console.print(f"[red]No evidence or decision entry found for {normalized_id}.[/red]")
        raise typer.Exit(1)

    console.print()
    console.print(f"[bold]Evidence for {normalized_id}[/bold]")
    console.print()

    table = Table(title="Judgment Metadata", show_lines=False)
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    if item:
        table.add_row("status", str(item.get("status", "unknown")))
        table.add_row("authority", str(item.get("authority", "unknown")))
        table.add_row("source_type", str(item.get("source_type", "unknown")))
        table.add_row("source_patch", str(item.get("source_patch", "unknown")))
        table.add_row("source_session", str(item.get("source_session", "unknown")))
        table.add_row("reviewed_at", str(item.get("reviewed_at", "unknown")))
        table.add_row("patch_id", str(item.get("patch_id", "unknown")))
    else:
        table.add_row("status", "unknown")
        table.add_row("authority", "unknown")
        table.add_row("source_type", "not indexed")

    console.print(table)
    console.print()

    if item and item.get("source_excerpt"):
        console.print(Panel(str(item["source_excerpt"]), title="Source Excerpt", border_style="green"))
        console.print()

    if decision_block:
        console.print(Panel(decision_block, title="DECISIONS.md Entry", border_style="cyan"))
        console.print()

    if item and item.get("source_patch"):
        patch_path = root / str(item["source_patch"])
        if patch_path.exists():
            console.print(f"[dim]Source patch exists: {patch_path}[/dim]")
        else:
            console.print(f"[yellow]Source patch not found on disk: {patch_path}[/yellow]")

    if not item:
        console.print("[yellow]This decision exists in DECISIONS.md but has no evidence index entry yet.[/yellow]")
        console.print("[dim]Evidence indexing is created by newer versions of `flg review`.[/dim]")
