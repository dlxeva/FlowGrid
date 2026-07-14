"""Cross-file project consistency diagnostics and evidence reindexing."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..core.evidence import rebuild_evidence_index, save_evidence_index, validate_project
from ..core.files import is_flg_project

console = Console()


def doctor(
    project_path: str = typer.Argument(".", help="Path to a FLG project"),
    strict: bool = typer.Option(False, "--strict", help="Exit with code 1 when issues are found"),
) -> None:
    """Check consistency between the formal ledger, state, and evidence index."""
    root = Path(project_path).resolve()
    if not root.exists() or not is_flg_project(root):
        console.print(f"[red]Not a FLG project: {root}[/red]")
        raise typer.Exit(1)

    report = validate_project(root)
    table = Table(title=f"FlowGrid Doctor: {root}")
    table.add_column("Check", style="cyan")
    table.add_column("Result", style="bold")
    table.add_row("Overall", "OK" if report["status"] == "ok" else "Needs attention")
    table.add_row("Formal decisions", str(report["decision_count"]))
    table.add_row("Indexed decisions", str(report["index_count"]))
    table.add_row("Missing index entries", str(len(report["missing_index"])))
    table.add_row("Orphan index entries", str(len(report["orphan_index"])))
    table.add_row("Broken evidence refs", str(len(report["broken_references"])))
    table.add_row("Legacy paths", str(len(report["legacy_paths"])))
    table.add_row("Closed patches still pending", str(len(report["merged_pending"])))
    console.print(table)

    for key in ("missing_index", "orphan_index", "broken_references", "legacy_paths", "merged_pending"):
        values = report[key]
        if values:
            console.print(f"[yellow]{key}:[/yellow]")
            for value in values[:20]:
                console.print(f"  - {value}")

    if strict and report["status"] != "ok":
        raise typer.Exit(1)


def reindex(
    project_path: str = typer.Argument(".", help="Path to a FLG project"),
) -> None:
    """Rebuild evidence_index.json from DECISIONS.md."""
    root = Path(project_path).resolve()
    if not root.exists() or not is_flg_project(root):
        console.print(f"[red]Not a FLG project: {root}[/red]")
        raise typer.Exit(1)

    index = rebuild_evidence_index(root)
    path = save_evidence_index(root, index)
    console.print(f"[green]Rebuilt evidence index:[/green] {path}")
    console.print(f"Indexed {len(index['items'])} formal decision(s) from DECISIONS.md.")
