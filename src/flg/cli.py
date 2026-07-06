"""FlowGrid CLI - Engineering workflow for strategy, marketing, operations and solution projects."""

import typer
from rich.console import Console

from .commands.init import init_project
from .commands.frame import frame_project
from .commands.closeout import closeout_session
from .commands.merge import merge_patch
from .commands.handoff import handoff_command
from .commands.export_handoff import export_handoff_pack
from .commands.review import review_patch
from .commands.audit import audit_project
from .commands.extract import extract_decisions_command
from .commands.import_cmd import import_project
from .core.state import load_state, get_state_schema_info

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
app.command(name="review", help="Review candidate decisions from a patch")(review_patch)
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


@app.command(name="state-schema")
def show_state_schema() -> None:
    """Show state.json schema health: core vs extension fields, variant mappings."""
    import json
    from pathlib import Path
    from rich.table import Table
    
    root = Path.cwd()
    state_path = root / ".flg" / "state.json"
    
    if not state_path.exists():
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)
    
    raw = json.loads(state_path.read_text(encoding="utf-8"))
    # Use the normalized view — this is what the CLI actually works with
    state = load_state(root)
    if state is None:
        console.print("[red]Failed to load state. File may be corrupt.[/red]")
        raise typer.Exit(1)
    info = get_state_schema_info(state)
    
    # Health badge
    health_color = {"ok": "green", "legacy": "yellow", "degraded": "red"}
    health_label = {"ok": "✅ 标准", "legacy": "⚠ 遗留（变体字段可映射）", "degraded": "❌ 降级（缺失核心字段）"}
    
    console.print()
    console.print(f"[bold]State Schema Health:[/bold] [{health_color[info['schema_health']]}]{health_label[info['schema_health']]}[/{health_color[info['schema_health']]}]")
    console.print(f"Schema version: {info['schema_version']}  |  Total fields: {info['total_fields']}  |  Core: {info['core_count']}  |  Extension: {info['extension_count']}")
    console.print()
    
    # Core fields table
    if info["core_fields"]:
        ct = Table(title="Core Fields (CLI depends on these)", show_lines=False)
        ct.add_column("Field", style="cyan")
        ct.add_column("Value", style="dim")
        for k in info["core_fields"]:
            v = raw.get(k, "")
            v_str = str(v)[:80]
            ct.add_row(k, v_str)
        console.print(ct)
        console.print()
    
    # Variant mappings
    if info["legacy_key_mappings"]:
        console.print("[yellow]Legacy key mappings (variant → canonical):[/yellow]")
        for variant, canonical in info["legacy_key_mappings"].items():
            console.print(f"  [dim]{variant}[/dim] → [cyan]{canonical}[/cyan]")
        console.print()
    
    # Extension fields
    if info["extension_fields"]:
        et = Table(title="Extension Fields (project-specific, CLI preserves but doesn't depend on)", show_lines=False)
        et.add_column("Field", style="dim")
        for k in info["extension_fields"]:
            et.add_row(k)
        console.print(et)
        console.print()
    
    # Missing core
    if info["missing_core"]:
        console.print("[red]Missing core fields (cannot be autofilled):[/red]")
        for k in info["missing_core"]:
            console.print(f"  [red]✗[/red] {k}")
        console.print()
        console.print("[dim]Run 'flg init' to create a fresh state, or manually add these fields.[/dim]")
    
    # Upgrade hint
    if info["schema_health"] in ("legacy", "degraded"):
        console.print()
        console.print("[dim]Tip: FLG reads legacy states safely via variant-key mapping. No forced rewrite — your custom fields are preserved. Run 'flg closeout' to normalize the state on next closeout.[/dim]")


@app.command(name="context")
def show_agent_context() -> None:
    """Show the Agent Startup Context — exactly what an agent sees on project entry.

    Displays the 3 sources of the Agent Startup Context Protocol:
      1. SNAPSHOT.md   (~2KB) — current project state
      2. DECISIONS.md  (~1KB) — most recent 1-2 decisions
      3. state.json    (~0.5KB) — next_actions

    Total payload: ~3-4KB. Every source is a plaintext file — auditable by the user.
    """
    from pathlib import Path
    from rich.panel import Panel
    from rich.markdown import Markdown
    import re

    root = Path.cwd()
    state_path = root / ".flg" / "state.json"

    if not state_path.exists():
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)

    import json
    state = json.loads(state_path.read_text(encoding="utf-8"))

    snapshot_text = ""
    recent = ""
    na_text = ""

    console.print()
    console.print("[bold]Agent Startup Context[/bold] [dim](~3-4KB total, 3 sources)[/dim]")
    console.print()

    # 1. SNAPSHOT.md
    snapshot_path = root / "SNAPSHOT.md"
    if snapshot_path.exists():
        snapshot_text = snapshot_path.read_text(encoding="utf-8")
        # Strip frontmatter if present
        snapshot_text = re.sub(r'^---\n.*?\n---\n', '', snapshot_text, flags=re.DOTALL).strip()
        console.print(Panel(snapshot_text[:2000], title="[bold cyan]1. SNAPSHOT.md[/bold cyan] — Current State (~2KB)", border_style="cyan"))
    else:
        console.print("[yellow]SNAPSHOT.md not found. Run 'flg closeout' to generate it.[/yellow]")
    console.print()

    # 2. Recent decisions
    decisions_path = root / "DECISIONS.md"
    if decisions_path.exists():
        decisions_text = decisions_path.read_text(encoding="utf-8")
        # Extract last 1-2 decision blocks (format: ## D-XXX｜title or ## D-XXX title)
        blocks = re.split(r'\n## D-\d+', decisions_text)
        recent = ""
        for block in blocks[-2:]:
            # Try multiple decision content patterns
            # Pattern 1: - **决策**：content
            dm = re.search(r'\*\*决策\*\*[：:]\s*(.+?)(?:\n|$)', block)
            # Pattern 2: **最终决策** section
            if not dm:
                dm = re.search(r'最终决策\*\*\n(.+?)(?:\n|$)', block)
            if dm:
                recent += f"> {dm.group(1).strip()[:200]}\n\n"
        if recent.strip():
            console.print(Panel(recent.strip(), title="[bold green]2. DECISIONS.md[/bold green] — Recent Decisions (~1KB)", border_style="green"))
        else:
            console.print("[dim]No decisions found in DECISIONS.md[/dim]")
    else:
        console.print("[dim]DECISIONS.md not found[/dim]")
    console.print()

    # 3. next_actions from state.json
    na = state.get("next_actions", [])
    if na:
        na_text = "\n".join(f"- {a}" for a in na[:5])
        console.print(Panel(na_text, title="[bold yellow]3. state.json next_actions[/bold yellow] — Immediate Tasks (~0.5KB)", border_style="yellow"))
    else:
        console.print("[dim]No next_actions in state.json[/dim]")
    console.print()

    # Total estimate
    snapshot_size = len(snapshot_text) if snapshot_path.exists() else 0
    decisions_size = len(recent) if decisions_path.exists() else 0
    na_size = len(na_text) if na else 0
    total = snapshot_size + decisions_size + na_size
    console.print(f"[dim]Estimated context payload: {total} chars (~{total//4} tokens)[/dim]")
    console.print("[dim]Use 'flg closeout' to refresh SNAPSHOT.md with latest decisions and risks.[/dim]")


if __name__ == "__main__":
    app()
