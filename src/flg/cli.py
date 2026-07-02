"""FlowGrid CLI - Engineering workflow for strategy, marketing, operations and solution projects."""

import typer
from rich.console import Console

from .commands.init import init_project
from .commands.frame import frame_project
from .commands.closeout import closeout_session
from .commands.merge import merge_patch
from .commands.handoff import handoff_command
from .commands.export_handoff import export_handoff_pack
from .commands.audit import audit_project
from .commands.extract import extract_decisions_command
from .commands.import_cmd import import_project
from .core.state import load_state

console = Console()

app = typer.Typer(
    name="flg",
    help="FlowGrid (FLG) - Engineering workflow for strategy, marketing, operations and solution projects.",
    no_args_is_help=True,
)

# Register commands
app.command(name="init", help="Initialize a new FlowGrid project")(init_project)
app.command(name="frame", help="Check framing completeness and generate frame patch")(frame_project)
app.command(name="closeout", help="Generate closeout patch from session transcript")(closeout_session)
app.command(name="merge", help="Merge pending patch into formal ledger")(merge_patch)
app.command(name="handoff", help="Generate agent handoff summary")(handoff_command)
app.command(name="export-handoff", help="Export a resumable handoff pack")(export_handoff_pack)
app.command(name="audit", help="Audit existing project directory")(audit_project)
app.command(name="extract-decisions", help="Extract candidate decisions")(extract_decisions_command)
app.command(name="import", help="Import existing project into FLG")(import_project)


@app.command(name="version")
def show_version() -> None:
    """Show FLG version."""
    from . import __version__
    console.print(f"FlowGrid v{__version__}")


@app.command(name="status")
def show_status() -> None:
    """Show current project status."""
    from pathlib import Path
    from rich.table import Table
    
    root = Path.cwd()
    state_path = root / ".flg" / "state.json"
    
    if not state_path.exists():
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)
    
    state = load_state(root)
    if state is None:
        console.print("[red]No readable state found. Run 'flg init' first.[/red]")
        raise typer.Exit(1)
    
    console.print()
    console.print(f"[bold]Project:[/bold] {state['project_name']}")
    console.print(f"[bold]Stage:[/bold] {state['current_stage']}")
    console.print(f"[bold]Created:[/bold] {state['created_at']}")
    console.print(f"[bold]Version:[/bold] {state['flg_version']}")
    
    # Check pending patches from state
    pending_patches = state.get("pending_patches", [])
    
    # Also scan .flg/patches/ directory for actual patch files
    patches_dir = root / ".flg" / "patches"
    patch_files = list(patches_dir.glob("*.patch.md")) if patches_dir.exists() else []
    
    if pending_patches or patch_files:
        console.print()
        console.print(f"[yellow]⚠ This project has pending patches. Agents should read them before continuing.[/yellow]")
        console.print()
        
        # Create table for patches
        table = Table(title="Pending Patches")
        table.add_column("Patch ID", style="cyan")
        table.add_column("Risk Level", style="yellow")
        table.add_column("Source Command", style="green")
        table.add_column("Generated At", style="dim")
        table.add_column("Status", style="bold")
        
        # Add patches from state
        for p in pending_patches:
            table.add_row(
                p.get("patch_id", "unknown"),
                p.get("risk_level", "unknown"),
                p.get("source_command", "unknown"),
                p.get("created_at", "unknown"),
                p.get("status", "unknown"),
            )
        
        # Also add any patch files not in state
        state_patch_ids = {p.get("patch_id") for p in pending_patches}
        for pf in patch_files:
            # Try to extract patch_id from filename
            filename = pf.stem.replace(".patch", "")
            if filename not in state_patch_ids:
                # Read patch to get info
                content = pf.read_text(encoding="utf-8")
                patch_info = {"patch_id": filename, "risk_level": "unknown", "source_command": "unknown", "created_at": "unknown", "status": "unknown"}
                for line in content.split("\n"):
                    if line.startswith("patch_id:"):
                        patch_info["patch_id"] = line.split(":", 1)[1].strip()
                    elif line.startswith("risk_level:"):
                        patch_info["risk_level"] = line.split(":", 1)[1].strip()
                    elif line.startswith("source_command:"):
                        patch_info["source_command"] = line.split(":", 1)[1].strip()
                    elif line.startswith("generated_at:"):
                        patch_info["created_at"] = line.split(":", 1)[1].strip()
                    elif line.startswith("status:"):
                        patch_info["status"] = line.split(":", 1)[1].strip()
                table.add_row(
                    patch_info["patch_id"],
                    patch_info["risk_level"],
                    patch_info["source_command"],
                    patch_info["created_at"],
                    patch_info["status"],
                )
        
        console.print(table)
        console.print()
        console.print("[dim]Agents should read these patches to understand pending project state.[/dim]")
    else:
        console.print("\n[green]No pending patches[/green]")
    
    console.print()


if __name__ == "__main__":
    app()
