"""Trace a reviewed judgment through its evidence episodes and relations."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..core.evidence import load_evidence_index
from ..core.files import is_flg_project, read_file_safe
from ..core.relations import (
    RELATION_TYPES,
    incoming_relations,
    normalize_decision_id,
    parse_decision_relations,
    relation_parse_issues,
)

console = Console()


def _decision_block(content: str, decision_id: str) -> str:
    marker = f"## {decision_id}"
    start = content.find(marker)
    if start < 0:
        return ""
    end = content.find("\n## D-", start + len(marker))
    return content[start:end if end >= 0 else None].strip()


def _relation_table(content: str, decision_id: str) -> Table | None:
    graph = parse_decision_relations(content)
    parse_issues = [
        issue
        for issue in relation_parse_issues(content)
        if issue.source == decision_id
    ]
    outgoing = graph.get(decision_id, {})
    incoming = incoming_relations(graph, decision_id)
    has_outgoing = any(outgoing.get(relation) for relation in RELATION_TYPES)
    if not has_outgoing and not incoming and not parse_issues:
        return None

    table = Table(title="Decision Relations")
    table.add_column("Direction", style="cyan")
    table.add_column("Relation")
    table.add_column("Decision", style="bold")

    for relation in RELATION_TYPES:
        for target in outgoing.get(relation, ()):
            table.add_row("outgoing", relation, target)
    for relation, source in incoming:
        table.add_row("incoming", relation, source)
    for issue in parse_issues:
        table.add_row("malformed", issue.relation, issue.raw_value)
    return table


def trace_command(
    decision_id: str = typer.Argument(..., help="Decision id, e.g. D-002"),
) -> None:
    """Show how a formal judgment entered and remains in project state."""
    root = Path.cwd()
    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)

    normalized_id = normalize_decision_id(decision_id)
    if normalized_id is None:
        console.print("[red]Decision id must look like D-002.[/red]")
        raise typer.Exit(1)

    index = load_evidence_index(root)
    item = index.get("items", {}).get(normalized_id)
    decisions = read_file_safe(root / "DECISIONS.md") or ""
    block = _decision_block(decisions, normalized_id)
    if not item and not block:
        console.print(f"[red]No decision found for {normalized_id}.[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Trace for {normalized_id}[/bold]\n")
    if item:
        console.print(
            f"[cyan]Current status:[/cyan] {item.get('status', 'unknown')}  "
            f"[cyan]Authority:[/cyan] {item.get('authority', 'unknown')}"
        )
        episodes = item.get("source_episodes", [])
        if episodes:
            table = Table(title="Source Episodes")
            table.add_column("Relation", style="cyan")
            table.add_column("Episode")
            table.add_column("Type")
            table.add_column("Reference")
            for episode in episodes:
                table.add_row(
                    str(episode.get("relation", "unknown")),
                    str(episode.get("source_id", "unknown")),
                    str(episode.get("source_type", "unknown")),
                    str(episode.get("source_ref", "unknown")),
                )
            console.print(table)
        else:
            console.print(
                "[yellow]No source episode index yet. "
                "Run `flg reindex` to rebuild it.[/yellow]"
            )

        excerpt = item.get("source_excerpt")
        if excerpt:
            console.print(
                Panel(
                    str(excerpt),
                    title="Retained Source Excerpt",
                    border_style="green",
                )
            )
    else:
        console.print(
            "[yellow]This ledger entry is not indexed. "
            "Run `flg reindex` before relying on provenance.[/yellow]"
        )

    relation_table = _relation_table(decisions, normalized_id)
    if relation_table:
        console.print(relation_table)

    if block:
        console.print(
            Panel(block, title="Formal Ledger Entry", border_style="cyan")
        )
