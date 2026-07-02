"""flg import command - Import existing project files into FLG."""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

from ..core.files import is_flg_project, read_file_safe
from ..core.state import create_initial_state, save_state
from ..templates import get_iso_now

console = Console()


def import_project(
    source_path: str = typer.Argument(..., help="Path to source project directory"),
    target_path: str = typer.Option(".", "--target", "-t", help="Target directory"),
    dry_run: bool = typer.Option(True, "--dry-run", "-d", help="Preview import without changes"),
) -> None:
    """Import existing project files into FLG structure."""
    source = Path(source_path).resolve()
    target = Path(target_path).resolve()
    
    if not source.exists():
        console.print(f"[red]Source path not found: {source}[/red]")
        raise typer.Exit(1)
    
    console.print()
    console.print(f"[bold]Importing from: {source}[/bold]")
    console.print(f"[bold]Target: {target}[/bold]")
    console.print()
    
    # Scan source directory
    files_to_import = []
    
    # Map source files to FLG files
    file_mapping = {
        "PROJECT.md": "PROJECT.md",
        "FRAMING.md": "FRAMING.md",
        "DECISIONS.md": "DECISIONS.md",
        "SNAPSHOT.md": "SNAPSHOT.md",
        "PROGRESS.md": "PROGRESS.md",
        "README.md": "README.md",
        # Chinese names
        "项目进展.md": "PROGRESS.md",
        "决策日志.md": "DECISIONS.md",
        "项目快照.md": "SNAPSHOT.md",
    }
    
    for source_name, target_name in file_mapping.items():
        source_file = source / source_name
        if source_file.exists():
            files_to_import.append({
                "source": source_name,
                "target": target_name,
                "size": source_file.stat().st_size,
            })
    
    # Display import preview
    if not files_to_import:
        console.print("[yellow]No importable files found.[/yellow]")
        console.print()
        return
    
    table = Table(title="Import Preview")
    table.add_column("Source File", style="cyan")
    table.add_column("Target File", style="green")
    table.add_column("Size", style="dim")
    
    for f in files_to_import:
        table.add_row(f["source"], f["target"], f"{f['size']} bytes")
    
    console.print(table)
    console.print()
    
    if dry_run:
        console.print("[dim]Dry-run mode. No changes made.[/dim]")
        console.print()
        console.print("To proceed with import:")
        console.print(f"  flg import {source_path} --no-dry-run")
        console.print()
        return
    
    # Confirm import
    if not Confirm.ask("Proceed with import?"):
        console.print("[yellow]Import cancelled.[/yellow]")
        return
    
    # Execute import
    now = get_iso_now()
    
    # Create target directory if needed
    target.mkdir(parents=True, exist_ok=True)
    
    # Copy files
    imported_files = []
    for f in files_to_import:
        source_file = source / f["source"]
        target_file = target / f["target"]
        
        if target_file.exists():
            console.print(f"[yellow]Skipped {f['target']} (already exists)[/yellow]")
            continue
        
        shutil.copy2(source_file, target_file)
        imported_files.append(f["target"])
        console.print(f"[green]✓ Imported {f['source']} → {f['target']}[/green]")
    
    # Initialize FLG if not already
    if not is_flg_project(target):
        console.print("\n[yellow]Initializing FLG structure...[/yellow]")
        
        # Create .flg directory
        flg_dir = target / ".flg"
        flg_dir.mkdir(exist_ok=True)
        (flg_dir / "patches").mkdir(exist_ok=True)
        (flg_dir / "sessions").mkdir(exist_ok=True)
        (flg_dir / "memory").mkdir(exist_ok=True)
        
        # Create state.json
        project_name = source.name
        state = create_initial_state(project_name)
        save_state(target, state)
        
        # Create CONTRACT.md
        from ..templates import CONTRACT_MD
        (flg_dir / "CONTRACT.md").write_text(CONTRACT_MD, encoding="utf-8")
        
        console.print("[green]✓ FLG structure initialized[/green]")
    
    console.print()
    console.print(f"[bold green]Import complete![/bold green]")
    console.print(f"Imported {len(imported_files)} file(s)")
    console.print()
    
    if imported_files:
        console.print("Next steps:")
        console.print("  1. Run [cyan]flg frame[/cyan] to check project framing")
        console.print("  2. Run [cyan]flg status[/cyan] to see project state")
    
    console.print()
