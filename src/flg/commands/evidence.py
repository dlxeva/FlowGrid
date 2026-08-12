"""flg evidence command - Retrieve evidence for reviewed judgments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..core.evidence import parse_decisions_ledger
from ..core.evidence_search import search_evidence_records
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


def _search_evidence(
    root: Path,
    query: str,
    *,
    top_k: int,
    include_pending: bool,
    include_history: bool,
    include_all: bool,
    include_unindexed: bool,
) -> None:
    decisions_content = read_file_safe(root / "DECISIONS.md") or ""
    decisions = parse_decisions_ledger(decisions_content)
    index = _load_evidence_index(root)
    try:
        leads = search_evidence_records(
            decisions,
            index.get("items", {}),
            query,
            top_k=top_k,
            include_pending=include_pending,
            include_history=include_history,
            include_all=include_all,
            include_unindexed=include_unindexed,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc

    console.print()
    console.print(f"[bold]Evidence leads for: {query.strip()}[/bold]")
    console.print("[dim]Read-only retrieval; results are evidence leads, not an answer or current action.[/dim]")
    console.print()
    if not leads:
        console.print("[yellow]No matching indexed evidence found for the selected status scope.[/yellow]")
        return

    table = Table(show_lines=True)
    table.add_column("Decision", style="cyan", no_wrap=True)
    table.add_column("Status", style="green", no_wrap=True)
    table.add_column("Authority", no_wrap=True)
    table.add_column("Score", justify="right", no_wrap=True)
    table.add_column("Matched fields")
    table.add_column("Title")
    for lead in leads:
        table.add_row(
            str(lead["decision_id"]),
            str(lead["status"]),
            str(lead["authority"]),
            f"{float(lead['score']):.3f}",
            ", ".join(lead["matched_fields"]),
            str(lead["title"]),
        )
    console.print(table)
    for lead in leads:
        provenance = lead["source_references"] or ("indexed" if lead["indexed"] else "not indexed")
        console.print(
            Panel(
                str(lead["excerpt"] or "(no excerpt recorded)"),
                title=f"{lead['decision_id']} evidence · {provenance}",
                border_style="cyan",
            )
        )


def evidence_command(
    decision_id: Optional[str] = typer.Argument(None, help="Decision id, e.g. D-002"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Find relevant reviewed evidence."),
    top_k: int = typer.Option(5, "--top-k", min=1, max=50, help="Maximum evidence leads to return."),
    include_pending: bool = typer.Option(False, "--include-pending", help="Include pending or contested judgments."),
    include_history: bool = typer.Option(False, "--include-history", help="Include stale, superseded, rejected, or archived judgments."),
    include_all: bool = typer.Option(False, "--include-all", help="Include judgments with unknown or custom statuses."),
    include_unindexed: bool = typer.Option(False, "--include-unindexed", help="Include ledger entries without provenance index records."),
) -> None:
    """Show one reviewed decision or search read-only evidence leads."""
    root = Path.cwd()
    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)

    if decision_id and query:
        console.print("[red]Choose either a decision id or --query, not both.[/red]")
        raise typer.Exit(2)
    if query is not None:
        _search_evidence(
            root,
            query,
            top_k=top_k,
            include_pending=include_pending,
            include_history=include_history,
            include_all=include_all,
            include_unindexed=include_unindexed,
        )
        return
    if not decision_id:
        console.print("[red]Provide a decision id or use --query/-q.[/red]")
        raise typer.Exit(2)

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
