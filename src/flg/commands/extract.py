"""flg extract-decisions command - Extract candidate decisions from project files."""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown

from ..core.files import is_flg_project, read_file_safe
from ..templates import get_iso_now

console = Console()


# Decision keywords
DECISION_KEYWORDS = [
    # Chinese
    "定了", "决定", "确认", "方向", "不做", "改成", "取舍", "边界", "目标",
    "先这样", "后续", "采用", "选择", "方案", "判断",
    # English
    "decided", "decision", "confirmed", "chose", "selected", "approach",
    "strategy", "direction", "focus on",
]


def extract_decisions_from_content(content: str, source: str) -> list[dict]:
    """Extract candidate decisions from content."""
    decisions = []
    
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        
        for keyword in DECISION_KEYWORDS:
            if keyword.lower() in line.lower():
                decisions.append({
                    "content": line,
                    "source": source,
                    "keyword": keyword,
                })
                break
    
    return decisions


def extract_decisions_command(
    project_path: str = typer.Argument(".", help="Path to project directory"),
    dry_run: bool = typer.Option(True, "--dry-run", "-d", help="Only show results, don't write"),
) -> None:
    """Extract candidate decisions from project files."""
    root = Path(project_path).resolve()
    
    if not root.exists():
        console.print(f"[red]Path not found: {root}[/red]")
        raise typer.Exit(1)
    
    console.print()
    console.print(f"[bold]Extracting decisions from: {root}[/bold]")
    console.print()
    
    # Scan files for decisions
    all_decisions = []
    
    # Check common project files
    files_to_scan = [
        "PROJECT.md",
        "FRAMING.md",
        "DECISIONS.md",
        "SNAPSHOT.md",
        "PROGRESS.md",
        "README.md",
    ]
    
    for filename in files_to_scan:
        filepath = root / filename
        if filepath.exists():
            content = read_file_safe(filepath)
            if content:
                decisions = extract_decisions_from_content(content, filename)
                all_decisions.extend(decisions)
    
    # Display results
    if not all_decisions:
        console.print("[green]No candidate decisions found.[/green]")
        console.print()
        return
    
    console.print(f"[yellow]Found {len(all_decisions)} candidate decision(s):[/yellow]")
    console.print()
    
    table = Table(title="Candidate Decisions")
    table.add_column("#", style="dim")
    table.add_column("Content", style="cyan")
    table.add_column("Source", style="green")
    table.add_column("Keyword", style="yellow")
    
    for i, decision in enumerate(all_decisions[:20], 1):  # Limit to 20
        content = decision["content"][:80] + "..." if len(decision["content"]) > 80 else decision["content"]
        table.add_row(str(i), content, decision["source"], decision["keyword"])
    
    console.print(table)
    
    if len(all_decisions) > 20:
        console.print(f"\n[dim]... and {len(all_decisions) - 20} more[/dim]")
    
    console.print()
    
    if dry_run:
        console.print("[dim]Dry-run mode. No changes made.[/dim]")
        console.print("To write to DECISIONS.md, run without --dry-run")
    
    console.print()
