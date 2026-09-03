"""Explicit management of the optional active delivery contract."""

from datetime import datetime, timezone
from pathlib import Path
from typing import List

import typer
from rich.console import Console

from ..core.delivery import active_delivery_issues
from ..core.files import is_flg_project
from ..core.state import load_state, save_state

console = Console()


def _root() -> Path:
    root = Path.cwd()
    if not is_flg_project(root):
        console.print("[red]Not a FLG project. Run 'flg init' first.[/red]")
        raise typer.Exit(1)
    return root


def delivery_show() -> None:
    """Show the active delivery contract without changing state."""
    state = load_state(_root()) or {}
    delivery = state.get("active_delivery")
    if delivery is None:
        console.print("[yellow]No active delivery contract recorded.[/yellow]")
        return
    console.print_json(data=delivery)
    for issue in active_delivery_issues(state):
        console.print(f"[yellow]⚠ {issue}[/yellow]")


def delivery_set(
    code_root: str = typer.Option(..., "--code-root"),
    candidate_version: str = typer.Option(..., "--candidate-version"),
    owner: str = typer.Option(..., "--owner"),
    gate: List[str] = typer.Option(..., "--gate", help="Repeat for every active release gate"),
    evidence: List[str] = typer.Option(..., "--evidence", help="Repeat for each verified evidence item"),
    next_action: str = typer.Option(..., "--next-action"),
) -> None:
    """Explicitly replace the current delivery contract for this project."""
    root = _root()
    state = load_state(root) or {}
    state["active_delivery"] = {
        "code_root": str(Path(code_root).expanduser().resolve()),
        "candidate_version": candidate_version,
        "owner": owner,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "gates": gate,
        "evidence": evidence,
        "next_action": next_action,
    }
    save_state(root, state)
    console.print("[green]✓ Active delivery contract updated[/green]")
