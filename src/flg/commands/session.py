"""Session archive commands."""

from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console

from ..core.files import is_flg_project

console = Console()

_STRUCTURED_LEDGER_FILENAMES = {
    "project.md",
    "framing.md",
    "decisions.md",
    "snapshot.md",
    "progress.md",
    "constraints.md",
    "goal_evolution.md",
    "state.json",
}


def archive_session(
    root: Path,
    source_file: Path,
    name: str | None = None,
    force: bool = False,
) -> Path:
    """Copy raw session evidence into the project's sessions directory."""
    source = source_file.expanduser().resolve()
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"Session file not found: {source}")
    sessions_dir = (root / ".flg" / "sessions").resolve()
    if source.parent == sessions_dir:
        return source
    if source.name.lower() in _STRUCTURED_LEDGER_FILENAMES and not force:
        raise ValueError("Refusing to archive a structured ledger file as raw session evidence.")
    sessions_dir.mkdir(parents=True, exist_ok=True)
    if name:
        filename = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-.") or "session"
        if not filename.lower().endswith(".md"):
            filename += ".md"
    else:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        stem = re.sub(r"[^A-Za-z0-9._-]+", "-", source.stem).strip("-") or "session"
        filename = f"{timestamp}-{stem}.md"
    target = sessions_dir / filename
    if target.exists() and not force:
        raise FileExistsError(f"Archive already exists: {target}")
    shutil.copy2(source, target)
    return target


def save_session(
    source_file: str = typer.Argument(..., help="Raw transcript or session notes to archive"),
    name: str | None = typer.Option(None, "--name", help="Archive filename"),
    force: bool = typer.Option(False, "--force", help="Allow structured ledger input or overwrite"),
) -> None:
    """Archive raw session evidence under .flg/sessions."""
    root = Path.cwd()
    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)

    try:
        target = archive_session(root, Path(source_file), name=name, force=force)
    except (FileNotFoundError, ValueError, FileExistsError) as exc:
        console.print(f"[red]{exc}[/red]")
        if isinstance(exc, ValueError):
            console.print("[dim]Use raw conversation notes or pass --force only when intentional.[/dim]")
        elif isinstance(exc, FileExistsError):
            console.print("[dim]Choose another --name or pass --force to replace it.[/dim]")
        raise typer.Exit(1) from exc

    if target == Path(source_file).expanduser().resolve():
        console.print(f"[green]Session already archived:[/green] {target}")
    else:
        console.print(f"[green]Archived session:[/green] {target}")
