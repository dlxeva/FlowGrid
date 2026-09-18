"""Report which formal decisions require revalidation after a change."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..core.files import is_flg_project, read_file_safe
from ..core.impact import analyze_impact
from ..core.relations import normalize_decision_id, parse_decision_relations

console = Console()


def impact_command(
    decision_id: str = typer.Argument(
        ...,
        help="Decision whose evidence, validity, or state may have changed.",
    ),
) -> None:
    """Show the affected judgment subgraph without mutating formal state."""
    root = Path.cwd()
    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)

    normalized_id = normalize_decision_id(decision_id)
    if normalized_id is None:
        console.print("[red]Decision id must look like D-002.[/red]")
        raise typer.Exit(1)

    content = read_file_safe(root / "DECISIONS.md") or ""
    graph = parse_decision_relations(content)
    if normalized_id not in graph:
        console.print(f"[red]No decision found for {normalized_id}.[/red]")
        raise typer.Exit(1)

    paths = analyze_impact(graph, normalized_id)
    console.print(f"\n[bold]Impact report for {normalized_id}[/bold]")
    console.print("[dim]Read-only: no formal decision status was changed.[/dim]\n")

    if not paths:
        console.print("[green]No related decision requires automatic revalidation.[/green]")
        return

    table = Table(title="Revalidation Candidates")
    table.add_column("Decision", style="bold")
    table.add_column("Depth", justify="right")
    table.add_column("Path")
    table.add_column("Derived status", style="yellow")
    for item in paths:
        table.add_row(
            item.decision_id,
            str(item.depth),
            f"{item.parent} → {item.via}",
            "revalidation_required",
        )
    console.print(table)
    console.print(
        "\n[yellow]Owner gate:[/yellow] review the evidence before changing, "
        "superseding, or promoting any formal decision."
    )
