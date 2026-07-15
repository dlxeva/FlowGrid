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
from .commands.context import context_command
from .commands.evidence import evidence_command
from .commands.capture import capture_add, capture_list, capture_show, capture_review, capture_profile
from .commands.decision_cmd import decision_add
from .commands.patch_cmd import patch_supersede, patch_discard
from .commands.onboard import onboard
from .commands.doctor import doctor, reindex
from .commands.session import save_session
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
app.command(name="context", help="Generate bounded agent startup Context Pack")(context_command)
app.command(name="evidence", help="Show evidence behind a reviewed decision")(evidence_command)
app.command(name="onboard", help="First-run setup: env check, guided demo, and skill installation")(onboard)
app.command(name="doctor", help="Check cross-file project consistency")(doctor)
app.command(name="reindex", help="Rebuild evidence index from DECISIONS.md")(reindex)

# Session archive group
session_app = typer.Typer(help="Archive raw session evidence", no_args_is_help=True)
session_app.command(name="save", help="Archive a raw transcript under .flg/sessions/")(save_session)
app.add_typer(session_app, name="session")

# Capture subcommand group
capture_app = typer.Typer(help="Real-time judgment candidate capture", no_args_is_help=True)
capture_app.command(name="add", help="Capture a judgment candidate")(capture_add)
capture_app.command(name="list", help="List captured judgment candidates")(capture_list)
capture_app.command(name="show", help="Show details of a captured judgment")(capture_show)
capture_app.command(name="review", help="Review pending captures: accept into DECISIONS.md or reject")(capture_review)
capture_app.command(name="profile", help="Manage judgment language profile for this project")(capture_profile)
app.add_typer(capture_app, name="capture")

# Decision subcommand group
decision_app = typer.Typer(help="Direct decision recording (strong commitment only)", no_args_is_help=True)
decision_app.command(name="add", help="Record a confirmed decision directly to DECISIONS.md")(decision_add)
app.add_typer(decision_app, name="decision")

# Patch lifecycle subcommand group (发现 2)
patch_app = typer.Typer(help="Manage patch lifecycle: supersede or discard stale patches", no_args_is_help=True)
patch_app.command(name="supersede", help="Mark a patch as superseded (replaced by a newer patch)")(patch_supersede)
patch_app.command(name="discard", help="Mark a patch as discarded (rejected / no longer relevant)")(patch_discard)
app.add_typer(patch_app, name="patch")


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

    # Collect all patches (from state + orphan files on disk) into a unified list,
    # then split by status. Only pending_review (or unknown) patches trigger the
    # "⚠ pending" warning. merged/rejected/superseded patches are shown as a
    # count-only summary so they don't cry wolf on every status run.
    # (发现 16/4: previously any patch file in .flg/patches/ triggered the warning,
    #  even after it was merged or rejected.)
    all_patches = []
    state_patch_ids = set()

    for p in pending_patches:
        all_patches.append({
            "patch_id": p.get("patch_id", "unknown"),
            "risk_level": p.get("risk_level", "unknown"),
            "source_command": p.get("source_command", "unknown"),
            "created_at": p.get("created_at", "unknown"),
            "status": p.get("status", "unknown"),
        })
        state_patch_ids.add(p.get("patch_id"))

    for pf in patch_files:
        filename = pf.stem.replace(".patch", "")
        if filename in state_patch_ids:
            continue
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
            # Only the frontmatter status defines patch lifecycle. Candidate
            # sections can contain their own pending_review statuses.
            elif line.startswith("status:") and patch_info["status"] == "unknown":
                patch_info["status"] = line.split(":", 1)[1].strip()
        all_patches.append(patch_info)

    # Split: pending_review (action needed) vs closed (merged/rejected/superseded)
    _CLOSED_STATUSES = {"merged", "rejected", "superseded"}
    pending_review_patches = []
    closed_patches = []
    for p in all_patches:
        status = (p.get("status") or "unknown").lower()
        if status in _CLOSED_STATUSES:
            closed_patches.append(p)
        else:
            pending_review_patches.append(p)

    if pending_review_patches:
        console.print()
        console.print(f"[yellow]⚠ This project has {len(pending_review_patches)} pending patch(es) needing review. Agents should read them before continuing.[/yellow]")
        console.print()

        table = Table(title="Pending Patches")
        table.add_column("Patch ID", style="cyan")
        table.add_column("Risk Level", style="yellow")
        table.add_column("Source Command", style="green")
        table.add_column("Generated At", style="dim")
        table.add_column("Status", style="bold")

        for p in pending_review_patches:
            table.add_row(
                p["patch_id"],
                p["risk_level"],
                p["source_command"],
                p["created_at"],
                p["status"],
            )

        console.print(table)
        console.print()
        console.print("[dim]Agents should read these patches to understand pending project state.[/dim]")
    else:
        console.print("\n[green]No pending patches needing review[/green]")

    if closed_patches:
        console.print()
        closed_counts = {}
        for p in closed_patches:
            s = p["status"]
            closed_counts[s] = closed_counts.get(s, 0) + 1
        summary_parts = [f"{count} {status}" for status, count in closed_counts.items()]
        console.print(f"[dim]Closed patches (kept for audit): {', '.join(summary_parts)}[/dim]")
    
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


if __name__ == "__main__":
    app()
