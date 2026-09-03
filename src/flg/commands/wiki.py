"""flg wiki commands - Opt-in project knowledge map."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..core.files import is_flg_project
from ..core.wiki import (
    WIKI_CONFIG,
    WIKI_MANIFEST,
    build_wiki_manifest,
    compare_wiki,
    init_wiki,
)

console = Console()


def _restore_snapshot(path: Path, snapshot: bytes | None) -> None:
    if snapshot is None:
        path.unlink(missing_ok=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(snapshot)


def wiki_init(
    root: str = typer.Option("docs", "--root", help="Project-relative wiki directory."),
    home: str = typer.Option("docs/README.md", "--home", help="Project-relative wiki home page."),
) -> None:
    """Configure and build a project wiki index without moving source files."""
    project = Path.cwd()
    config_path = project / WIKI_CONFIG
    manifest_path = project / WIKI_MANIFEST
    config_before = config_path.read_bytes() if config_path.exists() else None
    manifest_before = manifest_path.read_bytes() if manifest_path.exists() else None
    try:
        config = init_wiki(project, wiki_root=root, home=home)
        manifest = build_wiki_manifest(project)
    except (OSError, ValueError) as exc:
        _restore_snapshot(config_path, config_before)
        _restore_snapshot(manifest_path, manifest_before)
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    console.print("[bold green]✓ Wiki continuity enabled[/bold green]")
    console.print(f"[bold]Root:[/bold] {config['root']}")
    console.print(f"[bold]Home:[/bold] {config['home']}")
    console.print(f"[bold]Indexed pages:[/bold] {manifest['page_count']}")


def wiki_build() -> None:
    """Rebuild the wiki manifest after source documents change."""
    project = Path.cwd()
    if not is_flg_project(project):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)
    try:
        manifest = build_wiki_manifest(project)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    console.print("[bold green]✓ Wiki manifest rebuilt[/bold green]")
    console.print(f"[bold]Pages:[/bold] {manifest['page_count']}")
    console.print(f"[bold]Manifest:[/bold] .flg/context/wiki_manifest.json")


def wiki_status() -> None:
    """Check wiki freshness without writing project state."""
    project = Path.cwd()
    try:
        result = compare_wiki(project)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    if not result["configured"]:
        console.print("[yellow]Wiki continuity is not configured.[/yellow]")
        raise typer.Exit(0)

    color = "green" if result["status"] == "fresh" else "yellow"
    console.print(f"[bold {color}]Wiki status: {result['status']}[/bold {color}]")
    console.print(f"[bold]Pages:[/bold] {len(result['pages'])}")
    table = Table("Change", "Count", "Paths")
    for key in ("added", "changed", "removed"):
        values = result[key]
        table.add_row(key, str(len(values)), ", ".join(values[:5]) or "—")
    console.print(table)
